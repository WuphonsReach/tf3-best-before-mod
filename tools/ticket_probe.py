#!/usr/bin/env python3
"""Read a ticket price probe run (settings.tl ticketPriceProbe "observe" or "scale") from the game log.

Usage: tools/ticket_probe.py local/logs/stdout-....txt

The probe logs every OnCalcTicketPrice event (ticketPrice lines) and, for cargo, each item it names (ticketItem lines). This
joins the items to the arrival lines of the same unit and answers:
  - does the event name a unit once (at delivery) or once per leg, and when does it come against the arrival event,
  - which vehicle and line it names (the last leg's, or each leg's),
  - whether its stock list is the arrival's target, and how its basePrice compares with the probe's predicted pay,
  - how the player's income over the run compares with the predicted pay and with the basePrice sums. In a "scale" run with
    multiplier m: income / predicted near m means the answer is multiplied with the company level's; near m / payScale
    (payScale = the Cargo Income setting x the company multiplier) means it replaced it; near 1 means the engine ignored it.
Needs logLevel "curve" (or "full" for the chains and the vehicles' pending income).
"""
import re
import statistics
import sys
from collections import Counter, defaultdict


def kv(text):
    return dict(re.findall(r'(\w+)=("[^"]*"|\S+)', text))


def spread(values):
    values = sorted(values)
    if not values:
        return "none"
    return (f"min {values[0]:.4g}, median {statistics.median(values):.4g}, max {values[-1]:.4g} "
            f"({len(values)} values)")


def main(path):
    lines = open(path, errors="replace").read().splitlines()
    start = max((i for i, ln in enumerate(lines) if "BEST_BEFORE preRunFn" in ln), default=0)
    # Entity ids are reused, so an item is paired with the next arrival line of the same id (the ticket line comes first).
    events, items, arrivals, snaps, sends, errors = [], [], {}, [], [], []
    open_items, pairs = defaultdict(list), []
    for i, ln in enumerate(lines[start:], start):
        m = re.search(r"BEST_BEFORE (\w+) ?(.*)", ln)
        if not m:
            continue
        kind, rest = m.groups()
        d = kv(rest)
        d["_i"] = i
        if kind == "ticketPrice" and "error" in d:
            errors.append(ln.strip())
        elif kind == "ticketPrice" and "items" in d:
            events.append(d)
        elif kind == "ticketItem":
            items.append(d)
            open_items[d["unit"]].append(d)
        elif kind == "arrival":
            arrivals[(d["unit"], i)] = d
            if open_items[d["unit"]]:
                pairs.append((open_items[d["unit"]], d))
                open_items[d["unit"]] = []
        elif kind == "journal":
            snaps.append(d)
        elif kind == "sending":
            sends.append(d)
    if not events:
        sys.exit(f"{path}: no ticketPrice lines after the last load. Set ticketPriceProbe and logLevel \"curve\" or \"full\" in "
                 f"settings.tl and load the save")

    modes = Counter((e["probe"], e["multiplier"]) for e in events if e["id"] == "TransportVehicleSystem")
    print(f"Probe modes seen (cargo events): {dict(modes)}")
    for errline in errors[:5]:
        print(f"ERROR {errline}")
    by_id = defaultdict(lambda: [0, 0, 0.0])
    for e in events:
        by_id[e["id"]][0] += 1
        by_id[e["id"]][1] += int(e["items"])
        by_id[e["id"]][2] += float(e["basePriceSum"])
    for event_id, (n, k, total) in by_id.items():
        print(f"Events from {event_id}: {n}, items {k} (up to {max(int(e['items']) for e in events if e['id'] == event_id)} "
              f"per event), basePrice sum {total:,.0f}")

    # Once per unit or once per leg?
    joined = pairs
    unpaired = sum(len(v) for v in open_items.values())
    counts = Counter((len(v), a.get("legs", "?")) for v, a in joined)
    print("Items per delivered unit, by its legs (items, legs): " + ", ".join(f"{k}: {n}" for k, n in sorted(counts.items())))
    print(f"Items paired with an arrival line: {sum(len(v) for v, _ in joined)} of {len(items)} ({unpaired} without one: "
          f"the log ended, or the event names units that are not delivered); arrival lines {len(arrivals)}")
    same_unit = sum(1 for it in items if it["vehicle"] == it["unit"])
    if same_unit:
        print(f"Items whose vehicle field holds the unit itself: {same_unit} of {len(items)}")
    if joined:
        dt = [int(a["now"]) - int(v[0]["now"]) for v, a in joined]
        before = sum(1 for v, a in joined if v[0]["_i"] < a["_i"])
        print(f"Arrival time minus ticket time (clock units): {spread(dt)}; ticket line first in the log for {before}")
        same_target = sum(1 for v, a in joined if v[-1]["stockList"] == a["target"])
        print(f"Ticket stockList equal to the arrival target: {same_target} of {len(joined)}")
        last_line = sum(1 for v, a in joined if v[-1]["line"] == v[-1].get("lastLine"))
        last_vehicle = sum(1 for v, a in joined if v[-1]["vehicle"] == v[-1].get("lastVehicle"))
        print(f"Ticket names the unit's last leg: line {last_line}, vehicle {last_vehicle} of {len(joined)}")
        multi = [(v, a) for v, a in joined if a.get("legs", "1") != "1"]
        if multi:
            print(f"Units with more than one leg: {len(multi)}; items for them: "
                  + ", ".join(f"{k}: {n}" for k, n in sorted(Counter(len(v) for v, _ in multi).items())))
            for v, a in multi[:5]:
                print(f"  unit {a['unit']} chain {a.get('chain', '(logLevel full shows the chain)')}: "
                      + "; ".join(f"vehicle {it['vehicle']} line {it['line']} basePrice {float(it['basePrice']):.0f} "
                                  f"distance {it['distance']}" for it in v))
        ratio = [sum(float(it["basePrice"]) for it in v) / float(a["predictedIncome"])
                 for v, a in joined if a.get("predictedIncome", "n/a") not in ("n/a", "0")]
        print(f"basePrice / predicted pay per unit: {spread(ratio)}")
        scales = {a.get("payScale") for _, a in joined}
        print(f"payScale in the arrival lines: {', '.join(sorted(s for s in scales if s))}")

    pending = Counter("nil" if it.get("pending", "nil") == "nil" else "amount" for it in items if "pending" in it)
    if pending:
        print(f"Vehicle pending income at the ticket event: {dict(pending)}")

    # The player's income over the run.
    if len(snaps) >= 2:
        first, last = snaps[0], snaps[-1]
        t0, t1 = int(first["t"]), int(last["t"])
        income = float(last["playerIncomeTotal"]) - float(first["playerIncomeTotal"])
        booked = sum(float(s["amount"]) for s in sends if s.get("ledger") == "player" and first["_i"] < s["_i"] <= last["_i"])
        predicted = sum(float(a["predictedIncome"]) for a in arrivals.values()
                        if a.get("predictedIncome", "n/a") != "n/a" and t0 <= int(a["now"]) <= t1)
        cargo_base = sum(float(e["basePriceSum"]) for e in events
                         if e["id"] == "TransportVehicleSystem" and t0 <= int(e["now"]) <= t1)
        people_base = sum(float(e["basePriceSum"]) for e in events
                          if e["id"] != "TransportVehicleSystem" and t0 <= int(e["now"]) <= t1)
        engine = income - booked
        print(f"Player income {t0} to {t1}: {income:,.0f}, of it booked by the mod {booked:,.0f}, engine pay {engine:,.0f}")
        if predicted:
            print(f"  engine pay / predicted cargo pay {engine / predicted:.3f} (predicted {predicted:,.0f})")
        if cargo_base:
            print(f"  engine pay / cargo basePrice sum {engine / cargo_base:.3f}; / cargo + passenger basePrice "
                  f"{engine / (cargo_base + people_base):.3f} (cargo {cargo_base:,.0f}, passengers {people_base:,.0f})")
        print("  Pay lands as vehicles finish unloading, so units near either end of the run blur these ratios; use runs "
              "of several game months.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
