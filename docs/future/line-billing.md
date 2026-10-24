# Billing the adjustment to the line and vehicle

## In short

- **Goal.** A unit's bonus or deduction should land on the vehicle and line that carried it, at delivery, so the line windows and the floating figures show it. Today it goes to the player only, because the game shares a unit's pay along its chain by a formula we do not know (see [discarded](discarded.md)).
- **Lead: let the engine do it.** Before it pays, the engine raises `OnCalcTicketPrice`. The event names each item with its vehicle, line, unit (`simEntity`), stock list, `basePrice` and `distance`, and any subscriber can return a pay multiplier per item. The base game uses this for the company level (one multiplier for all items) and for subsidies (x2 per item on the lines that earned it) (`game_mechanics.zip`: `company/company_growth.script.tl`, `subventions/deliver_cargo/deliver_cargo.script.tl`; the record is `CalcTicketPriceCargoEvent` in `base/tealdef/scripts/gamescript.d.tl`). If the mod returned `1 + adjustment` per unit, the engine would pay the changed amount and share it out by its own formula. Every ledger in the chain would then be right without our knowing the split, and the journal bookings, the pay prediction and the `cargoIncomeScript` stub could go.
- **How sure.** The hook exists and the base game uses it for exactly this. The observe run (below) showed the event comes once per delivered unit, at the delivery tick, naming the unit, the last leg's line and the destination, with `basePrice` the unit's pay before the pay scale (engine pay = (cargo + passenger `basePrice`) x pay scale, to 0.1%). It does not name the earlier legs, its `vehicleEntity` holds the unit itself and `distance` is nil, so it tells us nothing about the split. Unknown: whether an answer changes the pay of every leg's line (the engine would share the scaled pay) or only the last one; how the engine combines our answer with the company level's and a subsidy's; whether 0 and values above 1 work.
- **Fallback.** Keep the bookings but split each unit's adjustment over its legs and book every share to that leg's vehicle and line as well as to the player. `PickupPoint.position` gives each leg's start, so a split by straight-line distance is possible, but the engine's split is still unknown (the event does not show it).
- **Status.** A test-only probe is on branch `2026-10-24-ticket-price-probe` (settings.tl `ticketPriceProbe`, read by `tools/ticket_probe.py`). The observe run is done; the scale runs are next.

## The probe

`ticketPriceProbe` in settings.tl is read on each load like `logLevel`, so no restart is needed between the runs. The first load with it on subscribes to the event; the subscription stays in the save.

- `"observe"` logs a `ticketPrice` line per event (cargo and passengers, with the `basePrice` sum) and a `ticketItem` line per cargo item: unit, vehicle, line, stock list, `basePrice`, `distance`, the unit's legs, its last leg, the good flag and corrected freshness. At `full` it also logs the vehicle's `unloadPendingIncome`. It answers nothing.
- `"scale"` answers `ticketPriceMultiplier` for every cargo item and books no adjustments, so the ledgers show the engine's pay alone.

Nothing is written to the state from this handler (game scripts may run in one Lua state per thread).

## Runs, in order

Use a save with transferred cargo (at least one chain of two lines) and `logLevel = "full"`, several game months each. Copy the log to `local/logs/` and run `python3 tools/ticket_probe.py <log>`.

1. **observe.** Done, see the results below.
2. **scale 0.5.** Engine pay / predicted pay near 0.5 means our answer is multiplied with the company level's. Near 0.5 / payScale means it replaced it, which would also drop subsidies, so the mod could not use it as is. Near 1 means it was ignored. Check that the line windows' income and the blue figure over unloading vehicles halve too, on the first leg's line (the boat) as well as the last: that is the question the observe run could not answer.
3. **scale 0.** Does a spoiled unit then pay nothing, or is 0 read as "no answer"?
4. **scale 2.** Do values above 1 work (needed for the bonus)? A subsidy's x2 says yes for the base game.

If all four come out right, the next step is a mode that answers `1 + curveAdjustment(freshness)` per unit, compared against the journal bookings on the same save.

## Results

**Observe**, WR26A Giga-Tv3 1915 (save 1024-1620; calendar 0.25x; pay scale 0.714; the save's curve +50% down to 50% freshness, break-even 15%), Oct 1915 to Mar 1916, `logLevel` `full`, log `local/logs/stdout-20261024-ticket-observe.txt`, `tools/ticket_probe.py`:

- 4,195 cargo events (`TransportVehicleSystem`, 1 to 4 items each) and 11,220 passenger events (`SimEntityAtVehicleSystem`, 17,634 items). No errors.
- 4,875 cargo items and 4,875 arrival lines, paired one to one. Each item comes at the same clock time as its unit's arrival and is logged first. Its stock list is the arrival target in every case, and its line the unit's last leg. The 2,864 two-leg units (boat to warehouse to truck: oil, fish, fuel) each got one item, naming the truck line; no item came when a boat unloaded into a warehouse. Entity ids are reused, so pair items with arrivals in log order, not by id.
- `vehicleEntity` held the unit's own id on every item, and `distance` was nil. The vehicle's `unloadPendingIncome` was nil at the event.
- `basePrice` / predicted pay: 1.361 to 1.429, median 1.399 = 1 / 0.714, so `basePrice` is the pay before the Cargo Income setting and the company multiplier.
- Player income over the run 199.0 million, of which 47.0 million were the mod's bookings; the engine's 152.0 million is 1.442 x the predicted cargo pay but 0.714 x the cargo + passenger `basePrice` (147.5 + 65.5 million). Passenger fares explain the income above the cargo prediction on this save.
- Side finding: the grain train on "CRA-DER CXR West Grain" (64 units, Mar 7 to 9 1916) showed its cargo bar at 25% on Feb 14, 7% on Mar 5 and 6% as unloading began; the mod's freshness for the same units at the same clock times was 29.9%, 13.5% and 12.0%. See [revisit-later](revisit-later.md) (limits per cargo and difficulty).
