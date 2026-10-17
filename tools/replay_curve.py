#!/usr/bin/env python3
"""Replay logged cargo arrivals through a freshness pay curve and print what it would add or take away.

Usage: tools/replay_curve.py [options] local/logs/stdout-....txt | local/runs/<name>.arrivals.csv [more files]

Reads the `BEST_BEFORE arrival` lines after the last load in each log (the same slice tools/verify_run.py reads), or the
`.arrivals.csv` that tools/extract_run.py cut from one (the same rows, far smaller and faster to read, and with the pay
prediction corrected to the save's Cargo Income setting and earned rank: prefer these), and
applies the five-setting curve to every unit, so the defaults can be tuned without the game:

  bonus-percent            pay bonus at 100% freshness, as a fraction of the unit's pay (0.5 = +50%)
  bonus-down-to-freshness  freshness where the bonus starts to fall; the bonus is level above it
  breakeven-freshness      freshness with exactly full pay
  penalty-below-freshness  freshness where the penalty reaches its maximum
  penalty-percent          maximum penalty, negative (-0.95 = -95%), also used for spoiled units

The flags are the settings.tl names in kebab case (bonusPercent -> --bonus-percent).

Each run is replayed on the curve it was played on, unless a flag overrides a setting. That curve is read from the log's
`BEST_BEFORE loadParams` line (the in-game settings the load started with, as list positions; the last one after the
last load), or for an extracted run from the `curve` in its `.json`. A log that has no such line (made before the line
existed) falls back to its last `curveSettings` line, and then to the numbers in best_before_1/content/settings.tl.

Straight lines between the points, order 1 >= bonus-down-to-freshness >= breakeven-freshness >= penalty-below-freshness >= 0. A deduction is clamped to
100% of the unit's predicted pay. The net is the sum of all adjustments as a share of the predicted pay of all arrivals.

Stored cargo: a specialized warehouse pauses a unit's spoil timer, so the plain age overstates how old it is. `--stored`
picks the freshness used: `corrected` takes the paused time (`ext`) off the age; `formula` uses the plain age; `zero`
and `neutral` use the plain age but, for a unit the game flags good although its plain age is past the limit, clamp it
to 0% or give it no adjustment. Units the game flags as spoiled always get the full penalty.

Logs of the same save overlap (each load replays the same deliveries), so pass logs of different saves together, or
read the per-log lines rather than the pooled one. Do not use a log from a run with a changed cargo limit (the ship
test). Examples:

  tools/replay_curve.py local/logs/stdout-20261016-0651.txt
  tools/replay_curve.py --stored neutral --breakeven-freshness 0.4 --solve-bonus local/logs/stdout-20261016-0651.txt
  tools/replay_curve.py --sweep breakeven-freshness=0.2,0.3,0.4,0.5 local/logs/stdout-20261016-0651.txt
  tools/replay_curve.py --use-defaults --sweep breakeven-freshness=0.2,0.3 local/runs/*.arrivals.csv   # the settings.tl curve, whatever the runs were played on
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict

MAX_DEDUCTION = 1.0                                   # of the unit's predicted pay
SETTINGS = ("bonus-percent", "bonus-down-to-freshness", "breakeven-freshness", "penalty-below-freshness", "penalty-percent")
PARAM_KEYS = {"bonus-percent": "freshPay", "bonus-down-to-freshness": "bonusDownTo", "breakeven-freshness": "breakeven",
              "penalty-below-freshness": "penaltyBelow", "penalty-percent": "spoiledPay"}      # the loadParams names
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "best_before_1", "content", "settings.tl")


def camel(name):
    """bonus-down-to-freshness -> bonusDownToFreshness"""
    first, *rest = name.split("-")
    return first + "".join(w.capitalize() for w in rest)


def file_defaults():
    """The numbers in the mod's settings.tl (one `name = value,` per line), so the replay starts from the mod's own."""
    found = dict(re.findall(r'^\s*(\w+)\s*=\s*("?[-\w.]+"?),', open(SETTINGS_FILE).read(), re.M))
    numbers = {name: float(found[camel(name)]) for name in SETTINGS}
    return numbers, "corrected"   # the mod judges stored cargo as corrected; --stored tries the other modes


DEFAULTS, DEFAULT_STORED = file_defaults()


def kv(text):
    return dict(re.findall(r'(\w+)=("[^"]*"|\S+)', text))


def clamp(value, low, high):
    return max(low, min(high, value))


def normalize(s):
    """The curve as the mod uses it (probe.script.tl normalizeCurve): the freshness points lowered into order, the pay settings clamped."""
    down = clamp(s["bonus-down-to-freshness"], 0.0, 1.0)
    even = clamp(s["breakeven-freshness"], 0.0, down)
    return {"bonus-percent": clamp(s["bonus-percent"], 0.0, 2.0), "bonus-down-to-freshness": down, "breakeven-freshness": even,
            "penalty-below-freshness": clamp(s["penalty-below-freshness"], 0.0, even), "penalty-percent": clamp(s["penalty-percent"], -1.0, 0.0)}


def params_curve(positions):
    """The curve for the in-game settings' list positions (`loadParams`): a position is a 5% step, position 1 is 0% (100% for the
    bonus); the spoiled pay is a share of pay, so the penalty is that minus 1."""
    share = lambda position: round(float(position) - 1) * 5 / 100
    s = {name: share(positions[key]) for name, key in PARAM_KEYS.items()}
    s["penalty-percent"] -= 1.0
    return normalize(s)


def curve_from_lines(lines):
    """(curve, source) of a log slice: the last `loadParams` line, else the last `curveSettings` line, else (None, None)."""
    params = notes = None
    for ln in lines:
        if "BEST_BEFORE loadParams " in ln:
            params = kv(ln.split("BEST_BEFORE loadParams ", 1)[1])
        elif "BEST_BEFORE curveSettings " in ln:
            notes = kv(ln.split("BEST_BEFORE curveSettings ", 1)[1])
    if params and all(key in params for key in PARAM_KEYS.values()):
        return params_curve(params), "loadParams"
    if notes and all(camel(name) in notes for name in SETTINGS):
        return {name: float(notes[camel(name)]) for name in SETTINGS}, "curveSettings"
    return None, None


def run_curve(path, lines=None):
    """(curve, source) a run was played on: from the raw log's slice, or the `curve` in an extracted run's .json."""
    if path.endswith(".csv"):
        meta_path = re.sub(r"\.arrivals\.csv$", ".json", path)
        if os.path.exists(meta_path):
            meta = json.load(open(meta_path))
            if meta.get("curve"):
                return meta["curve"], "extracted json"
            noted, _ = curve_from_lines(f"BEST_BEFORE curveSettings {n}" for n in meta.get("curveSettings") or [])   # extracted before `curve` existed
            if noted:
                return noted, "extracted json curveSettings"
        return None, None
    return curve_from_lines(lines)


def arrival_fields(path, lines=None):
    """The key=value fields of every arrival: from an extracted `.arrivals.csv` (tools/extract_run.py) or from a raw log's slice."""
    if path.endswith(".csv"):
        for row in csv.DictReader(open(path, newline="")):
            yield {k: v for k, v in row.items() if v != ""}
        return
    for ln in lines:
        if "BEST_BEFORE arrival " in ln:
            yield kv(ln.split("BEST_BEFORE arrival ", 1)[1])


def read_arrivals(path):
    """(units, curve source); every unit carries `s`, the curve its run was played on."""
    lines = None
    if not path.endswith(".csv"):
        lines = open(path, errors="replace").read().splitlines()
        start = max((i for i, ln in enumerate(lines) if "BEST_BEFORE preRunFn" in ln), default=0)
        lines = lines[start:]
    curve, source = run_curve(path, lines)
    if curve is None:
        curve, source = dict(DEFAULTS), "settings.tl"
    out = []
    for d in arrival_fields(path, lines):
        # an extracted csv carries `predictedCorrected`, the pay prediction at the right scale (difficulty x rank multiplier);
        # a raw log has only `predictedIncome`, which the probes before commit c976cfd computed with a fixed 0.96426
        pred = d.get("predictedCorrected") or d.get("predictedIncome", "n/a")
        if pred == "n/a" or "freshness" not in d:
            continue
        fresh = float(d["freshness"])
        # logged `corrected` (newer probe) or worked out from the age minus the pause (`ext`), plain age if neither
        if "corrected" in d:
            corrected = float(d["corrected"])
        elif "ext" in d and "ageMs" in d and float(d.get("limitMs", 0)) > 0:
            corrected = 1.0 - (float(d["ageMs"]) - float(d["ext"])) / float(d["limitMs"])
        else:
            corrected = fresh
        out.append({"s": curve, "pred": float(pred), "fresh": fresh, "corrected": corrected, "good": d.get("good") == "true",
                    "cargo": d.get("cargoType", "?"), "carrier": d.get("carrier", "?"),
                    "logged": int(d.get("deduction", 0)),
                    "pred_logged": float(d.get("predictedIncome", pred))})
    return out, source


def check_order(s):
    if not 0.0 <= s["bonus-percent"] <= 2.0 or not -1.0 <= s["penalty-percent"] <= 0.0:
        sys.exit("settings must satisfy 0 <= bonus-percent <= 2 and -1 <= penalty-percent <= 0 (the mod clamps to those)")
    order = [1.0, s["bonus-down-to-freshness"], s["breakeven-freshness"], s["penalty-below-freshness"], 0.0]
    if any(a < b for a, b in zip(order, order[1:])):
        sys.exit("settings must satisfy 1 >= bonus-down-to-freshness >= breakeven-freshness >= penalty-below-freshness >= 0")
    if s["bonus-percent"] < 0 or not -1 <= s["penalty-percent"] <= 0:
        sys.exit("bonus-percent must be >= 0 and penalty-percent between -1 and 0")


def adjustment(u, s, stored):
    """Fraction of the unit's pay added (positive) or taken away (negative)."""
    fresh, good = (u["corrected"] if stored == "corrected" else u["fresh"]), u["good"]
    if not good:
        return s["penalty-percent"]
    if fresh < 0:                                       # flagged good by the game although the formula says past due
        if stored == "neutral":
            return 0.0
        if stored == "zero":
            fresh = 0.0
    if fresh >= s["bonus-down-to-freshness"]:
        return s["bonus-percent"]
    if fresh >= s["breakeven-freshness"]:
        return s["bonus-percent"] * (fresh - s["breakeven-freshness"]) / (s["bonus-down-to-freshness"] - s["breakeven-freshness"])
    if fresh >= s["penalty-below-freshness"]:
        return s["penalty-percent"] * (s["breakeven-freshness"] - fresh) / (s["breakeven-freshness"] - s["penalty-below-freshness"])
    return s["penalty-percent"]


def replay(units, overrides, stored):
    """Returns (bonus total, deduction total) in pay units; a deduction is negative. Each unit is judged on the curve its run
    was played on, with the settings in `overrides` (flags) replacing that curve's."""
    gain = loss = 0.0
    for u in units:
        a = adjustment(u, {**u["s"], **overrides}, stored) * u["pred"]
        if a > 0:
            gain += a
        else:
            loss += max(a, -MAX_DEDUCTION * u["pred"])
    return gain, loss


def pct(x, base):
    return f"{100 * x / base:+.1f}%" if base else "n/a"


def table(units, overrides, stored, key, title):
    groups = defaultdict(list)
    for u in units:
        groups[u[key]].append(u)
    print(f"  by {title}:")
    print(f"    {title:<8} {'units':>6} {'base pay':>12} {'bonus':>11} {'deduction':>12} {'net':>8}")
    for k in sorted(groups, key=lambda x: (len(x), x)):
        g = groups[k]
        base = sum(u["pred"] for u in g)
        gain, loss = replay(g, overrides, stored)
        print(f"    {k:<8} {len(g):>6} {base:>12,.0f} {gain:>+11,.0f} {loss:>+12,.0f} {pct(gain + loss, base):>8}")


def describe_curve(units, overrides):
    """One line naming the curve(s) the units were replayed on."""
    curves = {tuple(sorted({**u["s"], **overrides}.items())) for u in units}
    if len(curves) > 1:
        return f"{len(curves)} different curves (one per run)"
    return " ".join(f"{name}={value:g}" for name, value in next(iter(curves)))


def report(name, units, overrides, stored, tables, source):
    base = sum(u["pred"] for u in units)
    gain, loss = replay(units, overrides, stored)
    logged = sum(u["logged"] for u in units)
    stored_units = sum(1 for u in units if u["good"] and u["fresh"] < 0)
    spoiled = sum(1 for u in units if not u["good"])
    print(f"{name}: {len(units)} units, base pay {base:,.0f}, {spoiled} flagged spoiled, "
          f"{stored_units} flagged good at negative freshness")
    print(f"  curve ({source}{', with flags' if overrides else ''}): {describe_curve(units, overrides)}")
    print(f"  result: bonus {gain:+,.0f}, deduction {loss:+,.0f}, net {gain + loss:+,.0f} = {pct(gain + loss, base)} of base pay")
    print(f"  (as logged by the probe that ran: deduction {-logged:+,.0f} = {pct(-logged, sum(u['pred_logged'] for u in units))}"
          f" of the pay it predicted)")
    if tables:
        table(units, overrides, stored, "carrier", "carrier")
        table(units, overrides, stored, "cargo", "cargo")


def solve_bonus(units, overrides, stored):
    """The net is linear in the bonus setting, so the bonus giving a net of zero follows from two replays."""
    gain0, loss0 = replay(units, dict(overrides, **{"bonus-percent": 0.0}), stored)
    gain1, _ = replay(units, dict(overrides, **{"bonus-percent": 1.0}), stored)
    return -loss0 / gain1 if gain1 > 0 else None


def main():
    ap = argparse.ArgumentParser(description="Replay logged arrivals through the five-setting freshness curve.")
    ap.add_argument("logs", nargs="+")
    for name in SETTINGS:
        ap.add_argument("--" + name, type=float, default=None, help="replace this setting of each run's own curve")
    ap.add_argument("--use-defaults", action="store_true",
                    help="start from the settings.tl numbers instead of each run's own curve (to tune the defaults over runs played on other curves)")
    ap.add_argument("--stored", choices=("corrected", "formula", "zero", "neutral"), default=DEFAULT_STORED)
    ap.add_argument("--sweep", help="one setting and its values, e.g. breakeven-freshness=0.2,0.3,0.4")
    ap.add_argument("--solve-bonus", action="store_true", help="also print the bonus that nets to zero")
    ap.add_argument("--tables", action="store_true", help="also print the net per carrier and per cargo type")
    args = ap.parse_args()
    overrides = {name: getattr(args, name.replace("-", "_")) for name in SETTINGS if getattr(args, name.replace("-", "_")) is not None}

    data = []
    for p in args.logs:
        units, source = read_arrivals(p)
        if units:
            if args.use_defaults:
                units = [dict(u, s=dict(DEFAULTS)) for u in units]
                source = "settings.tl"
            data.append((p, units, source))
    for _, units, _ in data:
        for curve in {tuple(sorted(u["s"].items())) for u in units}:
            check_order({**dict(curve), **overrides})
    for p, _, _ in data:
        marker = ",ext," if p.endswith(".csv") else "ext="           # a csv names its columns in the header line
        if marker not in open(p, errors="replace").read(2_000_000) and args.stored == "corrected":
            print(f"note: {p} has no `ext` field (older probe), so `corrected` equals the plain age there", file=sys.stderr)
    if not data:
        sys.exit("no arrivals with a predicted income found")
    if len(data) > 1:
        data.append(("pooled", [u for _, units, _ in data for u in units], "per run"))

    if args.sweep:
        name, values = args.sweep.split("=")
        if name not in SETTINGS:
            sys.exit(f"--sweep needs one of {', '.join(SETTINGS)}")
        values = [float(v) for v in values.split(",")]
        others = {k: v for k, v in overrides.items() if k != name}
        print(f"net as a share of base pay, {name} varied, the other settings from {'settings.tl' if args.use_defaults else 'each run'}"
              f"{f' except {others}' if others else ''}, stored={args.stored}")
        print(f"{'log':<34}" + "".join(f"{v:>9g}" for v in values))
        for p, units, _ in data:
            row = []
            for v in values:
                t = dict(overrides, **{name: v})
                for curve in {tuple(sorted(u["s"].items())) for u in units}:
                    check_order({**dict(curve), **t})
                gain, loss = replay(units, t, args.stored)
                row.append(pct(gain + loss, sum(u["pred"] for u in units)))
            print(f"{p[-32:]:<34}" + "".join(f"{r:>9}" for r in row))
        return

    for p, units, source in data:
        report(p, units, overrides, args.stored, args.tables, source)
        if args.solve_bonus:
            b = solve_bonus(units, overrides, args.stored)
            print("  bonus for a net of zero: " + (f"{b:.3f} ({100 * b:.0f}%)" if b is not None else "none (no unit earns a bonus)"))
        print()


if __name__ == "__main__":
    main()
