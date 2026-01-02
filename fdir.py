#!/usr/bin/env python3

import sys
from pathlib import Path
from datetime import datetime, timedelta
import os

RESET = "\033[0m"
YELLOW = "\033[33m"

def usage():
    print(
        """Usage:
  fdir <operation> [options] [--order <field> <a|d>]

Operations:
  modified (--gt | --lt) <time>      Filter files by last modified date
  size (--gt | --lt) <size>          Filter files by size
  name (--keyword | --swith | --ewith) <pattern>  Filter files by name
  type (--eq) <extension>            Filter files by file extension
  all                                 List all files and directories

Time units for 'modified':
  h   hours
  d   days
  w   weeks
  m   months (approx. 30 days)
  y   years (approx. 365 days)

Size units for 'size':
  B   bytes
  KB  kilobytes
  MB  megabytes
  GB  gigabytes

Name flags for 'name':
  --keyword   Match if filename contains the pattern
  --swith     Match if filename starts with the pattern
  --ewith     Match if filename ends with the pattern

Type flags for 'type':
  --eq        Match exact file extension (include the dot, e.g., .py)

Optional sorting:
  --order <field> <a|d>   Sort the output by the specified field
                           field: name, size, modified
                           a = ascending, d = descending

Examples:
  fdir modified --gt 1y --order name a
  fdir size --lt 100MB --order modified d
  fdir name --keyword report --order size a
  fdir type --eq .py --order name d
  fdir all --order modified a
"""
    )

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

def file_link(text, url):
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"

def print_files(matching_files, first_op, second_op):
    for file_info in matching_files:
        name, date, size = file_info[0], file_info[1], file_info[2]

        ops = [first_op, second_op]
        
        if "modified" in ops:
            date = highlight(date, YELLOW)
        if "size" in ops:
            size = highlight(size, YELLOW)
        if "name" in ops:
            name = highlight(name, YELLOW)

        path = os.path.abspath(file_info[0])
        url = f"file:///{path.replace(os.sep,'/')}"

        linked_name = file_link(name, url)

        print(f"{linked_name} | {date} | {size}")

def delete_files(matching_files):
    for file in matching_files:
        name = file[0]
        os.remove(name)

def satisfies_criteria(path, op, flag, value):
    if op == "all": return True
    if op == "size":
        cutoff = parse_size(value)
        return path.stat().st_size > cutoff if flag == "--gt" else path.stat().st_size < cutoff
    if op == "modified":
        cutoff = datetime.now() - parse_time(value)
        modified = datetime.fromtimestamp(path.stat().st_mtime)
        return modified <= cutoff if flag == "--gt" else modified >= cutoff
    if op == "name":
        name_arg = value.lower()
        file_name = path.name.lower()
        if flag == "--keyword": return name_arg in file_name
        if flag == "--swith": return file_name.startswith(name_arg)
        if flag == "--ewith": return file_name.endswith(name_arg)
    if op == "type":
        return path.suffix == value
    return False

def main():
    if len(sys.argv) == 1:
        print("error: No operation entered.\nsuggestion: Type 'fdir help'.")
        sys.exit(1)

    if sys.argv[1] == "help":
        usage()
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
    if first_op != "all" and first_op in ["modified", "size", "type", "name", "all"]:
        if len(sys.argv) >= 4:
            first_flag = sys.argv[2]
            first_val = sys.argv[3]
            if not (
                (first_op == "modified" and first_flag in ["--gt", "--lt"]) or
                (first_op == "size" and first_flag in ["--gt", "--lt"]) or
                (first_op == "type" and first_flag in ["--eq"]) or
                (first_op == "name" and first_flag in ["--keyword", "--swith", "--ewith"])
            ):
                print("error: Invalid arguments for operation.")
                sys.exit(1)

        else:
            print("error: Missing arguments for operation.")
            sys.exit(1)
    elif first_op == "all":
        pass
    elif first_op not in ["modified", "size", "type", "name", "all"]:
        print("error: Invalid operation.")
        sys.exit(1)

    second_op, second_flag, second_val = None, None, None
    if connector:
        conn_idx = sys.argv.index(connector)
        second_op = sys.argv[conn_idx + 1]
        second_flag = sys.argv[conn_idx + 2]
        second_val = sys.argv[conn_idx + 3]

    matching_files = []
    for path in Path.cwd().iterdir():
        if not (path.is_file() or path.is_dir()): continue
        
        match1 = satisfies_criteria(path, first_op, first_flag, first_val)
        
        if connector:
            match2 = satisfies_criteria(path, second_op, second_flag, second_val)
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

    if order_field:
        rev = (order_dir == "d")
        if order_field == "name":
            matching_files.sort(key=lambda x: x[0].lower(), reverse=rev)
        elif order_field == "modified":
            matching_files.sort(key=lambda x: x[3], reverse=rev)
        elif order_field == "size":
            matching_files.sort(key=lambda x: x[4], reverse=rev)

    print_files(matching_files, first_op, second_op)
    if "--del" in sys.argv:
        delete_files(matching_files)
        print (f"Deleted {len(matching_files)} files.")
    
    total = 0
    for file in matching_files:
        total += file[4]
    total = str(readable_size(total))
    print(f"Showing {len(matching_files)} files ({total}).")

if __name__ == "__main__":
    main()