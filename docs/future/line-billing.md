# Billing the adjustment to the line and vehicle

## In short

- **Goal.** A unit's bonus or deduction should land on the vehicle and line that carried it, at delivery, so the line windows and the floating figures show it. With the bookings (1.0.1, and the `bookings` fallback since) it goes to the player only, because the game shares a unit's pay along its chain by a formula we do not know (see [discarded](discarded.md)).
- **Lead: let the engine do it.** Before it pays, the engine raises `OnCalcTicketPrice`. The event names each item with its vehicle, line, unit (`simEntity`), stock list, `basePrice` and `distance`, and any subscriber can return a pay multiplier per item. The base game uses this for the company level (one multiplier for all items) and for subsidies (x2 per item on the lines that earned it) (`game_mechanics.zip`: `company/company_growth.script.tl`, `subventions/deliver_cargo/deliver_cargo.script.tl`; the record is `CalcTicketPriceCargoEvent` in `base/tealdef/scripts/gamescript.d.tl`). If the mod returned `1 + adjustment` per unit, the engine would pay the changed amount and share it out by its own formula. Every ledger in the chain would then be right without our knowing the split, and the journal bookings, the pay prediction and the `cargoIncomeScript` stub could go.
- **How sure.** Five runs on one save. The event comes once per delivered unit, at the delivery tick, naming the unit, the last leg's line and the destination, with `basePrice` the unit's pay before the pay scale. An answer of 0.5 halved the pay: it is multiplied with the company level's multiplier (engine pay matched cargo `basePrice` x 0.5 x pay scale plus passengers x pay scale to 0.2%), and every line of a two-leg chain, boat and truck alike, earned half its usual share. So the engine scales the unit's whole pay before it shares it out, and each line's ledger shows the change at delivery. The event does not show the split (its `vehicleEntity` holds the unit, `distance` is nil). An answer of 0 made a delivered unit pay nothing, on every line of its chain, and an answer of 2 doubled it, on every line of its chain, so the bonus can be paid this way too. The `"curve"` mode, answering `1 + adjustment` per unit, did what the bookings do, with the change on the lines: every answer equalled the unit's rate, the player's income matched to 0.1%, every tracked line's income moved by its units' average answer, and the grain train's window showed $827,966 for a trip that paid $3,043,520 in full. A control stretch with the mod removed from the same save paid that train $3,043,520 again, for cargo at 0% freshness, and the company's income per clock month fell by about what the answers had added (see the end). Still open: how our answer combines with a subsidy's x2 (product is likely, as with the company level).
- **Fallback (not needed: the ticket answer works).** Keep the bookings but split each unit's adjustment over its legs and book every share to that leg's vehicle and line as well as to the player. `PickupPoint.position` gives each leg's start, so a split by straight-line distance is possible, but the engine's split is still unknown (the event does not show it).
- **Status.** The test-only probe is in `main` (settings.tl `ticketPriceProbe`, read by `tools/ticket_probe.py`). All four runs (observe, scale 0.5, 0 and 2) are done. Run 5 (`"curve"`) is done, and ticket billing is the mod's way of paying from 1.2 (`billing = "ticket"` in settings.tl, the bookings kept as `"bookings"`; the probe's `"curve"` value became that setting). A save with ticket billing loads without the mod as far as the billing goes: the game drops the mod's game script and its subscription (`Removing entity ... for GameScript best_before_1::/probe.gs which is no longer available`); that load failed on the Stale Cargo warning instead ([stale-line-warnings](../stale-line-warnings.md)). Open: a subsidy's x2 with an answer.

## The probe

`ticketPriceProbe` in settings.tl is read on each load like `logLevel`, so no restart is needed between the runs. The first load with it on subscribes to the event; the subscription stays in the save.

- `"observe"` logs a `ticketPrice` line per event (cargo and passengers, with the `basePrice` sum) and a `ticketItem` line per cargo item: unit, vehicle, line, stock list, `basePrice`, `distance`, the unit's legs, its last leg, the good flag and corrected freshness. At `full` it also logs the vehicle's `unloadPendingIncome`. It answers nothing.
- `"scale"` answers `ticketPriceMultiplier` for every cargo item and books no adjustments, so the ledgers show the engine's pay alone.
- `"curve"` answers `1 + the curve's adjustment` for every cargo item and books no adjustments. It judges the unit as the arrival handler does (the game's delivery limit, the warehouse pause taken off, the game's spoiled flag), with the curve read from the in-game settings in the handler. The arrival line keeps its `rate` and adds `expectedAdjustment` (what the booking would have been, from the predicted pay) and `billing=ticket`.

Nothing is written to the state from this handler (game scripts may run in one Lua state per thread).

## Runs, in order

Use a save with transferred cargo (at least one chain of two lines) and `logLevel = "full"`, several game months each. Copy the log to `local/logs/` and run `python3 tools/ticket_probe.py <log>`.

1. **observe.** Done, see the results below.
2. **scale 0.5.** Done, see the results below.
3. **scale 0.** Done, see the results below.
4. **scale 2.** Done, see the results below.

All four came out right, so:

5. **curve.** Done, see the results below. Every answer should equal its arrival line's `rate`; the player's income should be the cargo `basePrice` x the answers plus the passenger `basePrice`, all x the pay scale; the lines' ledgers should show each unit's bonus or deduction (the grain train's trip should earn about 30% of its full pay, the oil lines more than full pay). `tools/ticket_probe.py` checks the first two.

## Results

**Observe**, WR26A Giga-Tv3 1915 (save 1024-1620; calendar 0.25x; pay scale 0.714; the save's curve +50% down to 50% freshness, break-even 15%), Oct 1915 to Mar 1916, `logLevel` `full`, log `local/logs/stdout-20261024-ticket-observe.txt`, `tools/ticket_probe.py`:

- 4,195 cargo events (`TransportVehicleSystem`, 1 to 4 items each) and 11,220 passenger events (`SimEntityAtVehicleSystem`, 17,634 items). No errors.
- 4,875 cargo items and 4,875 arrival lines, paired one to one. Each item comes at the same clock time as its unit's arrival and is logged first. Its stock list is the arrival target in every case, and its line the unit's last leg. The 2,864 two-leg units (boat to warehouse to truck: oil, fish, fuel) each got one item, naming the truck line; no item came when a boat unloaded into a warehouse. Entity ids are reused, so pair items with arrivals in log order, not by id.
- `vehicleEntity` held the unit's own id on every item, and `distance` was nil. The vehicle's `unloadPendingIncome` was nil at the event.
- `basePrice` / predicted pay: 1.361 to 1.429, median 1.399 = 1 / 0.714, so `basePrice` is the pay before the Cargo Income setting and the company multiplier.
- Player income over the run 199.0 million, of which 47.0 million were the mod's bookings; the engine's 152.0 million is 1.442 x the predicted cargo pay but 0.714 x the cargo + passenger `basePrice` (147.5 + 65.5 million). Passenger fares explain the income above the cargo prediction on this save.
- Side finding: the grain train on "CRA-DER CXR West Grain" (64 units, Mar 7 to 9 1916) showed its cargo bar at 25% on Feb 14, 7% on Mar 5 and 6% as unloading began; the mod's freshness for the same units at the same clock times was 29.9%, 13.5% and 12.0%. The mod now uses the game's adjusted delivery time ([findings](../findings.md)).

**Scale 0.5**, the same game from save 1024-1735 (Aug to Oct 1916; the stale slider was moved to 0% on this load), log `local/logs/stdout-20261024-ticket-scale05.txt`. 1,026 cargo items, each paired with its arrival as before; no bookings were sent.

- Player income 21.89 million against cargo `basePrice` 26.32 million and passenger `basePrice` 17.43 million at pay scale 0.714. Our answer multiplied with the company level's: 26.32 x 0.5 x 0.714 + 17.43 x 0.714 = 21.85 million (1.002). Had it replaced the company's multiplier the pay would be 25.61 million (0.855); had it been ignored, 31.25 million (0.700).
- Line ledgers (income = the upward steps of each line's `ACCOUNT` balance in the journal lines, against the pay of the units whose chain includes the line):

| Line | Leg | Share of pay, observe | Share, scale 0.5 | Ratio |
|---|---|---|---|---|
| PET CS Oil Tankers East Port N1 | boat | 0.848 | 0.423 | 0.499 |
| PET CS Oil Tankers East Port N2 | boat | 0.873 | 0.439 | 0.504 |
| PET CS Oil Tankers East Port S4 | boat | 0.892 | 0.437 | 0.490 |
| PET CS Oil Tankers East Port N3 | boat | 0.895 | 0.448 | 0.500 |
| PET East Port Oil Cargo Shuttle Trucks | truck | 0.105 | 0.052 | 0.493 |
| BRE CS Fish W-1 | boat | 0.653 | 0.327 | 0.501 |
| BRE Fish Trucks 1 | truck | 0.347 | 0.172 | 0.497 |
| THO CS Fishery 1 | boat | 0.112 | 0.066 | 0.591 |
| Line 3 (THO fish trucks) | truck | 0.922 | 0.546 | 0.592 |

  The two THO lines (63 units in the short run) and two oil boats not listed (S2 0.409, CRA-E1 0.531) are further from 0.5, as expected where few deliveries fall near the ends of a run. The shares themselves differ by chain (oil: boat about 87%, truck 10%; THO fish: boat 11%, truck 92%), so the split is not a fixed rule per leg.
- The arrival lines now carry the game's adjusted delivery time and the delivering vehicle's average quality. The adjusted time was 1.4 x the cargo file's time for all eight cargo types (grain 1,800 s, fish 1,575 s, oil 4,200 s), and on the 130 arrivals where one unit was left in the vehicle the vehicle's quality equalled 1 - age / adjusted time to within 0.0006 (against up to 0.04 off for the mod's 1.5 x). See [revisit-later](revisit-later.md).

**Scale 0**, the same game from save 1024-1746 (Oct 1916, stale slider back at 5%; saved as 1024-1804 on exit), log `local/logs/stdout-20261024-ticket-scale0.txt`. 1,024 cargo items, all answered 0.

- Player income 10.91 million, against passenger `basePrice` 15.17 million x 0.714 = 10.84 million (1.007): all of it is fares, and the cargo (`basePrice` 31.02 million) paid nothing.
- Every tracked oil and fish line, boats and trucks, earned 0 from the units it carried, apart from 5,082 on one oil boat at the start of the run.
- The grain train on "CRA-DER CXR West Grain" unloaded its 64 units at Dereham on Oct 7 to 9 1916 (`basePrice` 4.26 million). Its window showed no blue income figure during the unload, and its Last Year balance went from $-584,544 to $-604,028 (running costs only), where the same trip in the observe run ended at $2,440,466. The game's freshness for the 64 units was 3.5% to 6.4% (bar 5.8% at the start of the unload), the mod's 10.0% to 12.7%; 32 of them were below the 5% stale setting by the game's measure.

**Scale 2**, the same game from save 1024-1804 (Nov 12 1916 to Feb 18 1917, stale slider at 5%; saved as 1024-1818), log `local/logs/stdout-20261024-ticket-scale2.txt`. 2,040 cargo items (1,177 of them two-leg units), all answered 2, each paired with its arrival as before; no errors.

- Player income 108.75 million, against cargo `basePrice` 63.03 million x 2 x 0.714 + passenger `basePrice` 27.24 million x 0.714 = 109.50 million (0.993).
- Line ledgers, share of pay against the observe run:

| Line | Leg | Share of pay, observe | Share, scale 2 | Ratio |
|---|---|---|---|---|
| PET CS Oil Tankers East Port N1 | boat | 0.848 | 1.696 | 1.999 |
| PET CS Oil Tankers East Port N2 | boat | 0.873 | 1.754 | 2.010 |
| PET CS Oil Tankers East Port N3 | boat | 0.895 | 1.791 | 2.000 |
| PET CS Oil Tankers East Port S2 | boat | 0.849 | 1.697 | 2.000 |
| PET CS Oil Tankers East Port CRA-E1 | boat | 0.892 | 1.821 | 2.041 |
| PET CS Oil Tankers East Port S4 | boat | 0.892 | 1.515 | 1.698 |
| PET East Port Oil Cargo Shuttle Trucks | truck | 0.105 | 0.227 | 2.153 |
| BRE CS Fish W-1 | boat | 0.653 | 1.305 | 1.999 |
| BRE Fish Trucks 1 | truck | 0.347 | 0.695 | 2.003 |
| THO CS Fishery 1 | boat | 0.112 | 0.205 | 1.838 |
| Line 3 (THO fish trucks) | truck | 0.922 | 1.692 | 1.836 |

  Most lines doubled to within 1%. S4 (127 units) and the oil trucks are further off, as is the THO chain (117 units, both legs off by the same factor); each line is paid as its vehicles unload, so deliveries near the ends of a three-month run shift the shares.

**Curve**, the same game from save 1024-1904 (Dec 15 1917 to Jul 1918, saved as 1024-1939 on the way; the save's curve: +50% down to 50% freshness, full pay at 15%, nothing at 0% and for spoiled cargo), log `local/logs/stdout-20261024-1951.txt`. 4,617 cargo items (2,627 of them two-leg units), each paired with its arrival as before; no errors.

- Every answer equalled the `rate` in the unit's arrival line (4,617 of 4,617); answers ran from 0.16 to 1.5, median 1.5.
- Player income 191.8 million, against (cargo `basePrice` x our answers 203.2 million + passenger `basePrice` 65.2 million) x 0.714 = 191.6 million (1.001). The cargo pay the answers added, 41.0 million, is what the bookings would have added from the predicted pay (40.9 million).
- Line ledgers, share of pay against the observe run, over the average answer of the units each line carried:

| Line | Leg | Average answer | Share, observe | Share, curve | Ratio / average answer |
|---|---|---|---|---|---|
| PET CS Oil Tankers East Port N1 | boat | 1.500 | 0.848 | 1.263 | 0.993 |
| PET CS Oil Tankers East Port N2 | boat | 1.500 | 0.873 | 1.318 | 1.007 |
| PET CS Oil Tankers East Port N3 | boat | 1.500 | 0.895 | 1.336 | 0.995 |
| PET CS Oil Tankers East Port S2 | boat | 1.500 | 0.849 | 1.272 | 0.999 |
| PET CS Oil Tankers East Port S4 | boat | 1.500 | 0.892 | 1.312 | 0.980 |
| PET CS Oil Tankers East Port CRA-E1 | boat | 1.500 | 0.892 | 1.420 | 1.061 |
| PET East Port Oil Cargo Shuttle Trucks | truck | 1.500 | 0.105 | 0.162 | 1.025 |
| BRE CS Fish W-1 | boat | 1.500 | 0.653 | 0.969 | 0.990 |
| BRE Fish Trucks 1 | truck | 1.500 | 0.347 | 0.510 | 0.979 |
| THO CS Fishery 1 | boat | 1.500 | 0.112 | 0.165 | 0.988 |
| Line 3 (THO fish trucks) | truck | 1.500 | 0.922 | 1.366 | 0.988 |
| Line 261716 (one leg) | | 1.361 | 1.000 | 1.361 | 1.000 |

- The grain train on "CRA-DER CXR West Grain" unloaded its 64 units at Dereham on Jul 13 to 15 1918 at 2.4% to 5.5% freshness (cargo bar 5% to 3% during the unload). Its window's income figure for the trip was $827,966 and its Last Year balance went from $-584,544 to $243,422, where each earlier trip showed $3,043,520. The log gives the same: full pay $3,043,567, pay x the answers $827,996 (average answer 0.272). The bookings would have taken $2,213,579 from the player and left the line at the full $3,043,520.

**Ticket billing as the default** (`billing = "ticket"`, the shipped settings apart from `logLevel`), the same game from save 1024-1939 (Jul 1918 to Feb 1919; saved as 1024-2036), log `local/logs/stdout-20261024-ticket-default.txt`. 4,799 cargo units, no errors; `tools/verify_run.py` passed (every unit answered with its rate).

- Player income 193.5 million against (cargo `basePrice` x the answers 200.3 million + passenger `basePrice` 71.4 million) x 0.714: 0.997.
- The tracked lines' income moved by their units' average answer as in the curve run (0.95 to 1.06 of it; line 261716, one leg, 1.000).
- The grain train unloaded 64 units at 2.4% to 5.1% freshness at Dereham on Feb 12 to 14 1919: its floating income figure read $740,297 and its Last Year balance went from $-584,544 to $138,217; the log gives full pay $3,043,567 and pay x the answers $740,327 (average answer 0.243).

**No-mod control**, the same game from save 1024-2203 (save 1024-2036 with the Stale Cargo warnings switched off and saved, Feb 15 1919), loaded with Best Before deactivated and played to Jul 6 1919 (saved as 1024-2235). The log (`local/logs/stdout-20261024-warnings-switch.txt`, from 02:04:37Z) has no `BEST_BEFORE` line, so the figures are from the saves' journals and the screenshots.

- The grain train unloaded its 64 units at Dereham on Jul 6 1919 at 0% freshness (the cargo bar, read by the player). Its floating income figure read $3,043,520, the full pay the log predicted for each ticket-billing trip ($3,043,567), and its Last Year balance went from $-606,951 to $2,460,925. Its window's income chart shows the whole history: three trips at about $3.0 million, the two ticket-billing trips at about $0.83 million (Jul 1918) and $0.74 million (Feb 1919), then $3.0 million again.
- The company's journal, diffed between saves and taken per clock month (121,750 clock units): running costs the same in both stretches (rail $1.69 million a month against $1.71 million, the other rows within 1%), so the fleet did not change. Income without the mod $5.61 million a month (167.3 million over 29.8 clock months), with ticket billing $6.89 million (193.5 million over 28.1). Ratio 0.81. The ticket run's own log predicts 0.79: cargo `basePrice` 143.1 million paid 200.3 million with the answers (average answer 1.40 on this save's curve, +50% down to 50% freshness, which most units reached), passengers 71.4 million either way, so without the answers (143.1 + 71.4) / (200.3 + 71.4) = 0.79. The 2% gap is two different stretches of the same game (demand and routes move between them).

| Carrier row (journal) | With ticket billing, per clock month | Without the mod, per clock month | Ratio |
|---|---|---|---|
| Rail income | $4,764,176 | $3,965,392 | 0.83 |
| Road income | $582,330 | $416,848 | 0.72 |
| Tram income (passengers only) | $652,605 | $661,570 | 1.01 |
| Water income | $890,344 | $566,670 | 0.64 |
| All income | $6,890,000 | $5,610,000 | 0.81 |
| Running costs, rail | $1,705,122 | $1,690,471 | 0.99 |

Carriers by the journal's category byte, read in the order the game's type definitions declare them (`Carrier` in `api/type.d.tl`: ROAD 0, RAIL 1, TRAM 2, OTHER 3, AIR 4, WATER 5); the order is not otherwise checked, but it fits: the trams carry only passengers and did not move, the boats carry fresh fish and oil and moved the most.
