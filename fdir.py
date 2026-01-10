#!/usr/bin/env python3

import sys
from pathlib import Path
from datetime import datetime, timedelta
import os
import fnmatch
from difflib import SequenceMatcher

RESET = "\033[0m"
YELLOW_BG = "\033[43m"
BLUE   = "\033[38;5;39m"
GREEN  = "\033[38;5;82m"
YELLOW = "\033[38;5;226m"
ORANGE = "\033[38;5;214m"
RED    = "\033[38;5;196m"
RESET  = "\033[0m"


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
"""
    )

def version():
    print ("fdir v3.0.0, check the GitHub repo for new updates: https://github.com/VG-dev1/fdir")

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

def print_files(matching_files, first_op, second_op):
    for file_info in matching_files:
        name, date, size_str = file_info[0], file_info[1], file_info[2]
        raw_size = file_info[4]

        name_keyword = None
        if first_op == "name":
            name_keyword = sys.argv[3]
        elif second_op == "name":
            idx = sys.argv.index(second_op)
            name_keyword = sys.argv[idx + 2]

        date_display = highlight(f" {date} ", YELLOW_BG) if first_op == "modified" or second_op == "modified" else f" {date} "

        padded_size = f"{size_str:>10}"
        if first_op == "size" or second_op == "size":
            display_size = highlight(f" {padded_size} ", YELLOW_BG)
        else:
            display_size = f" {padded_size} "
        display_size = color_by_size(display_size, raw_size)

        name_display = name
        if name_keyword:
            import re
            pattern = re.compile(re.escape(name_keyword), re.IGNORECASE)
            name_display = pattern.sub(lambda m: highlight(m.group(0), YELLOW_BG), name)

        path = os.path.abspath(file_info[0])
        url = f"file:///{path.replace(os.sep,'/')}"
        linked_name = file_link(name_display, url)

        print(f"{date_display} | {display_size} | {linked_name}")

def delete_files(matching_files):
    for file in matching_files:
        name = file[0]
        os.remove(name)

def convert_files(matching_files, new_extension):
    for file in matching_files:
        old_path = file[5]
        new_path = old_path.with_suffix(new_extension)
        old_path.rename(new_path)

def fuzzy_match(query, file_name, threshold=0.6):
    name_only = file_name.rsplit('.', 1)[0]
    ratio = SequenceMatcher(None, query.lower(), name_only.lower()).ratio()
    return ratio >= threshold

def satisfies_criteria(path, op, flag, value, ignore, case_sensitive, fuzzy, content):
    if ignore:
        for pattern in ignore:
            if fnmatch.fnmatch(path.name, pattern):
                return False
    if path.name in ignore:
        return False
            
    if op == "all": return True
    if op == "size":
        cutoff = parse_size(value)
        return path.stat().st_size > cutoff if flag == "--gt" else path.stat().st_size < cutoff
    if op == "modified":
        cutoff = datetime.now() - parse_time(value)
        modified = datetime.fromtimestamp(path.stat().st_mtime)
        return modified <= cutoff if flag == "--gt" else modified >= cutoff
    if op == "name":
        if not case_sensitive:
            name_arg = value.lower()
            file_name = path.name.lower()
        else:
            name_arg = value
            file_name = path.name
        if fuzzy and flag == "--keyword":
            return fuzzy_match(value, file_name)
        else:
            if flag == "--keyword": return name_arg in file_name
            if flag == "--swith": return file_name.startswith(name_arg)
            if flag == "--ewith": return file_name.endswith(name_arg)
    if op == "type":
        return path.suffix == value
    if op == "content":
        if content is None: return False
        if not case_sensitive:
            return value.lower() in content.lower()
        return value in content
    return False

def main():
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
        order_field = sys.argv[idx + 1]
        order_dir = sys.argv[idx + 2]

    first_op = sys.argv[1]
    first_flag, first_val = None, None
    if first_op != "all" and first_op in ["modified", "size", "type", "name", "all", "content"]:
        if len(sys.argv) >= 4:
            first_flag = sys.argv[2]
            first_val = sys.argv[3]
            if not (
                (first_op == "modified" and first_flag in ["--gt", "--lt"]) or
                (first_op == "size" and first_flag in ["--gt", "--lt"]) or
                (first_op == "type" and first_flag in ["--eq"]) or
                (first_op == "name" and first_flag in ["--keyword", "--swith", "--ewith"]) or
                (first_op == "content" and first_flag in ["--keyword"])
            ):
                print("error: Invalid arguments for operation.")
                sys.exit(1)

        else:
            print("error: Missing arguments for operation.")
            sys.exit(1)
    elif first_op == "all":
        pass
    elif first_op not in ["modified", "size", "type", "name", "all", "version", "content"]:
        print("error: Invalid operation.")
        sys.exit(1)

    second_op, second_flag, second_val = None, None, None
    if connector:
        conn_idx = sys.argv.index(connector)
        second_op = sys.argv[conn_idx + 1]
        second_flag = sys.argv[conn_idx + 2]
        second_val = sys.argv[conn_idx + 3]

    matching_files = []
    if "--deep" in sys.argv:
        file_iterator = Path.cwd().rglob("*")
    else:
        file_iterator = Path.cwd().iterdir()
    if "--case" in sys.argv:
        if first_op in ["name", "content"] or second_op in ["name", "content"]:
            case_sensitive = True
        else:
            print ("error: Invalid arguments for operation.")
            sys.exit(1)
    else:
        case_sensitive = False
    counter = 0
    if "--top" in sys.argv:
        idx = sys.argv.index("--top")
        try:
            number = int(sys.argv[idx+1])
        except IndexError:
            print ("error: Missing arguments for operation.")
            sys.exit(1)
    else:
        number = None
    if "--fuzzy" in sys.argv:
        if first_op in ["name", "content"] or second_op in ["name", "content"]:
            fuzzy = True
        else:
            print ("error: Invalid arguments for operation.")
            sys.exit(1)
    else:
        fuzzy = False

    for path in file_iterator:
        if not (path.is_file() or path.is_dir()): continue

        content = None
        if (first_op == "content" or second_op == "content") and path.is_file():
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                content = ""
        
        match1 = satisfies_criteria(path, first_op, first_flag, first_val, ignore, case_sensitive, fuzzy, content)
        
        if connector:
            match2 = satisfies_criteria(path, second_op, second_flag, second_val, ignore, case_sensitive, fuzzy, content)
            final_match = (match1 or match2) if connector == "or" else (match1 and match2)
        else:
            final_match = match1

        if final_match:
            name = path.name
            raw_mtime = path.stat().st_mtime
            raw_size = path.stat().st_size
            date_str = datetime.fromtimestamp(raw_mtime).strftime("%d/%m/%y")
            size_str = readable_size(raw_size)

            matching_files.append([name, date_str, size_str, raw_mtime, raw_size, path])

            counter += 1
        
        if number:
            if counter == number:
                break

    if order_field:
        rev = (order_dir == "d")
        if order_field == "name":
            matching_files.sort(key=lambda x: x[0].lower(), reverse=rev)
        elif order_field == "modified":
            matching_files.sort(key=lambda x: x[3], reverse=rev)
        elif order_field == "size":
            matching_files.sort(key=lambda x: x[4], reverse=rev)

    print_files(matching_files, first_op, second_op)
    
    total = 0
    for file in matching_files:
        total += file[4]
    total = str(readable_size(total))
    print(f"Showing {len(matching_files)} files ({total}).")

    if "--del" in sys.argv:
        confirmation = input(f"warning: {len(matching_files)} files will be deleted. Are you sure you want to continue? (y/n) ")
        if confirmation == "y":
            delete_files(matching_files)
            print (f"Deleted {len(matching_files)} files.")
    if "--convert" in sys.argv:
        if first_op == "type" or second_op == "op":
            confirmation = input(f"warning: {len(matching_files)} files will be converted. Are you sure you want to continue? (y/n) ")
            if confirmation == "y":
                idx = sys.argv.index("--convert")
                try:
                    new_extension = sys.argv[idx+1]
                except IndexError:
                    print ("error: Missing arguments for operation.")
                    sys.exit(1)
                convert_files(matching_files, new_extension)
                print (f"Converted {len(matching_files)} files to {new_extension}.")
        else:
            print ("error: Invalid arguments for operation.")
            sys.exit(1)

if __name__ == "__main__":
    main()