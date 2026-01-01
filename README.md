# fdir

**fdir** is a simple command-line utility to list, filter, and sort files and folders in your current directory. It provides a more flexible alternative to Windows's 'dir' command.

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

## Examples

```bash
fdir modified --gt 1y --order name a
fdir size --lt 100MB --order modified d
fdir name --keyword report --order size a
fdir type --eq .py --order name d
fdir all --order modified a
fdir modified --gt 1y or size --gt 1gb
```

## Installation

1. Install via `pip` (Python 3.8+ required):
```bash
pip install fdir
```

2. Download the 'fdir.bat' launcher

3. Place 'fdir.bat' in a folder on your PATH