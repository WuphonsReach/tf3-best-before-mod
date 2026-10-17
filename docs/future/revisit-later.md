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
- **Defaults.** Current: +20% bonus down to 40% freshness (60% of the limit used), break-even at 20% freshness (80% used), -100% penalty at 0% fresh and below. Replayed over nine primary runs (1.06 billion base pay) it nets +8.0% pooled (+5.8% without the 333 save, which is 43% of the pay); per run from -30.0% (QZZZ, 36% of units spoiled) to +19.1% (the flat saves, almost nothing spoils). No single default nets zero: the bonus that does is 0% to 8% on saves that rarely spoil and 34% to 71% on saves that spoil a lot; pooled it is 11%. Most cargo is either very fresh or spoiled, so the two fade points barely matter (about 2 points pooled across their whole range); the bonus size sets the baseline and the penalty size decides how hard a badly run save is hit. Earlier candidates: +50% / -95% netted +33.0% pooled, +30% / -100% netted +16.8%. Open: whether to aim at roughly zero (about +11% bonus at -100%) or reward good logistics (the current ones). Settle with more saves, ideally one with Cargo Income at 150% and a rank 13 save.
- **Bonus.** Positive bookings are verified (see [findings](../findings.md)). The bonus creates money the base game never pays, so the default stays a deliberate choice, not a side effect; the settings allow up to +200%.
- **Full-pay deductions.** The penalty allows -100% and the deduction cap is 100% of the predicted pay. Checked in the game on the QZZZ save: all 2,850 spoiled units were deducted 99.99% to 100.01% of their predicted pay, none beyond rounding. The prediction is good to about 1%, so a unit can still end a hair negative in the ledger when the prediction is a little high.

## The account can go negative
- **Decided: no cap.** The mod never holds back a deduction because the account is low. Its purpose is to penalize delivering spoiled cargo: the player is paid nothing for a spoiled unit, and a prediction a hair too high can leave a unit a small fine (rounding-sized). A deduction that depended on the balance would also make pay depend on when a unit arrives.
- **What happened.** On the QZZZ save with the +30% / -100% defaults the account fell from $54.7M to -$7.9M in one run (low point -$8.4M). The earlier QZZZ run at +50% / -95% never went below $26.6M; the larger deductions (-$26.1M net of bonuses against -$10.5M) are the difference, on top of $205.7M of running costs. The game showed no error and the run continued.
- **Still unknown.** What the game does with a negative account over a longer time (loans, bankruptcy, vehicle sales). Only worth a longer run or a read of the game's bankruptcy rules if it turns out to matter for players.

## Housekeeping
- **The income-function logging stub** in `mod.script.tl` replaces `cargoIncomeScript`, which only one mod can do. Keep it while the logging is useful; remove it before a release.
- **The landing check in the verifier** is a rate of exact steps (about 0.6 to 0.96) because deductions can share a step with pay. A controlled save with one flow would allow an exact check.
