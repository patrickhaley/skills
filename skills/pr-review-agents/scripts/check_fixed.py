#!/usr/bin/env python3
"""Check that an installed file keeps the template's fixed text.

Everything outside `<!-- FILL: ... -->` markers must appear in the installed file, in order.
Whitespace differences are ignored. FILL regions may hold anything, including nothing.

Usage: check_fixed.py TEMPLATE INSTALLED [TEMPLATE INSTALLED ...]
Exit status is 1 if any file drifted from its template.
"""
import re
import sys

FILL = re.compile(r"<!--\s*FILL:.*?-->", re.S)


def norm(text: str) -> str:
    return " ".join(text.split())


def divergence(chunk: str, installed: str, start: "int | None") -> str:
    """Describe where a fixed chunk stops matching the installed text."""
    if start is None:  # locate the chunk by its opening words
        start = installed.find(chunk[:40])
        if start == -1:
            return f"fixed text missing entirely:\n  template:  {chunk[:120]}"
    n = 0
    while n < len(chunk) and start + n < len(installed) and chunk[n] == installed[start + n]:
        n += 1
    lo = max(0, n - 40)
    return (
        "fixed text differs:\n"
        f"  template:  ...{chunk[lo:n + 80]}\n"
        f"  installed: ...{installed[start + lo:start + n + 80]}"
    )


def check(template_path: str, installed_path: str) -> bool:
    template = open(template_path, encoding="utf-8").read()
    installed = norm(open(installed_path, encoding="utf-8").read())
    chunks = [norm(c) for c in FILL.split(template)]
    pos = 0
    for i, chunk in enumerate(chunks):
        if not chunk:
            continue
        found = installed.find(chunk, pos)
        anchored_start = i == 0 and found != 0
        if found == -1 or anchored_start:
            print(f"DRIFT {installed_path}: {divergence(chunk, installed, pos if i == 0 else None)}")
            return False
        pos = found + len(chunk)
    if chunks[-1] and pos != len(installed):
        print(f"DRIFT {installed_path}: extra text after the template's last fixed line")
        return False
    print(f"ok    {installed_path}")
    return True


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or len(args) % 2:
        sys.exit(__doc__)
    results = [check(args[i], args[i + 1]) for i in range(0, len(args), 2)]
    sys.exit(0 if all(results) else 1)
