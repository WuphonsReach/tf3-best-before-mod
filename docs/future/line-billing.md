# Billing the adjustment to the line and vehicle

## In short

- **Goal.** A unit's bonus or deduction should land on the vehicle and line that carried it, at delivery, so the line windows and the floating figures show it. Today it goes to the player only, because the game shares a unit's pay along its chain by a formula we do not know (see [discarded](discarded.md)).
- **Lead: let the engine do it.** Before it pays, the engine raises `OnCalcTicketPrice`. The event names each item with its vehicle, line, unit (`simEntity`), stock list, `basePrice` and `distance`, and any subscriber can return a pay multiplier per item. The base game uses this for the company level (one multiplier for all items) and for subsidies (x2 per item on the lines that earned it) (`game_mechanics.zip`: `company/company_growth.script.tl`, `subventions/deliver_cargo/deliver_cargo.script.tl`; the record is `CalcTicketPriceCargoEvent` in `base/tealdef/scripts/gamescript.d.tl`). If the mod returned `1 + adjustment` per unit, the engine would pay the changed amount and share it out by its own formula. Every ledger in the chain would then be right without our knowing the split, and the journal bookings, the pay prediction and the `cargoIncomeScript` stub could go.
- **How sure.** The hook exists and the base game uses it for exactly this. None of it has been tried from a mod. Unknown: whether the event comes once per unit or once per leg, and whether at delivery or at each unloading; how the engine combines our answer with the company level's and a subsidy's (product, or the last answer wins); whether 0 and values above 1 work; whether the unit's freshness can be read at that moment.
- **Fallback.** Keep the bookings but split each unit's adjustment over its legs and book every share to that leg's vehicle and line as well as to the player. `PickupPoint.position` gives each leg's start, so a split by straight-line distance is possible. That only helps if the observe run shows the engine's split.
- **Status.** A test-only probe is on branch `2026-10-24-ticket-price-probe` (settings.tl `ticketPriceProbe`, read by `tools/ticket_probe.py`). It has not been run in the game.

## The probe

`ticketPriceProbe` in settings.tl is read on each load like `logLevel`, so no restart is needed between the runs. The first load with it on subscribes to the event; the subscription stays in the save.

- `"observe"` logs a `ticketPrice` line per event (cargo and passengers, with the `basePrice` sum) and a `ticketItem` line per cargo item: unit, vehicle, line, stock list, `basePrice`, `distance`, the unit's legs, its last leg, the good flag and corrected freshness. At `full` it also logs the vehicle's `unloadPendingIncome`. It answers nothing.
- `"scale"` answers `ticketPriceMultiplier` for every cargo item and books no adjustments, so the ledgers show the engine's pay alone.

Nothing is written to the state from this handler (game scripts may run in one Lua state per thread).

## Runs, in order

Use a save with transferred cargo (at least one chain of two lines) and `logLevel = "full"`, several game months each. Copy the log to `local/logs/` and run `python3 tools/ticket_probe.py <log>`.

1. **observe.** Is there one item per unit or one per leg? Does it come at the same tick as the arrival, and which vehicle and line does it name? Is the stock list the arrival target? What is `basePrice` against the predicted pay: about 1 / company multiplier if the company factor comes after it? Does the passenger `basePrice` sum explain the income above the prediction on some saves (see [revisit-later](revisit-later.md))?
2. **scale 0.5.** Engine pay / predicted pay near 0.5 means our answer is multiplied with the company level's. Near 0.5 / payScale means it replaced it, which would also drop subsidies, so the mod could not use it as is. Near 1 means it was ignored. Check that the line windows' income and the blue figure over unloading vehicles halve too.
3. **scale 0.** Does a spoiled unit then pay nothing, or is 0 read as "no answer"?
4. **scale 2.** Do values above 1 work (needed for the bonus)? A subsidy's x2 says yes for the base game.

If all four come out right, the next step is a mode that answers `1 + curveAdjustment(freshness)` per unit, compared against the journal bookings on the same save.
