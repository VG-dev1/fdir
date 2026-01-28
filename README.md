# fdir

![PyPI - Downloads](https://img.shields.io/pypi/dm/fdir-cli)
[![Latest Release](https://img.shields.io/github/v/release/VG-dev1/fdir)](https://github.com/VG-dev1/fdir/releases)
[![GitHub License](https://img.shields.io/github/license/VG-dev1/fdir)](https://github.com/VG-dev1/fdir/blob/main/LICENSE.md)

fdir is the search language for your filesystem - a fast, intuitive way to find, filter, and act on files using human-friendly commands.

[Installation](#installation) • [Usage](#usage)

![Demo](assets/fdir.gif)

## Features

- Intuitive syntax: Use operations like `size` or `modified` instead of complex flags.
- Logical operators: Combine searches with `and` or `or`.
- Deep search: Traverse directories recursively.
- Batch processing: Convert file types or delete results directly from the search.
- Visual feedback: Heatmap coloring for file sizes and highlighting for matched patterns.
- Smart navigation: Includes hyperlinks to open matching files directly from the terminal.

## Usage

You can get a list of all the commands by running `fdir --help`.

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

### Searching for hidden files

fdir doesn't show hidden files by default. To show them, add the `--hidden` flag.

> [!NOTE]
> This only shows files that weren't hidden using a `.fdirignore` file.

### Logical operators

Unlike many search tools, fdir allows you to combine two different operations using `and` or `or`:

```bash
fdir modified --gt 1y or size --gt 1gb
```

### Command execution

Instead of just listing files, you can execute another command for every result found using the `--exec` flag (use `{}` as a placeholder):

```bash
fdir type --eq .jpg --exec echo Hi! {}
```

> [!NOTE]
> On Windows Powershell, you might need to wrap the placeholder in quotes, like this: `'{}'`.

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

Here are all `fdir`'s options (this is the output of `fdir --help`):

```
usage: fdir [-h] [--deep] [--top NUMBER] [--fuzzy] [--case] [--order FIELD DIR] [--columns COLUMNS] [--del]
            [--convert EXTENSION] [--nocolor] [--exec ...] [--hidden]
            {modified,size,name,type,content,all,version} ...

positional arguments:
  {modified,size,name,type,content,all,version}
    modified            Filter by date
    size                Filter by size
    name                Filter by name
    type                Filter by extension
    content             Search inside file content
    all                 List all files
    version             Show version

options:
  -h, --help            show this help message and exit
  --deep                Search recursively
  --top NUMBER          Show only first N results
  --fuzzy               Search approximately
  --case                Case-sensitive search
  --order FIELD DIR     Sort: <name|size|modified> <a|d>
  --columns COLUMNS     Column order (e.g., nds)
  --del                 Delete matches
  --convert EXTENSION   Convert to new extension
  --nocolor             Disable colors
  --exec ...            Execute command (use {} for path)
  --hidden              Show hidden files in search
```

## Installation

### pip

```bash
pip install fdir-cli
```