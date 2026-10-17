#!/usr/bin/env python3
"""Replay logged cargo arrivals through a freshness pay curve and print what it would add or take away.

Usage: tools/replay_curve.py [options] local/logs/stdout-....txt | local/runs/<name>.arrivals.csv [more files]

Reads the `BEST_BEFORE arrival` lines after the last load in each log (the same slice tools/verify_run.py reads), or the
`.arrivals.csv` that tools/extract_run.py cut from one (the same rows, far smaller and faster to read), and
applies the five-setting curve to every unit, so the defaults can be tuned without the game:

  bonus-percent            pay bonus at 100% freshness, as a fraction of the unit's pay (0.5 = +50%)
  bonus-down-to-freshness  freshness where the bonus starts to fall; the bonus is level above it
  breakeven-freshness      freshness with exactly full pay
  penalty-below-freshness  freshness where the penalty reaches its maximum
  penalty-percent          maximum penalty, negative (-0.95 = -95%), also used for spoiled units

The flags are the settings.tl names in kebab case (bonusPercent -> --bonus-percent).

The defaults are the numbers in best_before_1/content/settings.tl (the mod's own settings file), so a run is replayed
with what the game used unless a flag overrides it. The log also records them: look for `BEST_BEFORE settings`.

Straight lines between the points, order 1 >= bonus-down-to-freshness >= breakeven-freshness >= penalty-below-freshness >= 0. A deduction is clamped to
99% of the unit's predicted pay. The net is the sum of all adjustments as a share of the predicted pay of all arrivals.

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
"""
import argparse
import csv
import os
import re
import sys
from collections import defaultdict

MAX_DEDUCTION = 0.99                                    # of the unit's predicted pay
SETTINGS = ("bonus-percent", "bonus-down-to-freshness", "breakeven-freshness", "penalty-below-freshness", "penalty-percent")
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "best_before_1", "content", "settings.tl")


def camel(name):
    """bonus-down-to-freshness -> bonusDownToFreshness"""
    first, *rest = name.split("-")
    return first + "".join(w.capitalize() for w in rest)


def file_defaults():
    """The numbers in the mod's settings.tl (one `name = value,` per line), so the replay starts from the mod's own."""
    found = dict(re.findall(r'^\s*(\w+)\s*=\s*("?[-\w.]+"?),', open(SETTINGS_FILE).read(), re.M))
    numbers = {name: float(found[camel(name)]) for name in SETTINGS}
    return numbers, found.get("stored", '"formula"').strip('"')


DEFAULTS, DEFAULT_STORED = file_defaults()


def kv(text):
    return dict(re.findall(r'(\w+)=("[^"]*"|\S+)', text))


def arrival_fields(path):
    """The key=value fields of every arrival: from an extracted `.arrivals.csv` (tools/extract_run.py) or from a raw log."""
    if path.endswith(".csv"):
        for row in csv.DictReader(open(path, newline="")):
            yield {k: v for k, v in row.items() if v != ""}
        return
    lines = open(path, errors="replace").read().splitlines()
    start = max((i for i, ln in enumerate(lines) if "BEST_BEFORE preRunFn" in ln), default=0)
    for ln in lines[start:]:
        if "BEST_BEFORE arrival " in ln:
            yield kv(ln.split("BEST_BEFORE arrival ", 1)[1])


def read_arrivals(path):
    out = []
    for d in arrival_fields(path):
        pred = d.get("predictedIncome", "n/a")
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
        out.append({"pred": float(pred), "fresh": fresh, "corrected": corrected, "good": d.get("good") == "true",
                    "cargo": d.get("cargoType", "?"), "carrier": d.get("carrier", "?"),
                    "logged": int(d.get("deduction", 0))})
    return out


def check_order(s):
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


def replay(units, s, stored):
    """Returns (bonus total, deduction total) in pay units; a deduction is negative."""
    gain = loss = 0.0
    for u in units:
        a = adjustment(u, s, stored) * u["pred"]
        if a > 0:
            gain += a
        else:
            loss += max(a, -MAX_DEDUCTION * u["pred"])
    return gain, loss


def pct(x, base):
    return f"{100 * x / base:+.1f}%" if base else "n/a"


def table(units, s, stored, key, title):
    groups = defaultdict(list)
    for u in units:
        groups[u[key]].append(u)
    print(f"  by {title}:")
    print(f"    {title:<8} {'units':>6} {'base pay':>12} {'bonus':>11} {'deduction':>12} {'net':>8}")
    for k in sorted(groups, key=lambda x: (len(x), x)):
        g = groups[k]
        base = sum(u["pred"] for u in g)
        gain, loss = replay(g, s, stored)
        print(f"    {k:<8} {len(g):>6} {base:>12,.0f} {gain:>+11,.0f} {loss:>+12,.0f} {pct(gain + loss, base):>8}")


def report(name, units, s, stored, tables):
    base = sum(u["pred"] for u in units)
    gain, loss = replay(units, s, stored)
    logged = sum(u["logged"] for u in units)
    stored_units = sum(1 for u in units if u["good"] and u["fresh"] < 0)
    spoiled = sum(1 for u in units if not u["good"])
    print(f"{name}: {len(units)} units, base pay {base:,.0f}, {spoiled} flagged spoiled, "
          f"{stored_units} flagged good at negative freshness")
    print(f"  curve: bonus {gain:+,.0f}, deduction {loss:+,.0f}, net {gain + loss:+,.0f} = {pct(gain + loss, base)} of base pay")
    print(f"  (as logged by the probe that ran: deduction {-logged:+,.0f} = {pct(-logged, base)})")
    if tables:
        table(units, s, stored, "carrier", "carrier")
        table(units, s, stored, "cargo", "cargo")


def solve_bonus(units, s, stored):
    """The net is linear in the bonus setting, so the bonus giving a net of zero follows from two replays."""
    gain0, loss0 = replay(units, dict(s, **{"bonus-percent": 0.0}), stored)
    gain1, _ = replay(units, dict(s, **{"bonus-percent": 1.0}), stored)
    return -loss0 / gain1 if gain1 > 0 else None


def main():
    ap = argparse.ArgumentParser(description="Replay logged arrivals through the five-setting freshness curve.")
    ap.add_argument("logs", nargs="+")
    for name in SETTINGS:
        ap.add_argument("--" + name, type=float, default=DEFAULTS[name])
    ap.add_argument("--stored", choices=("corrected", "formula", "zero", "neutral"), default=DEFAULT_STORED)
    ap.add_argument("--sweep", help="one setting and its values, e.g. breakeven-freshness=0.2,0.3,0.4")
    ap.add_argument("--solve-bonus", action="store_true", help="also print the bonus that nets to zero")
    ap.add_argument("--tables", action="store_true", help="also print the net per carrier and per cargo type")
    args = ap.parse_args()
    s = {name: getattr(args, name.replace("-", "_")) for name in SETTINGS}
    check_order(s)

    data = [(p, read_arrivals(p)) for p in args.logs]
    data = [(p, u) for p, u in data if u]
    for p, _ in data:
        marker = ",ext," if p.endswith(".csv") else "ext="           # a csv names its columns in the header line
        if marker not in open(p, errors="replace").read(2_000_000) and args.stored == "corrected":
            print(f"note: {p} has no `ext` field (older probe), so `corrected` equals the plain age there", file=sys.stderr)
    if not data:
        sys.exit("no arrivals with a predicted income found")
    if len(data) > 1:
        data.append(("pooled", [u for _, units in data for u in units]))

    if args.sweep:
        name, values = args.sweep.split("=")
        if name not in SETTINGS:
            sys.exit(f"--sweep needs one of {', '.join(SETTINGS)}")
        values = [float(v) for v in values.split(",")]
        print(f"net as a share of base pay, {name} varied, other settings {({k: v for k, v in s.items() if k != name})}, "
              f"stored={args.stored}")
        print(f"{'log':<34}" + "".join(f"{v:>9g}" for v in values))
        for p, units in data:
            row = []
            for v in values:
                t = dict(s, **{name: v})
                check_order(t)
                gain, loss = replay(units, t, args.stored)
                row.append(pct(gain + loss, sum(u["pred"] for u in units)))
            print(f"{p[-32:]:<34}" + "".join(f"{r:>9}" for r in row))
        return

    for p, units in data:
        report(p, units, s, args.stored, args.tables)
        if args.solve_bonus:
            b = solve_bonus(units, s, args.stored)
            print("  bonus for a net of zero: " + (f"{b:.3f} ({100 * b:.0f}%)" if b is not None else "none (no unit earns a bonus)"))
        print()


if __name__ == "__main__":
    main()
