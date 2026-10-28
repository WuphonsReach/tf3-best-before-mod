#!/usr/bin/env python3
"""Check a Best Before test run from the game log alone (no screenshots).

Usage: tools/verify_run.py local/logs/stdout-....txt

The mod answers the game's ticket price event with each unit's pay multiplier. The run passes when
  - the log has no error lines and no gaps in the journal sequence numbers, and
  - every arrival line billed by ticket has the ticket item logged before it, answered with the arrival's rate (1 + the
    curve's adjustment, not below 0).
The player's income against the logged base pay times the answers is reported for information (units near either end of a
run blur it). A run under the test probe (ticketPriceProbe "observe" or "scale") bills nothing by ticket; read it with
tools/ticket_probe.py.
Stale line warnings are checked from the monthly staleRoll and staleLine lines: each line's share is the mean of its buckets,
every warn, clear and hold follows the thresholds, the warned set sent to the notifications matches the lines marked warned,
and where the log holds a line's previous state, its new bucket is rebuilt from the arrival lines counted for it in between.
Each arrival's staleUnit is checked against the rule too (not good, or corrected freshness below the staleBelow the staleRoll lines log).
"""
import re
import sys
from collections import defaultdict


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
    arrivals, snaps, errors = 0, [], []
    ticket_items, ticketed, ticket_events = {}, [], []     # items by unit, (arrival, item) pairs, events
    for i, ln in enumerate(lines[start:], start):
        if " - ERROR " in ln or "Error message" in ln:
            errors.append(ln.strip())
        m = re.search(r"BEST_BEFORE (\w+) ?(.*)", ln)
        if not m:
            continue
        kind, rest = m.groups()
        if kind == "ticketItem":
            d = kv(rest)
            ticket_items[d["unit"]] = d                 # ids are reused: the next arrival of this unit takes it
        elif kind == "ticketPrice" and "items=" in rest:
            ticket_events.append(kv(rest))
        elif kind == "arrival":
            d = kv(rest)
            arrivals += 1
            if d.get("billing") == "ticket":
                ticketed.append((d, ticket_items.pop(d["unit"], None)))
        elif kind == "journal":
            seq = int(re.match(r"#(\d+)", rest).group(1))
            t = int(re.search(r" t=(\d+)", rest).group(1))
            bal = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", rest.split(" t=")[1].split(" ", 1)[1])}
            snaps.append({"i": i, "seq": seq, "t": t, "bal": bal})

    print(f"{path}: {len(lines) - start} lines after the last load, {arrivals} arrivals, {len(ticketed)} billed by ticket, "
          f"{len(snaps)} journal snapshots")
    ok = True

    if errors:
        ok = False
        print(f"FAIL  {len(errors)} error lines, first: {errors[0][:200]}")
    else:
        print("PASS  no error lines")

    seqs = [s["seq"] for s in snaps]
    missing = sorted(set(range(min(seqs), max(seqs) + 1)) - set(seqs)) if seqs else []
    print(("PASS" if not missing else "FAIL") + f"  journal sequence numbers: {len(missing)} gaps")
    ok = ok and not missing
    if not ticketed:
        print("FAIL  no arrival billed by ticket (a test probe run? read it with tools/ticket_probe.py)")
        return 1
    return check_ticket(lines, start, ticketed, ticket_events, snaps, ok)


def check_ticket(lines, start, ticketed, events, snaps, ok):
    """Every ticketed arrival was answered with its rate; the player's income for information."""
    def answer(it):
        """The item's answer as a number, or None when the probe logged none (an error in the answer, or no SimCargo)."""
        try:
            return float(it["multiplier"])
        except (KeyError, ValueError):
            return None

    missing = [a for a, it in ticketed if it is None]
    wrong = [(a, it) for a, it in ticketed if it is not None
             and (answer(it) is None or abs(answer(it) - max(0.0, float(a["rate"]))) > 1e-6)]
    answered_ok = not missing and not wrong
    print(("PASS" if answered_ok else "FAIL") + f"  ticket answers: {len(ticketed) - len(missing) - len(wrong)} of {len(ticketed)} "
          f"arrivals billed by ticket were answered with their rate ({len(missing)} without a ticket item, {len(wrong)} "
          f"answered otherwise)")
    for a, it in wrong[:5]:
        print(f"      unit {a['unit']} at {a['now']}: answered {it['multiplier']}, rate {a['rate']}")
    for a in missing[:5]:
        print(f"      unit {a['unit']} at {a['now']}: no ticket item before the arrival line")
    est = [(float(a.get("deduction", 0)), float(a.get("bonus", 0))) for a, _ in ticketed]
    print(f"      estimated from the predicted pay: {sum(d for d, _ in est):,.0f} deducted and {sum(b for _, b in est):,.0f} added")
    if len(snaps) >= 2:
        t0, t1 = snaps[0]["t"], snaps[-1]["t"]
        income = snaps[-1]["bal"]["playerIncomeTotal"] - snaps[0]["bal"]["playerIncomeTotal"]
        answered = sum(float(it["basePrice"]) * (1.0 if answer(it) is None else answer(it)) for a, it in ticketed
                       if it is not None and t0 <= int(a["now"]) <= t1)   # an unanswered unit is paid in full
        people = sum(float(e["basePriceSum"]) for e in events if e["id"] != "TransportVehicleSystem" and t0 <= int(e["now"]) <= t1)
        scales = sorted({float(a["payScale"]) for a, _ in ticketed if "payScale" in a})
        if answered and scales:
            print(f"INFO  player income {income:,} against (cargo basePrice x answers {answered:,.0f} + passenger basePrice "
                  f"{people:,.0f}) x pay scale {scales[-1]:.4f}: {income / ((answered + people) * scales[-1]):.3f} (units near "
                  f"either end of the run blur it; months of play bring it to about 1.00)")
    ok = answered_ok and ok
    ok = check_stale(lines, start) and ok
    print("RESULT " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def check_stale(lines, start):
    """Stale line warnings: replay each line's buckets between the monthly rolls from the arrival lines counted for it."""
    state = {}                                 # line -> its last logged state (buckets, carried units, warned)
    pending = defaultdict(lambda: [0, 0])      # arrivals and stale arrivals counted for a line since that state
    problems = []
    params, roll_warned, roll_sent, last_sent = None, None, None, None
    rolls = replayed = 0

    # Each unit's staleUnit against the rule: not good, or corrected freshness below the stale threshold. The threshold is
    # fixed within a load (only a load can change an in-game setting) and every staleRoll line logs it. A load with the warnings switched
    # off writes no staleRoll line and counts no unit, so the check is skipped.
    thresholds = {m.group(1) for ln in lines[start:] for m in [re.search(r"BEST_BEFORE staleRoll .*?\bstaleBelow=(\S+)", ln)] if m}
    if len(thresholds) > 1:
        problems.append(f"staleRoll lines disagree on staleBelow: {sorted(thresholds)}")
    below = float(next(iter(thresholds))) if len(thresholds) == 1 else None
    unit_checked = 0
    if below is not None:
        for i, ln in enumerate(lines[start:], start):
            m = re.search(r"BEST_BEFORE arrival (.*)", ln)
            d = kv(m.group(1)) if m else {}
            if "staleUnit" not in d or "corrected" not in d:
                continue
            corrected = float(d["corrected"])
            if d.get("good") == "true" and abs(corrected - below) < 1e-9:
                continue                       # on the threshold itself: the logged digits cannot tell which side it fell
            expected_stale = d.get("good") != "true" or corrected < below
            unit_checked += 1
            if (d["staleUnit"] == "true") != expected_stale and len(problems) < 10:
                problems.append(f"line {i + 1}: unit {d.get('unit')} good={d.get('good')} corrected={corrected:.4f} logged "
                                f"staleUnit={d['staleUnit']}, the rule (below {below}) says {str(expected_stale).lower()}")

    def close_roll():
        expected = roll_sent if roll_sent is not None else last_sent
        if roll_warned is not None and expected is not None and expected != roll_warned:
            problems.append(f"month {int(params['month'])}: lines marked warned {sorted(roll_warned)}, sent {sorted(expected)}")

    for i, ln in enumerate(lines[start:], start):
        m = re.search(r"BEST_BEFORE (\w+) ?(.*)", ln)
        if not m:
            continue
        kind, rest = m.groups()
        if kind == "arrival":
            d = kv(rest)
            key = d.get("staleLine")
            if key and key != "none":
                pending[key][0] += 1
                pending[key][1] += d.get("staleUnit") == "true"
        elif kind == "staleRoll":
            close_roll()
            params = {k: float(v) for k, v in kv(rest).items()}
            roll_warned, roll_sent = set(), None
            rolls += 1
        elif kind == "staleWarnings":
            d = kv(rest)
            if "error" in d:
                problems.append(f"line {i + 1}: sending the warnings failed: {d['error']}")
            last_sent = set() if d["lines"] == "none" else set(d["lines"].split(","))
            if roll_warned is not None:
                roll_sent = last_sent
        elif kind == "staleLine":
            d = kv(rest)
            key, decision = d["line"], d["decision"]
            buckets = [(b[0], float(b[1:])) for b in d["buckets"].split(",")]
            entry = {"buckets": buckets, "units": int(d["units"]), "stale": int(d["stale"]), "warned": d["warned"] == "true"}
            prev, (units, stale) = state.get(key), pending[key]
            pending[key] = [0, 0]
            if decision == "new" or params is None:
                state[key] = entry
                continue
            share = float(d["share"])
            where = f"month {int(params['month'])} line {key}"
            if abs(sum(v for _, v in buckets) / len(buckets) - share) > 1e-3:
                problems.append(f"{where}: share {share} is not the mean of its buckets")
            if entry["warned"]:
                roll_warned.add(key)
            if decision == "gone":
                state.pop(key, None)
                continue
            state[key] = entry
            if decision == "reset":
                continue
            was = prev["warned"] if prev else None
            warn_at, clear_at = params["warnAbove"], params["clearBelow"]
            if decision == "warn" and not (share > warn_at - 1e-4 and entry["warned"] and was is not True):
                problems.append(f"{where}: warned at share {share} (warns above {warn_at})")
            elif decision == "clear" and not (share < clear_at + 1e-4 and not entry["warned"] and was is not False):
                problems.append(f"{where}: cleared at share {share} (clears below {clear_at})")
            elif decision == "hold" and ((was is not None and entry["warned"] != was)
                                         or (entry["warned"] and share < clear_at - 1e-4)
                                         or (not entry["warned"] and share > warn_at + 1e-4)):
                problems.append(f"{where}: held at share {share} with warned={entry['warned']}")
            if prev is None or params["steps"] != 1:
                continue
            units += prev["units"]
            stale += prev["stale"]
            last_source, last_share = prev["buckets"][-1]
            if units >= params["minUnits"]:
                new, carried = ("m", stale / units), (0, 0)
            else:
                new, carried = ("d" if last_source == "d" else "i", last_share), (units, stale)
            expected = prev["buckets"][1:] + [new]
            same = len(expected) == len(buckets) and all(a[0] == b[0] and abs(a[1] - b[1]) <= 1e-3 for a, b in zip(expected, buckets))
            if not same or carried != (entry["units"], entry["stale"]):
                problems.append(f"{where}: buckets {d['buckets']} units={entry['units']} stale={entry['stale']}, rebuilt from the "
                                f"arrivals: {','.join(f'{s}{v:.4f}' for s, v in expected)} units={carried[0]} stale={carried[1]}")
            replayed += 1
    close_roll()

    if not rolls:
        print("INFO  stale lines: no monthly roll after the last load (the run is shorter than a game month, or warnings are off)")
        return True
    warned_now = sorted(k for k, e in state.items() if e["warned"])
    print(("PASS" if not problems else "FAIL") + f"  stale lines: {rolls} monthly rolls, {len(state)} lines tracked, {replayed} "
          f"bucket rolls rebuilt from the arrivals, {unit_checked} units checked against the threshold, {len(warned_now)} lines warned at the end"
          + (f" ({', '.join(warned_now[:10])}{', ...' if len(warned_now) > 10 else ''})" if warned_now else ""))
    for problem in problems[:10]:
        print("      " + problem)
    return not problems


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
