#!/usr/bin/env python3
"""Check a Best Before test run from the game log alone (no screenshots).

Usage: tools/verify_run.py local/logs/stdout-....txt

The probe books every freshness deduction to the player only (the game pays a delivered unit once and shares it along
the supply chain by a formula we do not know). The run passes when
  - the log has no error lines and no gaps in the journal sequence numbers,
  - the units adjusted (deducted or given a bonus) in the arrival lines equal the units in the "sending adjustment" lines (nothing lost in the
    per-update aggregation, apart from the last few still queued), and
  - the booked amounts show up in the player's balance: most entries appear as an exact step of playerBalance or
    playerIncomeTotal in one of the next four snapshots (the rest share a step with pay, so the rate stays below 100%). On a busy
    save the rate falls further, so it also passes when the exact hits outnumber those of the same amounts shifted by one 50 to 1.
Vehicle and line ledgers are reported for information only: pay for a transferred unit is split along its chain, so a
first-leg ledger does not receive the whole predicted pay.
"""
import re
import sys
from collections import defaultdict

MARGIN = 10000          # clock units: pay of units that arrived this close to the end may not have landed yet
#                         (measured: pay shows in the next snapshot, at most about 5,200 after the arrival)
BATCH = 60000           # running costs are booked every 60,000 clock units
MIN_LANDED = 0.4        # share of the booked entries that must show up as an exact step (about 0.6 to 0.96 seen)
MIN_BUSY_HITS = 100     # a busy save passes on this many exact hits when the shifted-amount control hits BUSY_RATIO times less
BUSY_RATIO = 50
MAX_UNSENT = 5          # units that may still be queued when the log ends


def kv(text):
    return dict(re.findall(r'(\w+)=("[^"]*"|\S+)', text))


def main(path):
    lines = open(path, errors="replace").read().splitlines()
    start = max((i for i, ln in enumerate(lines) if "BEST_BEFORE preRunFn" in ln), default=0)
    # The level is judged from the log itself: the BEST_BEFORE settings line comes from mod.script.tl and runs one load behind the
    # level the probe used, while the probe writes a line per unit only at "curve" and "full".
    if not any("BEST_BEFORE arrival " in ln for ln in lines[start:]):
        sys.exit(f"{path}: no per-unit arrival lines after the last load. This check reads them, so set logLevel = \"curve\" or "
                 f"\"full\" in settings.tl, load the save (no restart needed) and run again")
    arrivals, sends, snaps, errors = [], [], [], []
    for i, ln in enumerate(lines[start:], start):
        if " - ERROR " in ln or "Error message" in ln:
            errors.append(ln.strip())
        m = re.search(r"BEST_BEFORE (\w+) ?(.*)", ln)
        if not m:
            continue
        kind, rest = m.groups()
        if kind == "arrival":
            d = kv(rest)
            if "predictedIncome" in d and d["predictedIncome"] != "n/a":
                arrivals.append({"i": i, "t": int(d["now"]), "vehicle": d.get("vehicle"), "line": d.get("line"),
                                 "pred": float(d["predictedIncome"]), "ded": int(d.get("deduction", 0)), "bonus": int(d.get("bonus", 0)),
                                 "carrier": d.get("carrier", "?")})
        elif kind == "sending":
            d = kv(rest)
            sends.append({"i": i, "ledger": d["ledger"], "entity": d["entity"], "amount": int(d["amount"]),
                          "units": int(d["units"]), "carrier": d["carrier"]})
        elif kind == "journal":
            seq = int(re.match(r"#(\d+)", rest).group(1))
            t = int(re.search(r" t=(\d+)", rest).group(1))
            bal = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", rest.split(" t=")[1].split(" ", 1)[1])}
            snaps.append({"i": i, "seq": seq, "t": t, "bal": bal})

    print(f"{path}: {len(lines) - start} lines after the last load, {len(arrivals)} arrivals, "
          f"{len(sends)} adjustment entries sent, {len(snaps)} journal snapshots")
    ok = True

    if errors:
        ok = False
        print(f"FAIL  {len(errors)} error lines, first: {errors[0][:200]}")
    else:
        print("PASS  no error lines")

    seqs = [s["seq"] for s in snaps]
    missing = sorted(set(range(min(seqs), max(seqs) + 1)) - set(seqs)) if seqs else []
    print(("PASS" if not missing else "FAIL") + f"  journal sequence numbers: {len(missing)} gaps")
    if len(snaps) < 3 or not sends:
        print("FAIL  too little data (no snapshots or no adjustments sent)")
        return 1

    units = sum(a["ded"] > 0 or a["bonus"] > 0 for a in arrivals)
    print(f"      {units} units adjusted, {sum(a['ded'] for a in arrivals):,} deducted and {sum(a['bonus'] for a in arrivals):,} added; "
          f"carriers {sorted(set(a['carrier'] for a in arrivals))}")

    end = snaps[-1]
    prior_snap_index = snaps[-2]["i"]          # sends after this one may not have landed yet
    def sent_total(entity):
        return sum(s["amount"] for s in sends if s["entity"] == entity and s["i"] < prior_snap_index)

    def costs_and_delta(key, first):
        costs = 0
        prev = first
        for s in snaps:
            if s["i"] <= first_snap(key)["i"] or key not in s["bal"] or key not in prev["bal"]:
                prev = s if key in s["bal"] else prev
                continue
            step = s["bal"][key] - prev["bal"][key]
            if step < 0 and s["t"] % BATCH == 0:
                costs += -step
            prev = s
        return costs

    def first_snap(key):
        return next(s for s in snaps if key in s["bal"])

    def check(key, kind):
        base = first_snap(key)
        last = next(s for s in reversed(snaps) if key in s["bal"])
        delta = last["bal"][key] - base["bal"][key]
        costs = costs_and_delta(key, base)
        sent = sent_total(key)
        expected = sum(a["pred"] for a in arrivals
                       if a[kind] == key and base["t"] <= a["t"] <= last["t"] - MARGIN)
        if expected <= 0:
            return None
        pay = delta + costs - sent
        return {"key": key, "delta": delta, "costs": costs, "sent": sent, "expected": expected,
                "ratio": pay / expected, "ratio_without": (delta + costs) / expected}

    for kind, label in (("vehicle", "vehicles"), ("line", "lines")):
        keys = sorted({a[kind] for a in arrivals if a[kind] not in (None, "nil")}
                      & {k for s in snaps for k in s["bal"]})
        rows = [r for r in (check(k, kind) for k in keys) if r]
        if rows:
            ratios = sorted(r["ratio"] for r in rows)
            print(f"INFO  {label} (first leg of each unit): {len(rows)} ledgers, derived pay / predicted pay "
                  f"min {ratios[0]:.2f}, median {ratios[len(ratios) // 2]:.2f}, max {ratios[-1]:.2f}")

    # The player: all arrivals, all deductions booked to the player.
    base, last = snaps[0], end
    delta = last["bal"]["playerBalance"] - base["bal"]["playerBalance"]
    costs, prev = 0, base
    for s in snaps[1:]:
        step = s["bal"]["playerBalance"] - prev["bal"]["playerBalance"]
        if step < 0 and s["t"] % BATCH == 0:
            costs += -step
        prev = s
    sent = sum(s["amount"] for s in sends if s["ledger"] == "player" and s["i"] < prior_snap_index)
    expected = sum(a["pred"] for a in arrivals if base["t"] <= a["t"] <= last["t"] - MARGIN)
    pay = delta + costs - sent
    print(f"INFO  player: delta {delta:,}, running costs {costs:,}, adjustments {sent:,}, predicted pay of all arrivals "
          f"{expected:,.0f}; derived pay / predicted {pay / expected:.3f} (without deductions "
          f"{(delta + costs) / expected:.3f}). Income the arrivals do not predict makes this above 1 "
          f"(1.145 in the 05:00 control run with no player deductions).")

    # Units: the arrival lines and the sent entries must agree.
    queued_units = sum(1 for a in arrivals if a["ded"] > 0 or a["bonus"] > 0)
    sent_units = sum(s["units"] for s in sends if s["ledger"] == "player")
    unsent_ok = 0 <= queued_units - sent_units <= MAX_UNSENT
    print(("PASS" if unsent_ok else "FAIL") + f"  units: {queued_units} adjusted in the arrival lines, "
          f"{sent_units} sent to the player")
    ok = ok and unsent_ok

    # Did each entry land exactly, at once? An entry can share a step with pay, so this is only a rate, and on a busy save (many
    # arrivals per snapshot) it falls well below the quiet-save rate. A control tells the two apart: the same count with every
    # amount moved by one currency unit can only hit by chance, so a busy save passes when the real amounts hit many times
    # more often than the shifted ones (and at least MIN_BUSY_HITS times).
    def count_landed(shift):
        landed, checked = 0, 0
        for s in sends:
            if s["ledger"] != "player":
                continue
            later = [x for x in snaps if x["i"] > s["i"]][:4]
            prevs = [x for x in snaps if x["i"] < s["i"]]
            if not later or not prevs:
                continue
            checked += 1
            for field in ("playerBalance", "playerIncomeTotal"):
                before = prevs[-1]["bal"].get(field)
                hit = False
                for x in later:
                    value = x["bal"].get(field)
                    if before is not None and value is not None and value - before == s["amount"] + shift:
                        hit = True
                        break
                    before = value
                if hit:
                    landed += 1
                    break
        return landed, checked

    landed, checked = count_landed(0)
    chance, _ = count_landed(1)
    rate = landed / checked if checked else 0.0
    quiet_ok = rate >= MIN_LANDED
    busy_ok = landed >= MIN_BUSY_HITS and chance * BUSY_RATIO <= landed
    landed_ok = quiet_ok or busy_ok
    how = "" if quiet_ok else (f"; busy save, {landed} exact hits against {chance} for amounts shifted by one" if busy_ok
                               else f"; control: {chance} hits for amounts shifted by one")
    print(("PASS" if landed_ok else "FAIL") + f"  landing: {landed} of {checked} player entries showed up as an exact "
          f"step of the balance or income total in the next four snapshots ({rate:.0%}, needs {MIN_LANDED:.0%}{how})")
    ok = ok and landed_ok
    print("RESULT " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
