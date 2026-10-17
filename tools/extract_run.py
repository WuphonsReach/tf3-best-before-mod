#!/usr/bin/env python3
"""Cut a test run out of a raw game log into three small files that the analysis tools can read.

Usage: tools/extract_run.py [--out local/runs] [--slug name] [--note text] local/logs/stdout-<date>-<time>[-slug].txt [...]

Reads the lines after the last `BEST_BEFORE preRunFn` (the same slice tools/verify_run.py and tools/replay_curve.py use)
and writes, named after the log (`<date>-<time>` first, then the slug):

  <name>.arrivals.csv   one row per `BEST_BEFORE arrival` line (the inputs of the curve; blank where an older probe did not log a field)
  <name>.journal.csv    one row per `BEST_BEFORE journal` snapshot: seq, t, playerBalance, playerIncomeTotal (the per-entity ledgers are left out)
  <name>.json           the run's facts: source log, save, the save's header settings, the mod's curve settings, the company line,
                        counts and totals, and your note

Logs of the same save overlap, and a rerun of one log gives identical files. The raw log stays the source for
tools/verify_run.py (it needs the sending lines and the error lines); replay_curve.py reads the arrivals file directly.
"""
import argparse
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ARRIVAL_COLUMNS = ["now", "unit", "cargoType", "carrier", "legs", "source", "target", "startTime", "pickupTime", "ext", "ageMs",
                   "limitMs", "freshness", "corrected", "good", "rate", "predictedIncome", "deduction", "bonus",
                   "vehicle", "line", "lastVehicle", "lastLine", "chain"]
SAVE_FORMAT_TOOLS = os.path.join(HERE, "..", "..", "tf3-save-format", "tools")
SAVE_DIR_GLOB = os.path.expanduser("~/snap/steam/common/.local/share/Steam/userdata")


def kv(text):
    return dict(re.findall(r'(\w+)=("[^"]*"|\S+)', text))


def log_time(line):
    m = re.match(r"\[(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d)Z", line)
    return f"{m.group(1)}T{m.group(2)}Z" if m else None


def save_header(save_name):
    """The header settings of the named save (cargoIncome, inflationFactor ...), or None when the file or the reader is missing."""
    try:
        sys.path.insert(0, SAVE_FORMAT_TOOLS)
        from save_header import read_header
        for user in os.listdir(SAVE_DIR_GLOB):
            path = os.path.join(SAVE_DIR_GLOB, user, "3493540", "local", "save", save_name + ".sav")
            if os.path.exists(path):
                head = read_header(path)
                return {"file": os.path.basename(path), "settings": head.get("settings")}
    except Exception as e:                              # optional: the run is still extracted
        return {"error": str(e)}
    return None


def extract(path, out_dir, slug, note, min_arrivals):
    lines = open(path, errors="replace").read().splitlines()
    start = max((i for i, ln in enumerate(lines) if "BEST_BEFORE preRunFn" in ln), default=0)
    stem = re.sub(r"^stdout-", "", os.path.splitext(os.path.basename(path))[0])
    if slug:
        stem = re.sub(r"^(\d{8}-\d{4}).*", r"\1", stem) + "-" + slug
    save = None
    for ln in lines:
        m = re.search(r"Loading game from file (.+?)\s*$", ln)
        if m:
            save = m.group(1)                           # the last load is the one the slice follows

    arrivals, journal, company, settings, sends, errors = [], [], None, None, [0, 0], 0
    for ln in lines[start:]:
        if " - ERROR " in ln or "Error message" in ln:
            errors += 1
        m = re.search(r"BEST_BEFORE (\w+) ?(.*)", ln)
        if not m:
            continue
        kind, rest = m.groups()
        if kind == "arrival":
            d = kv(rest)
            arrivals.append({c: d.get(c, "").strip('"') if c != "predictedIncome" or d.get(c) != "n/a" else "" for c in ARRIVAL_COLUMNS})
        elif kind == "journal":
            seq = re.match(r"#(\d+)", rest)
            vals = dict(re.findall(r"(\w+)=(-?\d+)", rest.split(" ", 1)[1]))
            journal.append({"seq": seq.group(1), "t": vals.get("t", ""), "playerBalance": vals.get("playerBalance", ""),
                            "playerIncomeTotal": vals.get("playerIncomeTotal", "")})
        elif kind == "company" and company is None:
            company = kv(rest)
        elif kind == "settings" and settings is None:
            settings = kv(rest)
        elif kind == "sending":
            d = kv(rest)
            sends[0] += 1
            sends[1] += int(d.get("units", 0))

    priced = [a for a in arrivals if a["predictedIncome"]]
    if len(priced) < min_arrivals:
        print(f"{os.path.basename(path)}: {len(priced)} priced arrivals after the last load (under {min_arrivals}), skipped")
        return
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, stem)
    for suffix, rows, cols in (("arrivals", arrivals, ARRIVAL_COLUMNS), ("journal", journal, ["seq", "t", "playerBalance", "playerIncomeTotal"])):
        with open(f"{base}.{suffix}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, cols)
            w.writeheader()
            w.writerows(rows)

    pred = sum(float(a["predictedIncome"]) for a in priced)
    ded = sum(int(a["deduction"] or 0) for a in priced)
    bon = sum(int(a["bonus"] or 0) for a in priced)
    meta = {"name": stem, "sourceLog": os.path.basename(path), "loadedAtUtc": log_time(lines[start]), "lastLineAtUtc": log_time(lines[-1]),
            "save": save, "saveHeader": save_header(save) if save else None, "modSettings": settings, "company": company,
            "arrivals": len(arrivals), "pricedArrivals": len(priced), "journalSnapshots": len(journal),
            "adjustmentEntriesSent": sends[0], "unitsInSentEntries": sends[1], "errorLines": errors,
            "predictedIncomeTotal": round(pred), "loggedBonusTotal": bon, "loggedDeductionTotal": -ded,
            "loggedNetPercentOfPredicted": round(100 * (bon - ded) / pred, 2) if pred else None,
            "note": note or None}
    with open(f"{base}.json", "w") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")
    print(f"{stem}: {len(arrivals)} arrivals, {len(journal)} snapshots, net {meta['loggedNetPercentOfPredicted']}% -> {base}.*")


def main():
    ap = argparse.ArgumentParser(description="Extract a run's arrivals, journal and facts from a raw game log.")
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "local", "runs"))
    ap.add_argument("--slug", help="replace the log name's suffix (only for a single log)")
    ap.add_argument("--min-arrivals", type=int, default=100, help="skip runs with fewer priced arrivals (default 100)")
    ap.add_argument("--note", help="free text kept in the json (for example: no-mod control)")
    a = ap.parse_args()
    if a.slug and len(a.logs) > 1:
        sys.exit("--slug takes a single log")
    for log in a.logs:
        extract(log, os.path.normpath(a.out), a.slug, a.note, a.min_arrivals)


if __name__ == "__main__":
    main()
