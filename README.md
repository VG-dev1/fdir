# fdir

**fdir** is a simple command-line utility to list, filter, and sort files and folders in your current directory. It provides a more flexible alternative to Windows's 'dir' command.

[![Latest Release](https://img.shields.io/github/v/release/VG-dev1/fdir)](https://github.com/VG-dev1/fdir/releases)

---

## Features

- List all files and folders in the current directory
- Filter files by:
  - Last modified date (`--gt`, `--lt`)
  - File size (`--gt`, `--lt`)
  - Name keywords (`--keyword`, `--swith`, `--ewith`)
  - File type/extension (`--eq`)
- Sort results by:
  - Name, size, or modification date (`--order <field> <a|d>`)
- Use and/or
- Delete results (`--del`)

## Demo

![Example usage](assets/demo1.png)

## Examples

```bash
fdir modified --gt 1y --order name a
fdir size --lt 100MB --order modified d
fdir name --keyword report --order size a
fdir type --eq .py --order name d
fdir all --order modified a
fdir modified --gt 1y or size --gt 1gb
```

## Usage

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

## Installation

1. Download the "fdir.exe" file from the Releases tab.

2. Create a new folder in %USERPROFILE% on your computer.

3. Paste the downloaded "fdir.exe" file into that folder.

4. Copy the path of that folder.

5. Put the path of that folder into your system's PATH (run `setx PATH "%PATH%;C:\path\to\fdir_folder"` (replace the path with your actual path)).