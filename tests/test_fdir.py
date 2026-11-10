"""Tests for fdir.py (single-file CLI, no package layout)."""

import datetime
import importlib.util
import os
import sys
from pathlib import Path


def load_fdir():
    path = Path(__file__).resolve().parent.parent / "fdir.py"
    spec = importlib.util.spec_from_file_location("fdir", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_size_units():
    fdir = load_fdir()
    assert fdir.parse_size("10KB") == 10 * 1024
    assert fdir.parse_size("2MB") == 2 * 1024**2
    assert fdir.parse_size("1GB") == 1024**3
    assert fdir.parse_size("100MB") == 100 * 1024**2


def test_readable_size_boundaries():
    fdir = load_fdir()
    assert fdir.readable_size(512) == "512 B"
    assert fdir.readable_size(2048) == "2.0 KB"


def test_listing_date_is_day_month_year(tmp_path, monkeypatch, capsys):
    """Regression: dates were rendered with strftime("%d/%y/%m") (DD/YY/MM)."""
    fdir = load_fdir()
    target = tmp_path / "sample.txt"
    target.write_text("hello")
    mtime = datetime.datetime(2026, 3, 5, 12, 0, 0).timestamp()
    os.utime(target, (mtime, mtime))

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["fdir", "all", "--nocolor"])
    fdir.main()

    out = capsys.readouterr().out
    assert "05/03/26" in out
    assert "05/26/03" not in out
