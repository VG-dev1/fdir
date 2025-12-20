#!/usr/bin/env python3

import sys
from pathlib import Path
from datetime import datetime, timedelta

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
            print (f"error: Unknown time unit: {unit!r}")
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
    
def print_files(matching_files):
    for file in range (len(matching_files)):
        name = matching_files[file][0]
        date = matching_files[file][1]
        size = matching_files[file][2]
        print(f"{name} | {date} | {size}")

def main():
    if len(sys.argv) == 1:
        # No arguments at all
        print("error: No operation entered.")
        print ("suggestion: Type 'fdir help' for a list of commands.")
        sys.exit(1)

    op = sys.argv[1]

    if op == "help":
        usage()
        sys.exit(0)

    def parse_order(args, default_len):
        order_field = None
        order_dir = None
        if len(args) == default_len + 2:
            if args[-2] != "--order" or args[-1] not in ("a", "d", "modified", "name", "size"):
                pass
            else:
                print("error: Invalid --order flag or value.")
                sys.exit(1)
        if len(args) >= default_len + 3:
            if args[-3] != "--order":
                print("error: Invalid --order flag.")
                sys.exit(1)
            order_field = args[-2]
            order_dir = args[-1]
            if order_field not in ("modified", "name", "size") or order_dir not in ("a","d"):
                print("error: Invalid --order value.")
                sys.exit(1)
        return order_field, order_dir

    if op == "modified":
        if len(sys.argv) < 4:
            print("error: The entered operation has invalid arguments.")
            sys.exit(1)

        matching_files = []

        cmp_flag = sys.argv[2]
        time_arg = sys.argv[3]
        file_count = 0

        order_field, order_dir = parse_order(sys.argv, 4)

        if cmp_flag not in ("--gt", "--lt"):
            print("error: The entered flag doesn't exist.")
            sys.exit(1)

        try:
            span = parse_time(time_arg)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            sys.exit(1)

        cutoff = datetime.now() - span

        for path in Path.cwd().iterdir():
            if not (path.is_file() or path.is_dir()):
                continue

            modified = datetime.fromtimestamp(path.stat().st_mtime)

            match_condition = modified <= cutoff if cmp_flag == "--gt" else modified >= cutoff

            name = path.name
            date = modified.strftime("%d/%m/%y")
            size = readable_size(path.stat().st_size)

            if match_condition:
                matching_files.append([name, date, size])
                file_count += 1

        if order_field:
            if order_field == "name":
                matching_files.sort(key=lambda x: x[0].lower(), reverse=(order_dir=="d"))
            elif order_field == "size":
                def size_to_bytes(s):
                    number, unit = s.split()
                    number = float(number)
                    units = ["B","KB","MB","GB","TB","PB"]
                    factor = 1024 ** units.index(unit)
                    return int(number * factor)
                matching_files.sort(key=lambda x: size_to_bytes(x[2]), reverse=(order_dir=="d"))
            elif order_field == "modified":
                matching_files.sort(key=lambda x: datetime.strptime(x[1], "%d/%m/%y"), reverse=(order_dir=="d"))

        print_files(matching_files)
        print (f"Showing {file_count} files.")
        sys.exit(0)
    
    if op == "size":
        if len(sys.argv) < 4:
            print("error: The entered operation has invalid arguments.")
            sys.exit(1)

        matching_files = []

        cmp_flag = sys.argv[2]
        size_arg = sys.argv[3]
        file_count = 0

        order_field, order_dir = parse_order(sys.argv, 4)

        if cmp_flag not in ("--gt", "--lt"):
            print("error: The entered flag doesn't exist.")
            sys.exit(1)

        try:
            cutoff_size = parse_size(size_arg)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            sys.exit(1)

        for path in Path.cwd().iterdir():
            if not (path.is_file() or path.is_dir()):
                continue

            file_size = path.stat().st_size

            if cmp_flag == "--gt":
                match_condition = file_size > cutoff_size
            else:
                match_condition = file_size < cutoff_size

            name = path.name
            date = datetime.fromtimestamp(path.stat().st_mtime)
            date = date.strftime("%d/%m/%y")
            size = readable_size(path.stat().st_size)

            if match_condition:
                matching_files.append([name, date, size])
                file_count += 1

        if order_field:
            if order_field == "name":
                matching_files.sort(key=lambda x: x[0].lower(), reverse=(order_dir=="d"))
            elif order_field == "size":
                def size_to_bytes(s):
                    number, unit = s.split()
                    number = float(number)
                    units = ["B","KB","MB","GB","TB","PB"]
                    factor = 1024 ** units.index(unit)
                    return int(number * factor)
                matching_files.sort(key=lambda x: size_to_bytes(x[2]), reverse=(order_dir=="d"))
            elif order_field == "modified":
                matching_files.sort(key=lambda x: datetime.strptime(x[1], "%d/%m/%y"), reverse=(order_dir=="d"))

        print_files(matching_files)
        print (f"Showing {file_count} files.")
        sys.exit(0)

    if op == "name":
        if len(sys.argv) < 4:
            print("error: The entered operation has invalid arguments.")
            sys.exit(1)

        matching_files = []

        cmp_flag = sys.argv[2]
        name_arg = sys.argv[3]
        file_count = 0

        order_field, order_dir = parse_order(sys.argv, 4)

        if cmp_flag not in ("--keyword", "--swith", "--ewith"):
            print("error: The entered flag doesn't exist.")
            sys.exit(1)

        for path in Path.cwd().iterdir():
            if not (path.is_file() or path.is_dir()):
                continue
            
            name_arg.lower()
            file_name = path.name.lower()
            match_condition = False

            if cmp_flag == "--keyword":
                match_condition = name_arg in file_name
            
            elif cmp_flag == "--swith":
                match_condition = file_name.startswith(name_arg)
                
            elif cmp_flag == "--ewith":
                match_condition = file_name.endswith(name_arg)

            name = path.name
            date = datetime.fromtimestamp(path.stat().st_mtime)
            date = date.strftime("%d/%m/%y")
            size = readable_size(path.stat().st_size)

            if match_condition:
                matching_files.append([name, date, size])
                file_count += 1

        if order_field:
            if order_field == "name":
                matching_files.sort(key=lambda x: x[0].lower(), reverse=(order_dir=="d"))
            elif order_field == "size":
                def size_to_bytes(s):
                    number, unit = s.split()
                    number = float(number)
                    units = ["B","KB","MB","GB","TB","PB"]
                    factor = 1024 ** units.index(unit)
                    return int(number * factor)
                matching_files.sort(key=lambda x: size_to_bytes(x[2]), reverse=(order_dir=="d"))
            elif order_field == "modified":
                matching_files.sort(key=lambda x: datetime.strptime(x[1], "%d/%m/%y"), reverse=(order_dir=="d"))

        print_files(matching_files)
        print (f"Showing {file_count} files.")
        sys.exit(0)

    if op == "type":
        if len(sys.argv) < 4:
            print("error: The entered operation has invalid arguments.")
            sys.exit(1)

        matching_files = []

        cmp_flag = sys.argv[2]
        type_arg = sys.argv[3]
        file_count = 0

        order_field, order_dir = parse_order(sys.argv, 4)

        if cmp_flag not in ("--eq"):
            print("error: The entered flag doesn't exist.")
            sys.exit(1)

        for path in Path.cwd().iterdir():
            if not path.is_file():
                continue

            file_extension = path.suffix
            match_condition = type_arg == file_extension

            name = path.name
            date = datetime.fromtimestamp(path.stat().st_mtime)
            date = date.strftime("%d/%m/%y")
            size = readable_size(path.stat().st_size)

            if match_condition:
                matching_files.append([name, date, size])
                file_count += 1

        if order_field:
            if order_field == "name":
                matching_files.sort(key=lambda x: x[0].lower(), reverse=(order_dir=="d"))
            elif order_field == "size":
                def size_to_bytes(s):
                    number, unit = s.split()
                    number = float(number)
                    units = ["B","KB","MB","GB","TB","PB"]
                    factor = 1024 ** units.index(unit)
                    return int(number * factor)
                matching_files.sort(key=lambda x: size_to_bytes(x[2]), reverse=(order_dir=="d"))
            elif order_field == "modified":
                matching_files.sort(key=lambda x: datetime.strptime(x[1], "%d/%m/%y"), reverse=(order_dir=="d"))

        print_files(matching_files)
        print (f"Showing {file_count} files.")
        sys.exit(0)

    if op == "all":
        if len(sys.argv) < 2:
            print("error: The entered operation has invalid arguments.")
            sys.exit(1)

        matching_files = []

        file_count = 0

        order_field, order_dir = parse_order(sys.argv, 2)

        for path in Path.cwd().iterdir():
            if not (path.is_file() or path.is_dir()):
                continue
            
            # File information
            name = path.name
            date = datetime.fromtimestamp(path.stat().st_mtime)
            date = date.strftime("%d/%m/%y")
            size = readable_size(path.stat().st_size)
            
            matching_files.append([name, date, size])
            file_count += 1

        if order_field:
            if order_field == "name":
                matching_files.sort(key=lambda x: x[0].lower(), reverse=(order_dir=="d"))
            elif order_field == "size":
                def size_to_bytes(s):
                    number, unit = s.split()
                    number = float(number)
                    units = ["B","KB","MB","GB","TB","PB"]
                    factor = 1024 ** units.index(unit)
                    return int(number * factor)
                matching_files.sort(key=lambda x: size_to_bytes(x[2]), reverse=(order_dir=="d"))
            elif order_field == "modified":
                matching_files.sort(key=lambda x: datetime.strptime(x[1], "%d/%m/%y"), reverse=(order_dir=="d"))

        print_files(matching_files)
        print (f"Showing {file_count} files.")
        sys.exit(0)

    # Unknown operation
    print("error: The entered operation doesn't exist.")
    sys.exit(1)

if __name__ == "__main__":
    main()
