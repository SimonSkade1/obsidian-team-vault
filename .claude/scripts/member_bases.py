#!/usr/bin/env python3
"""Generate vault-members/<name>.base for every vault-members/<name>.md: me.base as that member sees it.

A copy differs from me.base in one line: `me:` is the member's name instead of `formula.user` (the
user of the device, from _local/me.md). So it shows the same on every device and in
`obsidian base:query`, and its New button makes the member the `owner` and the person pressing it the `reviewer`.
Run after every change to me.base; the nightly review on the automation host runs it too.
Writes only files whose content changes; never deletes (a .base whose member file is gone stays).
"""
import re
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parents[2]
ME_LINE = re.compile(r"^  me: .*$", re.M)

src = (VAULT / "me.base").read_text(encoding="utf-8")
if len(ME_LINE.findall(src)) != 1:
    sys.exit("member_bases: me.base needs exactly one formula line '  me: ...'")
for md in sorted((VAULT / "vault-members").glob("*.md")):
    name = md.stem
    if re.search(r"['\"\\]", name):
        print(f"member_bases: skipped {md.name} (quote or backslash in the name)")
        continue
    text = ME_LINE.sub(lambda _: f"  me: '\"{name.lower()}\"'", src).encode("utf-8")
    out = md.with_suffix(".base")
    if not out.exists() or out.read_bytes() != text:
        out.write_bytes(text)
        print(f"member_bases: wrote {out.relative_to(VAULT)}")
