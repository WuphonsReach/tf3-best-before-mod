# Revisit once more is known

Questions and options that depend on something we have not learned yet. Each says what would settle it.

## Pay and ledgers
- **How the pay of a delivered unit is split along its chain.** Parked: not needed for the curve, which books to the player only. Settle with a small controlled save: one flow on a single leg, then two legs (one long, one short), then an intermediate industry. The log already names every vehicle, line and carrier of a unit's chain and the balance of each, so the shares can be read per delivery. If the formula is found, per-vehicle and per-line deductions could come back as an option (see [discarded](discarded.md)).
- **Which carrier a deduction is booked under.** Today the last leg's carrier. The game seems to book one entry per carrier ([one delivery in the save-format notes](https://github.com/WuphonsReach/tf3-save-format/blob/00c4039160d26f4fd15df0fdaf9466e67c737f7d/docs/finances.md) split 82% water), so a split of the deduction by carrier may match the Finances tab better.
- **Why a unit's predicted pay is off by a steady factor per cargo type** on the large save (0.8 to 0.86 for several, 0.59 and 0.10 for others). The price functions are ruled out: all eleven cargo types seen use the same `constantFn` parameters (see [findings](../findings.md)). The likely cause is the split along the chain, which is parked for now (see the first item); the log records each unit's chain if it is picked up again.
- **About 14% more player income than the arrivals predict** (1.36 on the large save). Possibly chain pay we do not see per unit.

## Freshness
- **Stored cargo.** The `stored = "corrected"` setting takes `deliveryExtensionDuration` off a unit's age, which removes every disagreement with the game's good flag on the logged runs (see [findings](../findings.md)). Open: the exact spoil rule for paused cargo (spoiled units start at about 0.845 of the limit on the corrected age, not at 1.0), and runs of several game years to see how much stored cargo there is.
- **Air.** No unit on an air line has been deducted yet (the test cargo plane delivered at 0.72 to 0.78 freshness). Needs a run with air cargo that arrives late.
- **Limits per cargo.** Eleven cargo types have been seen with limits from 1,687,500 ms to 6,750,000 ms; check that the 1.5 x delivery time rule holds for all of them, not only fish and vegetables.

## The curve and its defaults
- **Shape.** Five settings with straight lines between them: bonus at 100% freshness, where the bonus starts to fall, break-even, where the penalty is at its maximum, and the penalty at 0% and when spoiled. A smooth curve could be added later as an option without changing the five settings.
- **Defaults.** Aim for roughly no net change across a large save. On the first 254 logged deliveries a +50% bonus, break-even at 30% and a 95% maximum penalty came out at -6% of base pay; a more realistic default may move the break-even to 40 or 50% and needs a larger bonus or a gentler penalty to stay level. Tune by replaying logged deliveries across several saves (a small replay script in `tools/` would help).
- **Bonus.** Positive bookings have never been sent. The bonus creates money the base game never pays, so it needs a conservative default and a test that books only bonuses.
- **Why the penalty went to 100%.** The prediction is within about 1%, so a 95% maximum penalty left 5% of the pay as margin and a deduction could not turn a unit negative. The current defaults and the deduction cap allow -100% (the mod clamps at 100% of the predicted pay), so a prediction a little too high can leave a unit a hair negative. Not yet tested in the game with a full-pay deduction.

## Housekeeping
- **The income-function logging stub** in `mod.script.tl` replaces `cargoIncomeScript`, which only one mod can do. Keep it while the logging is useful; remove it before a release.
- **The landing check in the verifier** is a rate of exact steps (about 0.6 to 0.96) because deductions can share a step with pay. A controlled save with one flow would allow an exact check.
