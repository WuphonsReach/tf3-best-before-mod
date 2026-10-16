# tf3-best-before-mod

Transport Fever 3 mod: cargo payment scales with freshness.

**Status: early work.** `best_before_1/` is a test probe. For each arriving cargo unit it works out a *freshness deduction* (the part of the pay the freshness curve takes away) and books it back as a negative income entry to the vehicle, its line and the player. It logs everything with lines starting `BEST_BEFORE`. The deduction mechanism has been checked in the game; settings and the final curve are not done.

Planned pay curve: full rate above a freshness threshold, then a straight line down to a minimum rate at 0% freshness, then a fixed rate (default 0%) once the cargo is spoiled.

This is an unofficial mod. It contains no files from the game.

## Licence

MIT, see [LICENSE](LICENSE).

## Development

Type checking uses the Teal compiler (`tl`, install with `luarocks install --local tl`) against the game's own type definitions:

1. Copy `tlconfig.example.lua` to `tlconfig.lua` and replace `<tf3_install_folder>` with your game install path (`tlconfig.lua` is gitignored).
2. Run `tl check best_before_1/content/mod.script.tl`.

## Findings so far

Checked in game on a test save (vegetables and fish, horse carts and ships).

- **Spoiled cargo pays full price in the base game.** Fresh, spoiled and mixed carts are all paid the same: the income function's result times a constant of about 0.96426 that the engine applies afterwards (cause unknown).
- **Pay is straight-line distance**: price factor x 3D distance between pickup and delivery (plus a climb term). The unloading point matters, so the cart that stops slightly further away earns slightly more.
- **The income function cannot see freshness.** `baseConfig.economy.cargoIncomeScript` can be replaced by a mod, but it is called once per cargo unit with only `difficultyFactor`, the price factor and the distance. It is called before the unit's arrival event.
- **Each cargo unit is an entity** (`SimCargo`) with `pickupTime`, a source entity and the vehicle and line it travelled on. `api.engine.util.cargo.isGoodQuality(unit)` tells whether it is spoiled.
- **A unit spoils exactly `timeToDeliverInSeconds x 1.5` after pickup** (1,687,500 ms for vegetables and fish). Freshness is `1 - (now - pickupTime) / that`; the vehicle window's percentage is the load's average. The flag and this formula agreed on all 82 logged units.
- **The cargo type's price function cannot be redirected from a mod at run time.** The `scriptRef` is readable through `api.res.cargoTypeRep.get(id)` but changing it had no effect.
- **Predicting pay in the arrival handler works.** Source and target construction positions give the distance within about 1% of the engine's.
- **Game script rules learned the hard way:** `sendCommand` must not be called from `handleEvent` (assertion `!m_betweenChanges`), journal entries must have `time = -1`, `sendCommand` must be called without a result callback from `update` (a callback raises "Callbacks are currently disallowed"), and module-level variables do not survive between calls, so state goes in the game script `state`. State written by the handler is visible to `update`.
- **A journal booking reaches the account.** `api.cmd.makeJournalBookAssetCmd` with an INCOME entry (negative amount, road carrier) sent from `update` changed the account by exactly the booked amount: -93,084 for five bookings, and +55,798 for a $74,480 cart payment plus one -18,682 booking. The booking shows on the account only, not on the line's balance panel, since the entry carries no line or vehicle. Because there is no callback, success is judged from the account.

- **Vehicles and lines have their own ledgers.** The first argument of `makeJournalBookAssetCmd` is the entity whose account the entry goes to, not only the player. A vehicle, a line and the player each carry an `ACCOUNT` component, and an entry booked to one changes only that one. Real pay lands in all three, so a freshness deduction is booked to all three (vehicle, line, player). Over about 32 game minutes (two year-periods and about 15 month-periods of the game clock, with the calendar stopped) nothing booked to a vehicle or line reached the player's account.
- **Line panel and account timing.** The log books pay per unit as each arrives, but the line's balance panel only moves when a whole cart finishes unloading (steps of about $74.5k), so a screenshot taken mid-unload is short by up to a cart. The account also drops in lumps of roughly $35-45k when the game books running costs for every vehicle together (the red `$-391` labels over carts are each vehicle's share). The line panel sometimes gains about $6k while the account does not move (seen again in the booking run); cause unknown.
- **The three-way deduction was checked on a 4x-calendar save** (about 8 minutes, Mar 1901 to Mar 1906, 104 units deducted, 992,034 in total). Every tracked vehicle and line balance moved by pay minus running costs minus the deductions, within 3% of what the arrivals predicted (without the deductions the derived pay would have been 0.19 to 0.82 of the prediction on the lines that were deducted). The 29 spoiled and 75 part-fresh road units were all deducted; the account figure on screen matched the logged player balance, apart from the widget sometimes lagging a few seconds.
- **Ships are deducted too.** A second run on the same save shrank the limit for water vehicles to a quarter (a test change, since reverted), so the fish counted as about 20% fresh and 54 ship units were deducted (197,529 in total, about 3,650 each) from two ship vehicles, the ship line and the player. All ledgers stayed within 3% of the prediction. The game's own load bar still showed the fish at 80-99%, because only the mod's calculation used the shorter limit. Rail, tram and air have not been tried (the test save has none).
- **Not yet checked:** the probe still uses one limit (1,687,500 ms) for every cargo type. The player's account earns about 14% more than the arrivals predict (ratio 1.11 to 1.16 with the deductions in); cause unknown.

## Status

The probe in `best_before_1/content/probe.script.tl` computes the freshness deduction for each arriving unit, queues it in the game script state, and `update` sends it summed per vehicle, line and player (and carrier, taken from the vehicle) with no result callback, for every unit (the old 400-unit test cap is gone). The deduction is still the probe's test curve (full pay above 50% freshness, 30% at 0%, 0% once spoiled), not yet adjustable.

`tools/verify_run.py` checks a run from the game log alone: it compares each tracked ledger's balance change with the pay the arrivals predicted, the deductions sent and the running-cost batches, so a run needs few or no screenshots. Run it on a copy of `crash_dump/stdout.txt`. It ignores arrivals in the last 30,000 clock units before the final snapshot, because their pay may not have landed yet; pay shows in the next journal snapshot, at most about 5,200 units after the arrival. (A 30,000 margin dropped pay that had already landed and failed one vehicle and one line on a live log.)

Next: adjustable X, M and S, and a freshness bonus above a threshold (and in-game settings through `mod.json`), and dropping the income-function logging stub. The per-cargo limits already come from `api.res.cargoTypeRep`; only fish and crops (both 1,687,500 ms) have been seen so far.
