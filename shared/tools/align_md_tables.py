"""Pad every Markdown table so its pipes line up in the raw text, and list rows that are too wide.

Usage: python3 align_md_tables.py [--check] [--max N] FILE
Rewrites FILE in place (with --check, only reports). Tables inside code fences are left alone.
Prints one line per row over N columns (default 100) as `FILE:LINE: <n> columns`, then a summary line.
Exit status: 0 when every row fits, 1 when some row is too wide, 2 on a usage error.
"""
import argparse
import re
import sys
from pathlib import Path

SEPARATOR_CELL = re.compile(r"^:?-+:?$")


def split_row(line):
    """Cells of one table row. A pipe written `\\|` stays inside its cell."""
    body = line.strip()
    body = body[1:] if body.startswith("|") else body
    body = body[:-1] if body.endswith("|") and not body.endswith("\\|") else body
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", body)]


def is_separator(cells):
    return all(SEPARATOR_CELL.match(c) for c in cells)


def is_table_line(line):
    return line.lstrip().startswith("|")


def align_block(block):
    """Return the rows of one table, padded to a common width per column."""
    rows = [split_row(line) for line in block]
    columns = max(len(r) for r in rows)
    rows = [r + [""] * (columns - len(r)) for r in rows]
    widths = [max(3 if is_separator(r) else len(r[i]) for r in rows) for i in range(columns)]
    widths = [max(w, 3) for w in widths]
    out = []
    for r in rows:
        if is_separator(r):
            cells = []
            for i, c in enumerate(r):
                left, right = c.startswith(":"), c.endswith(":")
                dashes = "-" * (widths[i] - left - right)
                cells.append((":" if left else "") + dashes + (":" if right else ""))
        else:
            cells = [c.ljust(widths[i]) for i, c in enumerate(r)]
        out.append("| " + " | ".join(cells) + " |")
    return out


def align(text):
    lines = text.split("\n")
    result, i, in_fence = [], 0, False
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and is_table_line(line):
            j = i
            while j < len(lines) and is_table_line(lines[j]):
                j += 1
            block = lines[i:j]
            has_separator = any(is_separator(split_row(b)) for b in block[1:2])
            result.extend(align_block(block) if has_separator else block)
            i = j
            continue
        result.append(line)
        i += 1
    return "\n".join(result)


def wide_rows(text, limit):
    found, in_fence = [], False
    for number, line in enumerate(text.split("\n"), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and is_table_line(line) and len(line) > limit:
            found.append((number, len(line)))
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file", type=Path)
    ap.add_argument("--check", action="store_true", help="report only, do not rewrite the file")
    ap.add_argument("--max", type=int, default=100, help="widest allowed table row (default 100)")
    args = ap.parse_args(argv)
    try:
        text = args.file.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"cannot read {args.file}: {exc}", file=sys.stderr)
        return 2
    aligned = align(text)
    misaligned = aligned != text
    if misaligned and not args.check:
        args.file.write_text(aligned, encoding="utf-8")
    wide = wide_rows(aligned, args.max)
    for number, width in wide:
        print(f"{args.file}:{number}: {width} columns")
    if not misaligned:
        state = "pipes aligned"
    else:
        state = "pipes misaligned" if args.check else "pipes were misaligned, now fixed"
    print(f"{len(wide)} rows over {args.max} columns; {state}")
    return 1 if wide or (args.check and misaligned) else 0


if __name__ == "__main__":
    sys.exit(main())
