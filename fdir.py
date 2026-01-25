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
import ctypes

RESET = "\033[0m"
YELLOW_BG = "\033[48;5;136m"
BLUE   = "\033[38;5;39m"
GREEN  = "\033[38;5;82m"
YELLOW = "\033[38;5;226m"
ORANGE = "\033[38;5;214m"
RED    = "\033[38;5;196m"

def version():
    print ("fdir v3.3.0, check the GitHub repo for new updates: https://github.com/VG-dev1/fdir")

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
        if not case_sensitive:
            return path_name.lower().endswith(value.lower())
        return path_name.endswith(value)
    if op == "content":
        return content_found
    return False

def is_hidden(path: Path) -> bool:
    if os.name == "posix":
        if path.name.startswith('.'):
            return True
        return False
    if os.name == 'nt':
        try:
            attrs = os.stat(str(path.absolute())).st_file_attributes
            return bool(attrs & 2)
        except (AttributeError, OSError):
            return False

def main():
    if os.name == 'nt':
        os.system('color')

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--deep", action="store_true", help="Search recursively")
    parent_parser.add_argument("--top", type=int, metavar=('NUMBER'), help="Show only first N results")
    parent_parser.add_argument("--fuzzy", action="store_true", help="Search approximately")
    parent_parser.add_argument("--case", action="store_true", help="Case-sensitive search")
    parent_parser.add_argument("--order", nargs=2, metavar=('FIELD', 'DIR'), help="Sort: <name|size|modified> <a|d>")
    parent_parser.add_argument("--columns", default="dsn", help="Column order (e.g., nds)")
    parent_parser.add_argument("--del", action="store_true", dest="delete_flag", help="Delete matches")
    parent_parser.add_argument("--convert", metavar=('EXTENSION'), help="Convert to new extension")
    parent_parser.add_argument("--nocolor", action="store_true", help="Disable colors")
    parent_parser.add_argument("--exec", nargs=argparse.REMAINDER, help="Execute command (use {} for path)")
    parent_parser.add_argument("--hidden", action="store_true", help="Show hidden files in search")

    parser = argparse.ArgumentParser(
        prog="fdir",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[parent_parser]
    )
    
    subparsers = parser.add_subparsers(dest="operation", required=True)

    mod_p = subparsers.add_parser("modified", parents=[parent_parser], help="Filter by date")
    mod_p.add_argument("--gt", metavar=('TIMESTAMP'), help="Older than (e.g. 2d)")
    mod_p.add_argument("--lt", metavar=('TIMESTAMP'), help="Newer than")

    size_p = subparsers.add_parser("size", parents=[parent_parser], help="Filter by size")
    size_p.add_argument("--gt", metavar=('SIZE'), help="Larger than (e.g. 10MB)")
    size_p.add_argument("--lt", metavar=('SIZE'), help="Smaller than")

    name_p = subparsers.add_parser("name", parents=[parent_parser], help="Filter by name")
    name_p.add_argument("--keyword", metavar=('KEYWORD'), help="Contains pattern")
    name_p.add_argument("--swith", metavar=('KEYWORD'), help="Starts with")
    name_p.add_argument("--ewith", metavar=('KEYWORD'), help="Ends with")

    type_p = subparsers.add_parser("type", parents=[parent_parser], help="Filter by extension")
    type_p.add_argument("--eq", metavar=('EXTENSION'), help="Match extension (e.g. .py)")

    con_p = subparsers.add_parser("content", parents=[parent_parser], help="Search inside file content")
    con_p.add_argument("--keyword", metavar=('KEYWORD'), help="Contains pattern")

    subparsers.add_parser("all", parents=[parent_parser], help="List all files")
    subparsers.add_parser("version", parents=[parent_parser], help="Show version")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args, unknown = parser.parse_known_args()

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
        if not args.hidden:
            hidden = is_hidden(path)
            if hidden:
                continue
        
        display_name = path.name + "/" if path.is_dir() else path.name

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
            matching_files.append([display_name, date_str, size_str, raw_mtime, raw_size, path])
            if args.top and len(matching_files) >= args.top:
                break

    if not matching_files:
        print("No matches found.")
        sys.exit(0)

    sort_map = {"name": lambda x: x[0].lower(), "modified": lambda x: x[3], "size": lambda x: x[4]}
    if args.order:
        field, direction = args.order
        matching_files.sort(key=sort_map.get(field, sort_map["name"]), reverse=(direction == "d"))

    col_order = args.columns.lower() if len(args.columns) == 3 else "dsn"

    max_name_len = max((len(f[0]) for f in matching_files), default=0) + 2
    max_date_len = max((len(f[1]) for f in matching_files), default=0) + 2
    max_size_len = max((len(f[2]) for f in matching_files), default=0) + 2

    max_name_len = max((len(f[0]) for f in matching_files), default=0)
    max_date_len = max((len(f[1]) for f in matching_files), default=0)
    max_size_len = max((len(f[2]) for f in matching_files), default=0)

    for file_info in matching_files:
        name, date, size_str = file_info[0], file_info[1], file_info[2]
        raw_size = file_info[4]

        p_date = f"{date:<{max_date_len}}"
        p_size = f"{size_str:>{max_size_len}}"
        p_name = f"{name:<{max_name_len}}"

        date_val = highlight(p_date, YELLOW_BG) if "modified" in [first_op, second_op] else p_date
        if args.nocolor: date_val = p_date

        size_val = highlight(p_size, YELLOW_BG) if "size" in [first_op, second_op] else p_size
        if not args.nocolor:
            size_val = color_by_size(size_val, raw_size)

        name_display = p_name
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

        print("  ".join(row))

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