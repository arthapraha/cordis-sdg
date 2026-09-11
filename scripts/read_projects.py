#!/usr/bin/env python3
"""Read project.csv correctly, including the 193 rows a standard CSV reader breaks.

Registration v9 72187842d621e55dedb6c6b366356131141cd47acf3324ab26bc7f06293c341c.

THE PROBLEM. CORDIS's export under-escapes a field whose content BEGINS with a
quotation mark. A project whose abstract opens with one is written

    ;"";""Deep Learning (DL) has reached unparalleled performance...

where the objective needs three quote characters and has two. A standard reader
sees an opening quote, an immediate closing quote, an empty field, and then prose
outside any quotes, which it splits on every ";" inside the abstract. 193 of the
23,451 rows are affected. Quotes ELSEWHERE in the same field are escaped
correctly, so this is specifically a field whose content starts with one.

THE FIX IS NOT A REPAIR, IT IS A CORRECT PARSE. The first approach tried here was
to detect broken rows and rejoin the split fields, choosing the join point by
validating the row's shape. That cannot work and the reason is worth keeping:
absorbing any two adjacent free-text fields shifts the tail identically, so
joining at `masterCall` and joining at `objective` both leave a row whose dates,
rcn and status all validate. Every one of the 193 had five or more shape-valid
join points. A check that cannot distinguish the right answer from four wrong
ones is not a check.

What works is reading the file the way it is actually written. EVERY field in
this export is wrapped in quotes and separated by ";", so the field separator is
the literal three-character sequence ";" between quotes, not the semicolon. Split
on that, strip the outer quotes of the line, and un-double the internal quotes.
Measured against the snapshot: all 23,451 body rows yield exactly 22 fields, with
no exceptions and no heuristics. The malformed rows stop being a special case
because under this reading they were never malformed.

This module is the one place project text is read. Nothing else opens
project.csv.
"""

import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "data/raw/cordis-horizon-projects/project.csv"

SEP = '";"'


def _fields(line):
    line = line.rstrip("\r")
    if line.startswith('"'):
        line = line[1:]
    if line.endswith('"'):
        line = line[:-1]
    return [f.replace('""', '"') for f in line.split(SEP)]


def load(path=PROJECTS):
    """Return (header, rows). Every row has exactly len(header) fields or we stop.

    Refusing to return a partially understood file is deliberate: a reader that
    silently drops rows is how 193 projects went missing from a population count
    that was then reported three times.
    """
    if not path.is_file():
        sys.exit("missing projects extract: %s" % path)
    text = path.read_text(encoding="utf-8", newline="")
    lines = [ln for ln in text.split("\n") if ln.strip()]
    header = _fields(lines[0])
    rows = []
    for n, line in enumerate(lines[1:], start=2):
        row = _fields(line)
        if len(row) != len(header):
            sys.exit("line %d parsed to %d fields, expected %d — the reader does "
                     "not understand this file and will not guess" %
                     (n, len(row), len(header)))
        rows.append(row)
    return header, rows


def as_dicts(path=PROJECTS):
    header, rows = load(path)
    return [dict(zip(header, r)) for r in rows]


def csv_module_disagreements(path=PROJECTS):
    """Which rows a standard csv.reader gets wrong. Used by the notebook and the
    verifier, so the claim "193 rows" is measured rather than asserted."""
    import csv
    csv.field_size_limit(1 << 30)
    with open(path, encoding="utf-8", newline="") as fh:
        r = csv.reader(fh, delimiter=";")
        head = next(r)
        broken = {row[0] for row in r if len(row) != len(head)}
    return broken


def main():
    header, rows = load()
    broken = csv_module_disagreements()
    ids = [r[0] for r in rows]
    print("header fields:", len(header))
    print("rows:", len(rows), " distinct ids:", len(set(ids)))
    print("rows a standard csv.reader breaks:", len(broken))
    obj = header.index("objective")
    have = sum(1 for r in rows if r[obj].strip())
    print("rows with a non-empty objective:", have)
    if broken:
        sample = next(r for r in rows if r[0] in broken)
        print("example repaired row:", sample[0],
              "objective is %d chars, starts %r" % (len(sample[obj]), sample[obj][:60]))
    digest = hashlib.sha256("\n".join(sorted(set(ids))).encode()).hexdigest()
    print("sha256 over the sorted distinct id list:", digest)


if __name__ == "__main__":
    main()
