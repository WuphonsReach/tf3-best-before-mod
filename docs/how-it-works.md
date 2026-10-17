# How it works and where it can over-penalize

## In short

- **What it does.** The game pays every delivered cargo unit in full. The mod then works out how fresh the unit was and books one correcting entry to the player's account: a bonus for fresh cargo, a deduction for slow or spoiled cargo, nothing at the break-even point. The mod never changes the game's own pay.
- **What drives the result.** Freshness (how much of the unit's delivery time limit was used), the five curve settings in `settings.tl`, and the mod's prediction of what the game paid for that unit (price x distance x the Cargo Income setting x the company's ticket price multiplier).
- **Where it can over-penalize.** Three places, all small or rare. The prediction is only good to about 1% per unit, so a full (-100%) deduction can take a hair more than the unit paid. A unit flagged spoiled by the game takes the full penalty whatever its age. Cargo that waited in a warehouse is judged on a corrected age, and if that correction were wrong it would over-penalize (the settings keep a `formula` mode to compare).
- **Where it under-penalizes instead.** A unit whose source or target building cannot be found (sold or rebuilt in transit) gets no entry. Pay the game gives beyond the prediction is not adjusted.
- **How sure we are.** The prediction matched the ledger at 1.001 (player level) on the rank 1, High Inflation flat save, and 0.99 to 1.00 on earlier saves, with individual vehicles between 0.92 and 1.21. Bonuses and deductions land in the account as booked. A -100% deduction has been run in the game (QZZZ, 2,850 spoiled units, each deducted 99.99% to 100.01% of its predicted pay).
- **Side effect to know.** With the default -100% penalty a save that spoils a lot can drive the account negative (QZZZ went to -$7.9M in one run). The mod does not cap deductions at the balance; see [future/revisit-later.md](future/revisit-later.md).
- **Unknown.** How the game splits the pay of a transferred unit along its chain (the mod books to the player, not to vehicles or lines), where the roughly 1.1x of income above the prediction in the control runs comes from, and whether the 1% prediction error is random or biased.

## The steps

1. The game pays a unit when it arrives, in full, using the income function. A mod cannot see freshness at that point, so the pay stays as it is.
2. The mod receives the arrival event, which carries the unit's pickup time and its delivery time limit. Freshness is `1 - age / (limit x 1.5)`, where age is the time since pickup. 1 is just picked up, 0 is at the limit, below 0 is past it.
3. The curve turns freshness into a share of the unit's pay: `+bonusPercent` while at or above `bonusDownToFreshness`, a straight line down to 0 at `breakevenFreshness`, a straight line on to `penaltyPercent` at `penaltyBelowFreshness`, and `penaltyPercent` below that and for spoiled units. The settings are described in [settings.tl](../best_before_1/content/settings.tl).
4. The mod predicts the unit's pay from the construction positions of its source and target, scaled by the Cargo Income setting and the company's ticket price multiplier, both read at run time. At rank 1 the multiplier does not exist and the mod uses 1.0.
5. The adjustment is the curve share times the predicted pay, rounded to whole money. A deduction is capped at 100% of the predicted pay. The mod queues it and the game script's `update` books the sum for the player's account.

Ranges the mod enforces: bonus 0 to +200% (a unit can pay 3x in the full bonus window), penalty 0 to -100%, freshness points in the order 1 >= bonusDown >= breakeven >= penaltyBelow >= 0. Values outside are clamped and logged.

## Where it can over-penalize

- **Prediction error.** The mod does not read the pay the game gave; it rebuilds it. That is good to about 1% on average, but a single unit can differ more (derived pay over predicted pay ran from 0.92 to 1.21 across vehicles; the likely reason is that a chain's pay is shared among its vehicles by a formula we do not know, which we have not confirmed). With a -100% penalty the deduction equals the predicted pay, so a prediction a little too high leaves that unit a hair negative. Earlier defaults used -95% and kept 5% of margin; the cap was raised to 100% on purpose, and the effect is small.
- **Spoiled units.** The game's own "good" flag decides what is spoiled. A flagged unit always takes `penaltyPercent`, even if its computed freshness looks fine. We have not checked whether the flag and the computed age ever disagree for cargo that did not wait in a warehouse.
- **Stored cargo.** A specialized warehouse pauses a unit's spoil timer, so its plain age overstates how old it is. With `stored = "corrected"` the mod takes the paused time (`deliveryExtensionDuration`) off the age. On the large flat save, 132 units that went rail to warehouse to road had a plain freshness near -0.45 but the game flagged them good, and corrected they scored about 0.65 and earned the full bonus. Judged on plain age they would have lost about $5.7M of $66M base pay. Other `stored` modes (`formula`, `zero`, `neutral`) exist to compare.
- **Missing entities.** The mod guards every lookup. If a vehicle, line or building is gone, the unit is skipped for the lookup it needs; this loses an adjustment (under-penalizes), it does not add one.
- **Where the entry goes.** The deduction is booked to the player only, not split along the unit's chain. The game's per-vehicle and per-line balances still show the full pay, so they overstate a vehicle's earnings when a deduction applies, and the player's balance is the one to trust.

## Where it under-penalizes or misses

- Pay the game gives beyond the prediction is not adjusted. Player income ran about 1.1x over the prediction in the control runs; the cause is unknown (passenger income is not logged), and it is not the pay scale.
- Units below 1 money are not booked.
- Passenger income is not part of the mod at all, only cargo.

## Evidence

- QZZZ, +30%/-100% curve: 7,921 units, 2,850 spoiled, each deducted its whole predicted pay (ratio 0.99988 to 1.00009), none beyond rounding; the player ratio is 1.575 there because that save has income the prediction does not cover, so it says nothing about the margin.
- Flat large save, rank 1, Inflation High, +50%/-95% curve: 1,572 units, all sent, derived/predicted pay 1.001 at player level (1.441 without the deductions), 99% of booked entries landed as exact steps of the balance.
- Earlier saves (rank 3 to 13): 0.99 to 1.00 once the mod read the Cargo Income setting and the ticket price multiplier at run time, see [findings.md](findings.md).
- Curve replays across the saved runs: [future/revisit-later.md](future/revisit-later.md).
