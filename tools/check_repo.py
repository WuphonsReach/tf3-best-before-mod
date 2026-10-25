#!/usr/bin/env python3
"""Cheap consistency checks for the repo; exit code 1 if any fails. Runs in CI (.github/workflows/checks.yml) and by hand.

Checks: the mod's JSON files parse, mod.io_fileid.txt is present, modVersion matches the top CHANGELOG entry, settings.tl's
curve equals the mod.json defaults, and settings.tl ships logLevel "summary", billing "ticket" and ticketPriceProbe "off".
"""
import json
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
mod = root / "best_before_1"
failures = []


def fail(msg):
    failures.append(msg)
    print(f"FAIL  {msg}")


def ok(msg):
    print(f"PASS  {msg}")


# The JSON files the game and the uploader read.
loaded = {}
for rel in ("mod.json", "_content.json", "_metadata/modinfo.json"):
    try:
        loaded[rel] = json.loads((mod / rel).read_text())
        ok(f"{rel} parses")
    except (OSError, ValueError) as e:
        fail(f"{rel} does not parse: {e}")

# Without the id file the uploader creates a second mod.
fileid = mod / "_metadata" / "mod.io_fileid.txt"
if fileid.is_file() and fileid.read_text().strip().isdigit():
    ok("mod.io_fileid.txt holds a mod id")
else:
    fail("_metadata/mod.io_fileid.txt is missing or not a number (the next upload would create a second mod)")

# modVersion in mod.script.tl against the newest changelog entry ("## 1.2 (not released)" for modVersion "1.2-dev").
m = re.search(r'^local modVersion = "([^"]+)"', (mod / "content/mod.script.tl").read_text(), re.M)
h = re.search(r"^## (\S+)", (root / "CHANGELOG.md").read_text(), re.M)
if not m or not h:
    fail("could not find modVersion in mod.script.tl or the top heading in CHANGELOG.md")
else:
    version = m.group(1)
    base = version.removesuffix("-dev")
    if h.group(1) == base:
        ok(f"modVersion {version} matches the top CHANGELOG entry {h.group(1)}")
    else:
        fail(f"modVersion {version} does not match the top CHANGELOG entry {h.group(1)}")

# settings.tl's curve is the fallback and must equal the mod.json defaults (the slider position as a number).
settings = {k: v for k, v in re.findall(r"^\t(\w+) = ([^,\n]+),", (mod / "content/settings.tl").read_text(), re.M)}
if "mod.json" in loaded:
    default = {}
    for p in loaded["mod.json"]["params"]:
        default[p["key"].removeprefix("bestBefore.")] = int(p["values"][p["defaultIndex"]].rstrip("%")) / 100
    expected = {
        "bonusPercent": default["freshPay"] - 1,
        "bonusDownToFreshness": default["bonusDownTo"],
        "breakevenFreshness": default["breakeven"],
        "penaltyBelowFreshness": default["penaltyBelow"],
        "penaltyPercent": default["spoiledPay"] - 1,
        "staleBelowFreshness": default["staleBelow"],
    }
    for name, want in expected.items():
        try:
            got = float(settings[name])
        except (KeyError, ValueError):
            fail(f"settings.tl has no number for {name}")
            continue
        if abs(got - want) > 1e-9:
            fail(f"settings.tl {name} = {got:g} but the mod.json default is {want:g}")
    if not any("settings.tl" in f for f in failures):
        ok("settings.tl curve equals the mod.json defaults")

# A test value of logLevel must not ship.
if settings.get("logLevel") == '"summary"':
    ok('settings.tl logLevel is "summary"')
else:
    fail(f'settings.tl logLevel is {settings.get("logLevel")}, the shipped value is "summary"')

# Nor a test billing or probe setting.
for name, shipped in (("billing", '"ticket"'), ("ticketPriceProbe", '"off"')):
    if settings.get(name) == shipped:
        ok(f"settings.tl {name} is {shipped}")
    else:
        fail(f"settings.tl {name} is {settings.get(name)}, the shipped value is {shipped}")

sys.exit(1 if failures else 0)
