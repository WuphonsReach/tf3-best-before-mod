# How it works and where it can over-penalize

## In short

- **What it does.** The game pays every delivered cargo unit in full. The mod then works out how fresh the unit was and books one correcting entry to the player's account: a bonus for fresh cargo, a deduction for slow or spoiled cargo, nothing at the break-even point. The mod never changes the game's own pay.
- **What drives the result.** Freshness (how much of the unit's spoil limit was used), the five curve settings (copied from `settings.tl` into a save the first time the mod runs on it, then kept by the save), and the mod's prediction of what the game paid for that unit (price x distance x the Cargo Income setting x the company's ticket price multiplier).
- **Where it can over-penalize.** Three places, all small or rare. The prediction is only good to about 1% per unit, so a full (-100%) deduction can take a hair more than the unit paid. A unit flagged spoiled by the game takes the full penalty whatever its age. Cargo that waited in a warehouse is judged on a corrected age, and if that correction were wrong it would over-penalize (the settings keep a `formula` mode to compare).
- **Where it under-penalizes instead.** A unit whose source or target building cannot be found (sold or rebuilt in transit) gets no entry. Units paying less than 1 money get no entry. Pay the game gives beyond the prediction is not adjusted.
- **How sure we are.** The prediction matches the player's ledger at 1.001 on both rank 1 flat saves, and individual vehicles range between 0.92 and 1.21 (their share of a chain's pay). Bonuses and deductions land in the account as booked. A -100% deduction has been run in the game (QZZZ, 2,850 spoiled units, each deducted 99.99% to 100.01% of its predicted pay).
- **Side effect to know.** With the default -100% penalty a save that spoils a lot can drive the account negative (QZZZ went to -$7.9M in one run). By design the mod does not cap deductions at the balance (a spoiled unit pays nothing, and a rounding-sized fine is accepted); see [future/revisit-later.md](future/revisit-later.md).
- **Unknown.** How the game splits the pay of a transferred unit along its chain (the mod books to the player, not to vehicles or lines), why player income exceeds the prediction on some saves, and whether the 1% prediction error is random or biased.

## The steps

1. The game pays a unit when it arrives, in full, using the income function. A mod cannot see freshness at that point, so the pay stays as it is.
2. The mod receives the arrival event, which carries the unit's pickup time. The unit's *spoil limit* is 1.5 x its cargo's delivery time. Freshness is `1 - age / spoil limit`, where age is the time since pickup (for stored cargo, minus the paused time). 1 is just picked up, 0 is at the spoil limit, below 0 is past it.
3. The curve turns freshness into a share of the unit's pay: `+bonusPercent` while at or above `bonusDownToFreshness`, a straight line down to 0 at `breakevenFreshness`, a straight line on to `penaltyPercent` at `penaltyBelowFreshness`, and `penaltyPercent` below that and for spoiled units. The settings are described in [settings.tl](../best_before_1/content/settings.tl).
4. The mod predicts the unit's pay from the construction positions of its source and target, scaled by the Cargo Income setting and the company's ticket price multiplier, both read at run time. At rank 1 the multiplier does not exist and the mod uses 1.0.
5. The adjustment is the curve share times the predicted pay, rounded to whole money. A deduction is capped at 100% of the predicted pay. The mod queues it and the game script's `update` books the sum per carrier for the player's account.

The curve settings and `stored` are sticky: the first time the game script runs on a save it copies them from `settings.tl` into the game script state, which the game writes into the save, and from then on it reads that copy. Editing `settings.tl` afterwards does not change that save; a new game, or a save the mod has not run on, takes the file's current values. The log shows it as `BEST_BEFORE curveSettings source=settings.tl saved=yes ...` when a save is stamped and `source=save saved=kept ...` (with the file's values after `settingsTl:`) when the file disagrees with the saved copy. Both lines are written when the state changes, so a reload with nothing different logs nothing; `logLevel` is not saved and still comes from the file at every start. Checked: a save written right after loading (`test-1017-large-flat-1x5 1017-1424 immediate save`) holds the curve in the `best_before_1` / `probe.gs` state (read with `tf3save._lua_pairs` from the [tf3-save-format](https://github.com/WuphonsReach/tf3-save-format/tree/00c4039160d26f4fd15df0fdaf9466e67c737f7d/tools) tools). Reading it back on load (`source=save saved=kept` after a `settings.tl` edit) is not yet tested.

Ranges the mod enforces: bonus 0 to +200% (a unit can pay 3x in the full bonus window), penalty 0 to -100%, freshness points in the order 1 >= bonusDown >= breakeven >= penaltyBelow >= 0. Values outside are clamped; a value outside its own range is also logged (the order is clamped silently).

## Where it can over-penalize

- **Prediction error.** The mod does not read the pay the game gave; it rebuilds it. That is good to about 1% on average, but a single unit can differ more (derived pay over predicted pay ran from 0.92 to 1.21 across vehicles; the likely reason is that a chain's pay is shared among its vehicles by a formula we do not know, which we have not confirmed). With a -100% penalty the deduction equals the predicted pay, so a prediction a little too high leaves that unit a hair negative. The effect is small.
- **Spoiled units.** The game's own "good" flag decides what is spoiled. A flagged unit always takes `penaltyPercent`, even if its computed freshness looks fine. For cargo that did not wait in a warehouse the flag and the formula agreed on all 82 units checked on the small save; for the other saves the check has not been made unit by unit.
- **Stored cargo.** A specialized warehouse pauses a unit's spoil timer, so its plain age overstates how old it is. With `stored = "corrected"` the mod takes the paused time (`deliveryExtensionDuration`) off the age. On the large flat save, 132 units that went rail to warehouse to road had a plain freshness near -0.45 but the game flagged them good, and corrected they scored about 0.65 and earned the full bonus. Judged on plain age they would have lost about $5.7M of $66M base pay. Other `stored` modes (`formula`, `zero`, `neutral`) exist to compare.
- **Where the entry goes.** The adjustment is booked to the player only, not split along the unit's chain. The game's per-vehicle and per-line balances still show the full pay, so they overstate a vehicle's earnings when a deduction applies, and the player's balance is the one to trust.

## Where it under-penalizes or misses

- **Missing entities.** The mod guards every lookup. If a vehicle, line or building is gone, the unit is skipped for the lookup it needs; this loses an adjustment, it does not add one.
- **Pay beyond the prediction.** Pay the game gives beyond the prediction is not adjusted. Player income ran above the prediction on some saves (see [findings](findings.md)); the cause is unknown (passenger income is not logged).
- **Small units.** Adjustments below 1 money are not booked.
- **Passengers.** Passenger income is not part of the mod at all, only cargo.

## Evidence

- QZZZ, +30%/-100% curve: 7,921 units, 2,850 spoiled, each deducted its whole predicted pay (ratio 0.99988 to 1.00009), none beyond rounding; the player ratio is 1.575 there because that save has income the prediction does not cover, so it says nothing about the margin.
- Flat large save, rank 1, Inflation High, +50%/-95% curve: 1,572 units, all sent, derived/predicted pay 1.001 at player level, 99% of booked entries landed as exact steps of the balance.
- Second flat save (potential level 2): 1.001 over 2,289 units, see [findings.md](findings.md).
- Curve replays across the saved runs: [future/revisit-later.md](future/revisit-later.md).
