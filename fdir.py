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
import subprocess
import argparse

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
  all                               List all files and directories
  version                           Show fdir version

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
  --columns <3-chars>     Column order: n (name), d (date), s (size)
                          Example: nds
  --deep                  Search recursively
  --top <n>               Show only first N results
  --fuzzy                 Search approximately
  --del                   Delete matching files
  --convert               Convert matching files
  -exec <command>         Execute command for each match (use {} for path)
"""
    )

def version():
    print ("fdir v3.2.1, check the GitHub repo for new updates: https://github.com/VG-dev1/fdir")

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

def fuzzy_match(query, file_name, threshold=0.6):
    name_only = file_name.rsplit('.', 1)[0]
    ratio = SequenceMatcher(None, query.lower(), name_only.lower()).ratio()
    return ratio >= threshold

def check_file_content(p, val, case_sensitive):
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
            return fuzzy_match(value, path_name)
        else:
            if flag == "--keyword": return name_arg in file_name
            if flag == "--swith": return file_name.startswith(name_arg)
            if flag == "--ewith": return file_name.endswith(name_arg)
    if op == "type":
        return path_name.lower().endswith(value.lower())
    if op == "content":
        return content_found
    return False

def main():
    if os.name == 'nt':
        os.system('color')

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--deep", action="store_true")
    parent_parser.add_argument("--top", type=int)
    parent_parser.add_argument("--fuzzy", action="store_true")
    parent_parser.add_argument("--case", action="store_true")
    parent_parser.add_argument("--order", nargs=2)
    parent_parser.add_argument("--columns", default="dsn")
    parent_parser.add_argument("--del", action="store_true", dest="delete_flag")
    parent_parser.add_argument("--convert")
    parent_parser.add_argument("--nocolor", action="store_true")
    parent_parser.add_argument("--exec", nargs=argparse.REMAINDER)

    parser = argparse.ArgumentParser(prog="fdir", parents=[parent_parser], add_help=False)
    subparsers = parser.add_subparsers(dest="operation")

    mod_parser = subparsers.add_parser("modified", parents=[parent_parser], add_help=False)
    mod_parser.add_argument("--gt")
    mod_parser.add_argument("--lt")

    size_parser = subparsers.add_parser("size", parents=[parent_parser], add_help=False)
    size_parser.add_argument("--gt")
    size_parser.add_argument("--lt")

    name_parser = subparsers.add_parser("name", parents=[parent_parser], add_help=False)
    name_parser.add_argument("--keyword")
    name_parser.add_argument("--swith")
    name_parser.add_argument("--ewith")

    type_parser = subparsers.add_parser("type", parents=[parent_parser], add_help=False)
    type_parser.add_argument("--eq")

    cont_parser = subparsers.add_parser("content", parents=[parent_parser], add_help=False)
    cont_parser.add_argument("--keyword")

    subparsers.add_parser("all", parents=[parent_parser], add_help=False)
    subparsers.add_parser("version", parents=[parent_parser], add_help=False)
    subparsers.add_parser("help", parents=[parent_parser], add_help=False)

    args, unknown = parser.parse_known_args()

    if args.operation == "help":
        usage()
        sys.exit(0)
    
    if args.operation == "version":
        version()
        sys.exit(0)

    try:
        with open(".fdirignore", "r", encoding="utf-8") as f:
            ignore = [line.strip() for line in f if line.strip()] 
    except FileNotFoundError:
        ignore = []

    connector = None
    second_op, second_flag, second_val = None, None, None
    for conn in ["and", "or"]:
        if conn in unknown:
            connector = conn
            conn_idx = unknown.index(conn)
            try:
                second_op = unknown[conn_idx + 1]
                second_flag = unknown[conn_idx + 2]
                second_val = unknown[conn_idx + 3]
            except IndexError:
                print(f"error: Missing arguments after '{connector}'.")
                sys.exit(1)

    first_op = args.operation
    first_flag, first_val = None, None
    op_map = vars(args)
    for f in ["gt", "lt", "eq", "keyword", "swith", "ewith"]:
        if op_map.get(f):
            first_flag = f"--{f}"
            first_val = op_map[f]
            break

    start_time = time.perf_counter()
    matching_files = []
    file_iterator = Path(".").rglob("*") if args.deep else Path(".").iterdir()

    for path in file_iterator:
        try:
            stat_info = path.stat()
        except (FileNotFoundError, PermissionError):
            continue

        content_match1 = check_file_content(path, first_val, args.case) if first_op == "content" else False
        content_match2 = check_file_content(path, second_val, args.case) if second_op == "content" else False
        
        match1 = satisfies_criteria(path.name, stat_info, first_op, first_flag, first_val, ignore, args.case, args.fuzzy, content_match1)
        
        if connector:
            match2 = satisfies_criteria(path.name, stat_info, second_op, second_flag, second_val, ignore, args.case, args.fuzzy, content_match2)
            final_match = (match1 or match2) if connector == "or" else (match1 and match2)
        else:
            final_match = match1

        if final_match:
            raw_mtime = stat_info.st_mtime
            raw_size = stat_info.st_size
            date_str = datetime.fromtimestamp(raw_mtime).strftime("%d/%y/%m")
            size_str = readable_size(raw_size)
            matching_files.append([path.name, date_str, size_str, raw_mtime, raw_size, path])
            if args.top and len(matching_files) >= args.top:
                break

    if args.order:
        order_field, order_dir = args.order
        rev = (order_dir == "d")
        if order_field == "name":
            matching_files.sort(key=lambda x: x[0].lower(), reverse=rev)
        elif order_field == "modified":
            matching_files.sort(key=lambda x: x[3], reverse=rev)
        elif order_field == "size":
            matching_files.sort(key=lambda x: x[4], reverse=rev)

    col_order = args.columns.lower() if len(args.columns) == 3 else "dsn"

    for file_info in matching_files:
        name, date, size_str = file_info[0], file_info[1], file_info[2]
        raw_size = file_info[4]

        date_display = f" {date} "
        date_val = highlight(date_display, YELLOW_BG) if first_op == "modified" or second_op == "modified" else date_display
        if args.nocolor: date_val = date_display

        padded_size_str = f"{size_str:>10}"
        if first_op == "size" or second_op == "size":
            size_val = highlight(padded_size_str, YELLOW_BG)
        else:
            size_val = padded_size_str
        
        if not args.nocolor:
            size_val = color_by_size(size_val, raw_size)

        name_display = name
        keywords = [v for v in [first_val, second_val] if v]
        for kw in keywords:
            pattern = re.compile(re.escape(kw), re.IGNORECASE)
            name_display = pattern.sub(lambda m: highlight(m.group(0), YELLOW_BG), name_display)

        path_abs = str(file_info[5].absolute()).replace(os.sep, '/')
        url = f"file:///{path_abs}"
        name_val = file_link(name_display, url)

        row = []
        for char in col_order:
            if char == 'd': row.append(date_val)
            elif char == 's': row.append(size_val)
            elif char == 'n': row.append(name_val)
        
        print(" ".join(row))

    total_size = sum(f[4] for f in matching_files)
    duration = time.perf_counter() - start_time
    print(f"Showing {len(matching_files)} files ({readable_size(total_size)}).")
    print(f"Completed in {duration:.3f}s.")

    if args.exec and matching_files:
        for file_info in matching_files:
            path_abs = str(file_info[5].absolute())
            cmd_parts = [arg.replace('{}', path_abs) for arg in args.exec]
            subprocess.run(" ".join(cmd_parts), shell=True)

    if args.delete_flag and matching_files:
        confirmation = input(f"warning: {len(matching_files)} items will be deleted. Are you sure? (y/n) ")
        if confirmation.lower() == "y":
            for file in matching_files:
                path = file[5]
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            print (f"Deleted {len(matching_files)} items.")

    if args.convert and matching_files:
        new_ext = args.convert if args.convert.startswith(".") else "." + args.convert
        confirmation = input(f"warning: {len(matching_files)} files will be converted to {new_ext}. Are you sure? (y/n) ")
        if confirmation.lower() == "y":
            for file in matching_files:
                old_path = file[5]
                if old_path.is_file():
                    new_path = old_path.with_suffix(new_ext)
                    old_path.rename(new_path)
            print (f"Converted {len(matching_files)} files.")

if __name__ == "__main__":
    main()