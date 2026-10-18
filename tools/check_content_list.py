#!/usr/bin/env python3
"""Check that best_before_1/_content.json lists every file under best_before_1/content/ and nothing else.

The game builds the mod's file index from that list: a file that is on disk but not in the list cannot be loaded
(1.0 shipped without settings.tl in it and the game refused to start). Run before every upload; exit code 1 on a mismatch.
"""
import json
import sys
from pathlib import Path

mod = Path(__file__).resolve().parent.parent / "best_before_1"
listed = set(json.loads((mod / "_content.json").read_text())["files"])
on_disk = {str(p.relative_to(mod / "content")) for p in (mod / "content").rglob("*") if p.is_file()}

missing = sorted(on_disk - listed)
stale = sorted(listed - on_disk)
for name in missing:
    print(f"FAIL  {name} is in content/ but not in _content.json (the game cannot load it)")
for name in stale:
    print(f"FAIL  {name} is in _content.json but not in content/")
if missing or stale:
    sys.exit(1)
print(f"PASS  _content.json lists all {len(on_disk)} files under content/")
