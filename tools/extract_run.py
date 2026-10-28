#!/usr/bin/env python3
"""Cut a test run out of a raw game log into three small files that the analysis tools can read.

Usage: tools/extract_run.py [--out local/runs] [--slug name] [--note text] local/logs/stdout-<date>-<time>[-slug].txt [...]

Reads the lines after the last `BEST_BEFORE preRunFn` (the same slice tools/verify_run.py and tools/replay_curve.py use)
and writes, named after the log (`<date>-<time>` first, then the slug):

  <name>.arrivals.csv   one row per `BEST_BEFORE arrival` line (the inputs of the curve; blank where an older probe did not log a field).
                        `predictedIncome` is as logged; `predictedCorrected` is the pay prediction at the right scale (see below) and is
                        what tools/replay_curve.py reads
  <name>.journal.csv    one row per `BEST_BEFORE journal` snapshot: seq, t, playerBalance, playerIncomeTotal (the per-entity ledgers are left out)
  <name>.json           the run's facts: source log, save, the save's header settings, the curve the run was played on (`curve`, read
                        from the `loadParams` line, which tools/replay_curve.py replays on), the company line, counts and totals,
                        and your note

Pay scale. The engine pays (price x distance) x difficultyFactor (the Cargo Income option) x ticketPriceMultiplier (the Inflation
option, set from the earned rank). The first probes logged a prediction with a fixed 0.96426 (Normal, rank 3) instead, which is
wrong on any other save. A probe from commit c976cfd on logs `payScale=` per arrival, and that value is used as it stands
(`scaleSource` "logged"). For older logs the scale is rebuilt from the save the run loaded: difficultyFactor from the header's
Cargo Income setting and the multiplier stored in the save's company state, and `predictedCorrected` = predictedIncome x scale /
0.96426 (`scaleSource` "save"). The multiplier is worked out from the earned rank at the start of the run (1 + (rank - 1) x
(f - 1) / 14, f from the Inflation option; the stored value can be stale); autosaves written during the run are read too and
`multiplierDuringRun` lists them, so a rank-up inside a run shows up there. With no save found nothing is corrected
(`scaleSource` "none").

Logs of the same save overlap, and a rerun of one log gives identical files. The raw log stays the source for
tools/verify_run.py (it needs the ticket lines and the error lines); replay_curve.py reads the arrivals file directly.
"""
import argparse
import calendar
import csv
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OLD_PROBE_SCALE = 0.96426                              # the fixed factor logs before c976cfd predicted with
INFLATION_AT_TYCOON = {1: 1.0, 2: 0.9, 3: 0.75, 4: 0.6, 5: 0.5}     # Inflation option -> multiplier reached at rank 15 (604); tf3-save-format docs/inflation.md
CARGO_INCOME_FACTORS = {1: 0.5, 2: 0.75, 3: 1.0, 4: 1.25, 5: 1.5}   # the header stores the list position; tf3-save-format docs/settings.md
ARRIVAL_COLUMNS = ["now", "unit", "cargoType", "carrier", "legs", "source", "target", "startTime", "pickupTime", "ext", "ageMs",
                   "limitMs", "limitFrom", "fileSeconds", "perishable", "billing", "freshness", "corrected", "good", "rate", "payScale", "predictedIncome", "predictedCorrected", "deduction", "bonus",
                   "vehicle", "line", "lastVehicle", "lastLine", "chain"]
SAVE_FORMAT_TOOLS = os.path.join(HERE, "..", "..", "tf3-save-format", "tools")
SAVE_DIR_GLOB = os.path.expanduser("~/snap/steam/common/.local/share/Steam/userdata")
sys.path.insert(0, SAVE_FORMAT_TOOLS)
sys.path.insert(0, HERE)
from replay_curve import curve_from_lines               # the curve a run was played on, shared with the replay
try:                                                    # the sibling repo's readers; without them runs are extracted uncorrected
    from save_header import read_header
    from tf3save import date_of_day, decompress, script_state
except ImportError:
    read_header = decompress = script_state = date_of_day = None


def kv(text):
    return dict(re.findall(r'(\w+)=("[^"]*"|\S+)', text))


def log_time(line):
    m = re.match(r"\[(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d)Z", line)
    return f"{m.group(1)}T{m.group(2)}Z" if m else None


def save_dirs():
    return [os.path.join(SAVE_DIR_GLOB, user, "3493540", "local", "save") for user in os.listdir(SAVE_DIR_GLOB)]


def find_save(save_name, loaded_epoch):
    """The .sav the run loaded: the file named in the log, else the first dated save of that name written after the load
    (the game keeps the loaded name, the files carry a time stamp)."""
    for folder in save_dirs():
        exact = os.path.join(folder, save_name + ".sav")
        if os.path.exists(exact):
            return exact
        later = sorted((os.path.getmtime(os.path.join(folder, f)), f) for f in os.listdir(folder)
                       if f.startswith(save_name + " ") and f.endswith(".sav"))
        later = [f for m, f in later if loaded_epoch is None or m >= loaded_epoch - 5]
        if later:
            return os.path.join(folder, later[0])
    return None


def company_state(data):
    """level, potentialLevel, experience and the stored ticketPriceMultiplier (absent at rank 1 or Inflation None) of a decoded save."""
    prog = script_state(data, "game_mechanics/company/company_progression.gs") or {}
    states = [st for st in (prog.get("companyState") or {}).values() if isinstance(st, dict)]
    if not states:
        return None
    st = states[0]
    return {"level": st.get("level"), "potentialLevel": st.get("potentialLevel"), "experience": st.get("experience"),
            "ticketPriceMultiplier": st.get("ticketPriceMultiplier")}


def save_context(save_name, loaded_epoch, last_epoch):
    """Everything the pay scale needs from the save the run loaded: header settings, company state at the start, and the
    multiplier of every other save written while the run lasted (a rank-up inside the run shows there)."""
    if read_header is None:
        return {"error": "tf3-save-format tools not found"}
    try:
        path = find_save(save_name, loaded_epoch)
        if path is None:
            return None
        data = decompress(open(path, "rb").read())
        head = read_header(path, data=data)
        ctx = {"file": os.path.basename(path), "settings": head.get("settings"), "gameDate": str(date_of_day(head["game_date"])),
               "company": company_state(data), "multiplierDuringRun": []}
        folder = os.path.dirname(path)
        for f in sorted(os.listdir(folder)):
            full = os.path.join(folder, f)
            if f.endswith(".sav") and full != path and loaded_epoch and loaded_epoch - 5 <= os.path.getmtime(full) <= last_epoch + 60 \
                    and save_name.split(" ")[0] in f:
                later = company_state(decompress(open(full, "rb").read()))
                if later:
                    ctx["multiplierDuringRun"].append({"file": f, "potentialLevel": later["potentialLevel"],
                                                       "ticketPriceMultiplier": later["ticketPriceMultiplier"]})
        return ctx
    except Exception as e:                              # optional: the run is still extracted, uncorrected
        return {"error": str(e)}


def epoch_of(iso):
    return iso and calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))


def rank_multiplier(rank, inflation_index):
    """The ticket price multiplier for an earned rank: 1 + (rank - 1) x (f - 1) / 14, f from the Inflation option."""
    return 1.0 + (rank - 1) * (INFLATION_AT_TYCOON[inflation_index] - 1.0) / 14.0


def pay_scale_of(ctx):
    """difficultyFactor x ticket price multiplier, from the save's header settings and earned rank, or None when unreadable.
    The multiplier is worked out from `potentialLevel` (the stored `ticketPriceMultiplier` equals it on every save checked)
    so a save without the stored key still works."""
    if not ctx or ctx.get("company") is None or not ctx.get("settings"):
        return None
    settings = ctx["settings"]
    return CARGO_INCOME_FACTORS[int(settings.get("advancedOptions.cargoIncome", 3))] \
        * rank_multiplier(int(ctx["company"]["potentialLevel"]), int(settings.get("advancedOptions.inflationFactor", 3)))


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

    arrivals, journal, company, settings, curve_notes, sends, errors = [], [], None, None, [], [0, 0], 0
    load_params = None
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
        elif kind == "settings" and settings is None and not rest.startswith(".tl "):   # not "settings.tl could not be loaded"
            settings = kv(rest)
        elif kind == "loadParams":                      # the in-game settings the load started with, as list positions
            load_params = rest
        elif kind == "curveSettings":                   # the curve a save actually used; settings.tl may differ once the game hands the mod its in-game settings
            curve_notes.append(rest)
        elif kind == "sending":
            d = kv(rest)
            sends[0] += 1
            sends[1] += int(d.get("units", 0))

    priced = [a for a in arrivals if a["predictedIncome"]]
    if len(priced) < min_arrivals:
        print(f"{os.path.basename(path)}: {len(priced)} priced arrivals after the last load (under {min_arrivals}), skipped")
        return

    loaded_at, last_at = log_time(lines[start]), log_time(lines[-1])
    ctx = save_context(save, epoch_of(loaded_at), epoch_of(last_at)) if save else None
    rebuilt = pay_scale_of(ctx)
    sources = set()
    for a in arrivals:
        if not a["predictedIncome"]:
            continue
        if a["payScale"]:                               # the probe logged the scale it used: the prediction is right as it stands
            a["predictedCorrected"] = a["predictedIncome"]
            sources.add("logged")
        elif rebuilt is not None:
            a["predictedCorrected"] = repr(float(a["predictedIncome"]) * rebuilt / OLD_PROBE_SCALE)
            a["payScale"] = ""
            sources.add("save")
        else:
            a["predictedCorrected"] = a["predictedIncome"]
            sources.add("none")
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, stem)
    for suffix, rows, cols in (("arrivals", arrivals, ARRIVAL_COLUMNS), ("journal", journal, ["seq", "t", "playerBalance", "playerIncomeTotal"])):
        with open(f"{base}.{suffix}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, cols)
            w.writeheader()
            w.writerows(rows)

    curve, curve_source = curve_from_lines(lines[start:])
    if curve_source == "loadParams" and curve_notes:    # the probe's own note of the curve in force should agree with it
        noted = curve_from_lines([f"BEST_BEFORE curveSettings {curve_notes[-1]}"])[0]
        if noted and any(noted[k] != curve[k] if isinstance(curve[k], str) else abs(noted[k] - curve[k]) > 1e-9 for k in curve):
            print(f"  warning: the last curveSettings line ({curve_notes[-1]}) differs from the loadParams curve {curve}")
    if curve is None:
        print("  note: no loadParams or curveSettings line, so the curve this run was played on is unknown (replay_curve.py uses settings.tl)")
    pred = sum(float(a["predictedIncome"]) for a in priced)
    corrected = sum(float(a["predictedCorrected"]) for a in priced)
    ded = sum(int(a["deduction"] or 0) for a in priced)
    bon = sum(int(a["bonus"] or 0) for a in priced)
    meta = {"name": stem, "sourceLog": os.path.basename(path), "loadedAtUtc": loaded_at, "lastLineAtUtc": last_at,
            "save": save, "saveContext": ctx, "scaleSource": "/".join(sorted(sources)),
            "payScaleRebuilt": rebuilt, "modSettings": settings, "loadParams": load_params, "curve": curve, "curveSource": curve_source,
            "curveSettings": curve_notes, "company": company,
            "arrivals": len(arrivals), "pricedArrivals": len(priced), "journalSnapshots": len(journal),
            "adjustmentEntriesSent": sends[0], "unitsInSentEntries": sends[1], "errorLines": errors,
            "predictedIncomeTotal": round(pred), "predictedCorrectedTotal": round(corrected),
            "loggedBonusTotal": bon, "loggedDeductionTotal": -ded,
            "loggedNetPercentOfPredicted": round(100 * (bon - ded) / pred, 2) if pred else None,
            "note": note or None}
    with open(f"{base}.json", "w") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")
    print(f"{stem}: {len(arrivals)} arrivals, {len(journal)} snapshots, net {meta['loggedNetPercentOfPredicted']}%, scale {meta['scaleSource']}"
          f" (predicted pay x{corrected / pred:.3f}) -> {base}.*")
    if ctx and ctx.get("company") and any(m["potentialLevel"] != ctx["company"]["potentialLevel"] for m in ctx["multiplierDuringRun"]):
        print("  note: the earned rank changed inside this run (see multiplierDuringRun in the json); the scale is the start rank's")


def run_span(out_dir, name):
    """(first clock, last clock, the set of source>target pairs) of an extracted run's arrivals."""
    clocks, pairs = [], set()
    for row in csv.DictReader(open(os.path.join(out_dir, name + ".arrivals.csv"), newline="")):
        if row["now"]:
            clocks.append(int(row["now"]))
        pairs.add((row["source"], row["target"]))
    return (min(clocks), max(clocks), pairs) if clocks else None


def same_start(a, b):
    """Two runs replay the same deliveries when their clocks overlap and most of their source>target pairs are shared. A save is
    often replayed from one starting point (another curve, a performance check, a copy with other game settings) under
    another file name, so the file name cannot tell."""
    if a is None or b is None or a[1] < b[0] or b[1] < a[0]:
        return False
    return len(a[2] & b[2]) >= 0.5 * min(len(a[2]), len(b[2]))


def write_index(out_dir):
    """index.csv: one row per extracted run, so the runs can be picked without opening each json. Runs from the same starting
    point replay the same deliveries, so they form one `start` group (named after its largest run) and only that largest run is
    marked `primary` (pool those)."""
    rows = []
    for name in sorted(f for f in os.listdir(out_dir) if f.endswith(".json")):
        m = json.load(open(os.path.join(out_dir, name)))
        ctx = m.get("saveContext") or {}
        settings, company = ctx.get("settings") or {}, ctx.get("company") or {}
        rows.append({"name": m["name"], "save": ctx.get("file") or m.get("save"), "gameDate": ctx.get("gameDate"),
                     "earnedRank": company.get("potentialLevel"), "claimedRank": company.get("level"),
                     "cargoIncome": settings.get("advancedOptions.cargoIncome"), "inflation": settings.get("advancedOptions.inflationFactor"),
                     "arrivals": m["pricedArrivals"], "scaleSource": m["scaleSource"],
                     "payScale": m["payScaleRebuilt"], "predictedCorrectedTotal": m["predictedCorrectedTotal"],
                     "loggedNetPercent": m["loggedNetPercentOfPredicted"], "note": m.get("note")})
    spans = [run_span(out_dir, r["name"]) for r in rows]
    group = list(range(len(rows)))                      # union-find over runs that share a starting point
    def root(i):
        while group[i] != i:
            i = group[i]
        return i
    for i in range(len(rows)):
        for j in range(i):
            if same_start(spans[i], spans[j]):
                group[root(i)] = root(j)
    best = {}
    for i, r in enumerate(rows):
        g = root(i)
        if g not in best or r["arrivals"] > best[g]["arrivals"]:
            best[g] = r
    for i, r in enumerate(rows):
        r["start"] = best[root(i)]["name"]
        r["primary"] = "yes" if best[root(i)] is r else ""
    with open(os.path.join(out_dir, "index.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)


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
    if os.path.isdir(a.out):
        write_index(os.path.normpath(a.out))


if __name__ == "__main__":
    main()
