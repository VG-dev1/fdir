#!/usr/bin/env python3

import sys
from pathlib import Path
from datetime import datetime, timedelta
import os
import fnmatch
from difflib import SequenceMatcher
import shutil
import time
import re

RESET = "\033[0m"
YELLOW_BG = "\033[43m"
BLUE   = "\033[38;5;39m"
GREEN  = "\033[38;5;82m"
YELLOW = "\033[38;5;226m"
ORANGE = "\033[38;5;214m"
RED    = "\033[38;5;196m"

def usage():
    print(
        """Usage:
  `fdir <operation> [options] [--order <field> <a|d>]

OPERATIONS
  modified   --gt | --lt <time>     Filter by last modified date
  size       --gt | --lt <size>     Filter by file size
  name       --keyword <pattern>    Name contains pattern
             --swith <pattern>      Name starts with pattern
             --ewith <pattern>      Name ends with pattern
  type       --eq <extension>       Match file extension (e.g. .py)
  all                             List all files and directories
  version                         Show fdir version

TIME UNITS (modified)
  h    hours
  d    days
  w    weeks
  m    months (≈30 days)
  y    years  (≈365 days)

SIZE UNITS (size)
  B    bytes
  KB   kilobytes
  MB   megabytes
  GB   gigabytes

ADDITIONAL FLAGS
  --order <field> <a|d>   Sort by: name | size | modified
                          a = ascending, d = descending
  --deep                  Search recursively
  --top <n>               Show only first N results
  --fuzzy                 Search approximately
  --del                   Delete matching files
  --convert               Convert matching files
"""
    )

def version():
    print ("fdir v3.1.0, check the GitHub repo for new updates: https://github.com/VG-dev1/fdir")

def parse_time(value: str) -> timedelta:
    if len(value) < 2:
        print ("error: Time value is too short.")
        sys.exit(1)

    try:
        amount = int(value[:-1])
    except ValueError:
        print ("error: Invalid number in time value.")
        sys.exit(1)

    unit = value[-1]

    match unit:
        case "h":
            return timedelta(hours=amount)
        case "d":
            return timedelta(days=amount)
        case "w":
            return timedelta(weeks=amount)
        case "m":
            return timedelta(days=amount * 30)
        case "y":
            return timedelta(days=amount * 365)
        case _:
            print (f"error: Unknown time unit.")
            sys.exit(1)
        
def parse_size(value: str):
    if len(value) < 2:
        print ("error: Size value is too short.")
        sys.exit(1)

    amount_str = value[:-2]
    unit = value[-2:].lower()

    if unit in ("k", "m", "g"):
        amount_str = value[:-1]
        unit = value[-1].lower()

    try:
        byte_amount = int(amount_str)
    except ValueError:
        print ("error: Invalid number in size value.")
        sys.exit(1)

    match unit:
        case "kb" | "k":
            return byte_amount * 1024
        case "mb" | "m":
            return byte_amount * (1024 ** 2)
        case "gb" | "g":
            return byte_amount * (1024 ** 3)
        case "b":
            return byte_amount
        case _:
            print (f"error: Unknown size unit: {unit!r}")
            sys.exit(1)

def readable_size(size_bytes):
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1

    if units[i] == "B":
        return f"{int(size)} {units[i]}"
    else:
        return f"{size:.1f} {units[i]}"
    
def highlight(text, color):
    return f"{color}{text}{RESET}"

def color_by_size(text, size_bytes):
    if size_bytes < 1024 * 1024:
        color = BLUE
    elif size_bytes < 10 * 1024 * 1024:
        color = GREEN
    elif size_bytes < 100 * 1024 * 1024:
        color = YELLOW
    elif size_bytes < 500 * 1024 * 1024:
        color = ORANGE
    else:
        color = RED
    return f"{color}{text}{RESET}"

def file_link(text, url):
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"

def print_files(matching_files, first_op, first_val, second_op, second_val):
    for file_info in matching_files:
        name, date, size_str = file_info[0], file_info[1], file_info[2]
        raw_size = file_info[4]

        date_display = highlight(f" {date} ", YELLOW_BG) if first_op == "modified" or second_op == "modified" else f" {date} "

        padded_size = f"{size_str:>10}"
        if first_op == "size" or second_op == "size":
            display_size = highlight(f" {padded_size} ", YELLOW_BG)
        else:
            display_size = f" {padded_size} "
        display_size = color_by_size(display_size, raw_size)

        name_display = name
        keywords = []
        if first_op == "name" and first_val: keywords.append(first_val)
        if second_op == "name" and second_val: keywords.append(second_val)

        for kw in keywords:
            pattern = re.compile(re.escape(kw), re.IGNORECASE)
            name_display = pattern.sub(lambda m: highlight(m.group(0), YELLOW_BG), name_display)

        path_abs = os.path.abspath(file_info[5])
        url = f"file:///{path_abs.replace(os.sep,'/')}"
        linked_name = file_link(name_display, url)

        print(f"{date_display} | {display_size} | {linked_name}")

def delete_files(matching_files):
    for file in matching_files:
        path = file[5]
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                os.remove(path)

def convert_files(matching_files, new_extension):
    for file in matching_files:
        old_path = file[5]
        if old_path.is_file():
            new_path = old_path.with_suffix(new_extension)
            old_path.rename(new_path)

def fuzzy_match(query, file_name, threshold=0.6):
    name_only = file_name.rsplit('.', 1)[0]
    ratio = SequenceMatcher(None, query.lower(), name_only.lower()).ratio()
    return ratio >= threshold

def satisfies_criteria(path_name, stat_info, op, flag, value, ignore, case_sensitive, fuzzy, content_found):
    for pattern in ignore:
        if fnmatch.fnmatch(path_name, pattern):
            return False
            
    if op == "all": return True
    if op == "size":
        cutoff = parse_size(value)
        return stat_info.st_size > cutoff if flag == "--gt" else stat_info.st_size < cutoff
    if op == "modified":
        cutoff = datetime.now() - parse_time(value)
        modified = datetime.fromtimestamp(stat_info.st_mtime)
        return modified <= cutoff if flag == "--gt" else modified >= cutoff
    if op == "name":
        if not case_sensitive:
            name_arg = value.lower()
            file_name = path_name.lower()
        else:
            name_arg = value
            file_name = path_name
        if fuzzy and flag == "--keyword":
            return fuzzy_match(value, file_name)
        else:
            if flag == "--keyword": return name_arg in file_name
            if flag == "--swith": return file_name.startswith(name_arg)
            if flag == "--ewith": return file_name.endswith(name_arg)
    if op == "type":
        return path_name.lower().endswith(value.lower())
    if op == "content":
        return content_found
    return False

def get_files(directory, recursive):
    if recursive:
        for root, dirs, files in os.walk(directory):
            for name in dirs + files:
                yield Path(root) / name
    else:
        with os.scandir(directory) as it:
            for entry in it:
                yield Path(entry.path)

def main():
    if os.name == 'nt':
        os.system('color')

    try:
        with open(".fdirignore", "r", encoding="utf-8") as f:
            ignore = [line.strip() for line in f if line.strip()] 
    except FileNotFoundError:
        ignore = []

    if len(sys.argv) == 1:
        print("error: No operation entered.\nsuggestion: Type 'fdir help'.")
        sys.exit(1)

    if sys.argv[1] == "help":
        usage()
        sys.exit(0)
    if sys.argv[1] == "version":
        version()
        sys.exit(0)

    connector = None
    if "or" in sys.argv: connector = "or"
    elif "and" in sys.argv: connector = "and"

    order_field, order_dir = None, None
    if "--order" in sys.argv:
        idx = sys.argv.index("--order")
        try:
            order_field = sys.argv[idx + 1]
            order_dir = sys.argv[idx + 2]
        except IndexError:
            print("error: Missing arguments for --order.")
            sys.exit(1)

    first_op = sys.argv[1]
    first_flag, first_val = None, None
    if first_op != "all" and first_op in ["modified", "size", "type", "name", "content"]:
        try:
            first_flag = sys.argv[2]
            first_val = sys.argv[3]
        except IndexError:
            print("error: Missing arguments for operation.")
            sys.exit(1)
            
        if not (
            (first_op == "modified" and first_flag in ["--gt", "--lt"]) or
            (first_op == "size" and first_flag in ["--gt", "--lt"]) or
            (first_op == "type" and first_flag in ["--eq"]) or
            (first_op == "name" and first_flag in ["--keyword", "--swith", "--ewith"]) or
            (first_op == "content" and first_flag in ["--keyword"])
        ):
            print("error: Invalid arguments for operation.")
            sys.exit(1)
    elif first_op == "all":
        pass
    else:
        print("error: Invalid operation.")
        sys.exit(1)

    second_op, second_flag, second_val = None, None, None
    if connector:
        try:
            conn_idx = sys.argv.index(connector)
            second_op = sys.argv[conn_idx + 1]
            second_flag = sys.argv[conn_idx + 2]
            second_val = sys.argv[conn_idx + 3]
        except IndexError:
            print(f"error: Missing arguments after '{connector}'.")
            sys.exit(1)

    start_time = time.perf_counter()
    deep = "--deep" in sys.argv
    file_iterator = get_files(os.getcwd(), deep)

    case_sensitive = "--case" in sys.argv
    fuzzy = "--fuzzy" in sys.argv
    
    number = None
    if "--top" in sys.argv:
        idx = sys.argv.index("--top")
        try:
            number = int(sys.argv[idx+1])
        except (IndexError, ValueError):
            print ("error: Invalid or missing argument for --top.")
            sys.exit(1)

    matching_files = []
    counter = 0

    for path in file_iterator:
        try:
            stat_info = path.stat()
        except (FileNotFoundError, PermissionError):
            continue

        content_match1 = False
        content_match2 = False

        def check_file_content(p, val):
            if not p.is_file(): return False
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if not case_sensitive:
                            if val.lower() in line.lower(): return True
                        else:
                            if val in line: return True
            except Exception:
                pass
            return False

        if first_op == "content":
            content_match1 = check_file_content(path, first_val)
        if second_op == "content":
            content_match2 = check_file_content(path, second_val)
        
        match1 = satisfies_criteria(path.name, stat_info, first_op, first_flag, first_val, ignore, case_sensitive, fuzzy, content_match1)
        
        if connector:
            match2 = satisfies_criteria(path.name, stat_info, second_op, second_flag, second_val, ignore, case_sensitive, fuzzy, content_match2)
            final_match = (match1 or match2) if connector == "or" else (match1 and match2)
        else:
            final_match = match1

        if final_match:
            name = path.name
            raw_mtime = stat_info.st_mtime
            raw_size = stat_info.st_size
            date_str = datetime.fromtimestamp(raw_mtime).strftime("%d/%m/%y")
            size_str = readable_size(raw_size)

            matching_files.append([name, date_str, size_str, raw_mtime, raw_size, path])
            counter += 1
        
        if number and counter >= number:
            break

    if order_field:
        rev = (order_dir == "d")
        if order_field == "name":
            matching_files.sort(key=lambda x: x[0].lower(), reverse=rev)
        elif order_field == "modified":
            matching_files.sort(key=lambda x: x[3], reverse=rev)
        elif order_field == "size":
            matching_files.sort(key=lambda x: x[4], reverse=rev)

    end_time = time.perf_counter()
    duration = end_time - start_time

    print_files(matching_files, first_op, first_val, second_op, second_val)
    
    total = sum(file[4] for file in matching_files)
    print(f"Showing {len(matching_files)} files ({readable_size(total)}).")
    print(f"Completed in {duration:.3f}s.")

    if "--del" in sys.argv and matching_files:
        confirmation = input(f"warning: {len(matching_files)} items will be deleted. Are you sure? (y/n) ")
        if confirmation.lower() == "y":
            delete_files(matching_files)
            print (f"Deleted {len(matching_files)} items.")

    if "--convert" in sys.argv and matching_files:
        idx = sys.argv.index("--convert")
        try:
            new_ext = sys.argv[idx+1]
            if not new_ext.startswith("."): new_ext = "." + new_ext
            confirmation = input(f"warning: {len(matching_files)} files will be converted to {new_ext}. Are you sure? (y/n) ")
            if confirmation.lower() == "y":
                convert_files(matching_files, new_ext)
                print (f"Converted {len(matching_files)} files.")
        except IndexError:
            print ("error: Missing extension for --convert.")
            sys.exit(1)

if __name__ == "__main__":
    main()