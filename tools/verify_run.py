#!/usr/bin/env python3
"""Check a Best Before test run from the game log alone (no screenshots).

Usage: tools/verify_run.py local/logs/stdout-....txt

For every vehicle and line the probe logged ("BEST_BEFORE journal" lines carry each tracked ledger's balance), the
ledger's balance change over the run must equal
    pay + deductions - running costs
where the pay is what the arrivals predicted, the deductions are the "sending deduction" lines, and the running
costs are the negative steps at multiples of 60,000 clock units. If the deductions had not landed, the derived pay
would be too high by the deductions' share, so the check tells landed from not landed.
"""
import re
import sys
from collections import defaultdict

MARGIN = 30000          # clock units: pay of units that arrived this close to the end may not have landed yet
BATCH = 60000           # running costs are booked every 60,000 clock units
TOLERANCE = 0.03        # the prediction matches real pay within about 1%


def kv(text):
    return dict(re.findall(r'(\w+)=("[^"]*"|\S+)', text))


def main(path):
    lines = open(path, errors="replace").read().splitlines()
    start = max((i for i, ln in enumerate(lines) if "BEST_BEFORE preRunFn" in ln), default=0)
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
                                 "pred": float(d["predictedIncome"]), "ded": int(d.get("deduction", 0)),
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
          f"{len(sends)} deduction entries sent, {len(snaps)} journal snapshots")
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
        print("FAIL  too little data (no snapshots or no deductions sent)")
        return 1

    units = sum(a["ded"] > 0 for a in arrivals)
    print(f"      {units} units deducted, {sum(a['ded'] for a in arrivals):,} in total; "
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
        bad = [r for r in rows if abs(r["ratio"] - 1) > TOLERANCE and r["sent"] != 0]
        print(("PASS" if not bad else "FAIL") + f"  {label}: {len(rows)} ledgers checked, {len(bad)} outside "
              f"{TOLERANCE:.0%} (derived pay / predicted pay)")
        ok = ok and not bad
        for r in (bad or rows)[:6]:
            print(f"        {r['key']}: delta {r['delta']:>10,} costs {r['costs']:>7,} deductions {r['sent']:>9,} "
                  f"predicted pay {r['expected']:>10,.0f}  ratio {r['ratio']:.3f} (without deductions {r['ratio_without']:.3f})")

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
    print(f"INFO  player: delta {delta:,}, running costs {costs:,}, deductions {sent:,}, predicted pay of all arrivals "
          f"{expected:,.0f}; derived pay / predicted {pay / expected:.3f} (without deductions "
          f"{(delta + costs) / expected:.3f}). Income the arrivals do not predict makes this above 1 "
          f"(1.145 in the 05:00 control run with no player deductions).")

    # Did each entry land exactly, at once? (it can share a step with pay, so this is only a rate)
    exact = 0
    for s in sends:
        key = s["entity"]
        later = [x for x in snaps if x["i"] > s["i"] and key in x["bal"]][:4]
        prevs = [x for x in snaps if x["i"] < s["i"] and key in x["bal"]]
        if not later or not prevs:
            continue
        before = prevs[-1]["bal"][key]
        for x in later:
            if x["bal"][key] - before == s["amount"] or x["bal"].get("playerBalance") is None:
                exact += 1
                break
            before = x["bal"][key]
    print(f"INFO  {exact} of {len(sends)} entries showed up as an exact step in one of the next four snapshots")
    print("RESULT " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
