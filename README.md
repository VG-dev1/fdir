# fdir

![PyPI - Downloads](https://img.shields.io/pypi/dm/fdir-cli)
[![Latest Release](https://img.shields.io/github/v/release/VG-dev1/fdir)](https://github.com/VG-dev1/fdir/releases)
![GitHub Repo stars](https://img.shields.io/github/stars/VG-dev1/fdir)
[![GitHub License](https://img.shields.io/github/license/VG-dev1/fdir)](https://github.com/VG-dev1/fdir/blob/main/LICENSE.md)

`fdir` is a program for finding and organizing anything on your system. It is a simple and user-friendly way to find the files that you need and do something with them.

[Installation](#installation) • [Usage](#usage)

![Demo](https://i.ibb.co/pmXCwZT/demo2.png)

## Features

- Intuitive syntax: Use operations like `size` or `modified` instead of complex flags.
- Logical operators: Combine searches with `and` or `or`.
- Deep search: Traverse directories recursively.
- Batch processing: Convert file types or delete results directly from the search.
- Visual feedback: Heatmap coloring for file sizes and highlighting for matched patterns.
- Smart navigation: Includes hyperlinks to open matching files directly from the terminal.

## Usage

You can get a list of all the commands by running `fdir help`.

### Searching by name

fdir provides specific flags to match filenames. You can search for a keyword anywhere in the name, or specify if the name starts or ends with a pattern:

```bash
fdir name --keyword report
fdir name --swith 2023_
```

Additionally, you can enable fuzzy (typo-tolerant) search using the `--fuzzy` flag:

```bash
fdir name --keyword reprot --fuzzy
```

### Searching for a particular file extension

Use the `type` operation to find files with a specific extension (including the dot):

```bash
fdir type --eq .py
```

### Filtering by modification time

You can filter files based on how long ago they were modified using units like `h` (hours), `d` (days), `w` (weeks), `m` (months), and `y` (years):

```bash
fdir modified --lt 1w
```

### Searching by keywords inside files

You can even look inside files for keywords using the `content` operation:

```bash
fdir content --keyword main
```

> [!NOTE]
> Only supported for textual files.

### Logical operators

Unlike many search tools, fdir allows you to combine two different operations using `and` or `or`:

```bash
fdir modified --gt 1y or size --gt 1gb
```

### Command execution

Instead of just listing files, you can execute another command for every result found using the `--exec` flag:

```bash
fdir type --eq .jpg --exec echo Hi! '{}'
```

### File deletion

You can delete all the matching files using the `--del` flag:

```bash
fdir size --gt 1gb --del
```

### File conversion

The type operation allows you to rename and convert the extensions of all matching files using the `--convert` flag:

```bash
fdir type --eq .wav --convert .mp3
```

### Customizing output

#### Print order

You can sort the matching files using the `--order` flag:

```bash
fdir modified --gt 1y --order modified a
```

#### Column order

You can reorder the output columns using the `--columns` flag with `n` (name), `d` (date), and `s` (size):

```bash
fdir all --columns nsd
```

#### No color output

If you don't want the colored output enabled by default, you can use the `--nocolor` flag:

```bash
fdir all --nocolor
```

### Excluding files

You can create a `.fdirignore` file in the directory you're running `fdir` from to exclude certain file names, directories, or extensions. They're like `.gitignore` files, but used by `fdir`.

### Recursive search

By default, `fdir` doesn't search recursively. To enable that, you can use the `--deep` flag:

```bash
fdir all --deep
```

## Options

Here are all `fdir`'s options (this is the output of `fdir help`):

```
Usage:
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
  --exec <command>         Execute command for each match (use {} for path)
  --nocolor               Disable the output coloring
```

## Installation

### pip

```bash
pip install fdir-cli
```