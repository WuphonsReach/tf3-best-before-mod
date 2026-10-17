# Revisit once more is known

## In short

- **Open questions.** How the game splits a transferred unit's pay along its chain (parked, the curve does not need it); why player income exceeds the prediction on some saves; the exact spoil rule for stored cargo; and what a negative account does over a longer time.
- **Open choices.** The curve defaults (+20% bonus, break-even at 80% of the spoil limit used, -100% penalty) net +8.0% pooled over nine runs; whether to aim at about zero or reward good logistics waits on more saves. In-game settings for the curve are planned through `mod.json` and untested.
- **Settled.** Deductions are never capped at the account balance.

Each item says what would settle it.

## Pay and ledgers
- **How the pay of a delivered unit is split along its chain.** Parked: not needed for the curve, which books to the player only. Settle with a small controlled save: one flow on a single leg, then two legs (one long, one short), then an intermediate industry. The log already names every vehicle, line and carrier of a unit's chain and the balance of each, so the shares can be read per delivery. If the formula is found, per-vehicle and per-line deductions could come back as an option (see [discarded](discarded.md)).
- **Which carrier a deduction is booked under.** Today the last leg's carrier. The game seems to book one entry per carrier ([one delivery in the save-format notes](https://github.com/WuphonsReach/tf3-save-format/blob/00c4039160d26f4fd15df0fdaf9466e67c737f7d/docs/finances.md) split 82% water), so a split of the deduction by carrier may match the Finances tab better.
- **Why a unit's predicted pay is off by a steady factor per cargo type** on the large save (0.8 to 0.86 for several, 0.59 for another). The price functions are ruled out: all eleven cargo types seen use the same `constantFn` parameters (see [findings](../findings.md)). The likely cause is the split along the chain, which is parked (see the first item); the log records each unit's chain if it is picked up again.
- **Why player income exceeds the prediction on some saves** (1.145 on the small save without the mod, 1.575 on QZZZ; the two flat saves match at 1.001). Passenger income is not logged, so a run that logs it would show whether that is the gap.

## Freshness
- **Stored cargo.** The `stored = "corrected"` setting takes `deliveryExtensionDuration` off a unit's age, which removes every disagreement with the game's good flag on the logged runs (see [findings](../findings.md)). Open: the exact spoil rule for paused cargo (spoiled units start at about 0.845 of the limit on the corrected age, not at 1.0), and runs of several game years to see how much stored cargo there is.
- **Limits per cargo.** Eleven cargo types have been seen with limits from 1,687,500 ms to 6,750,000 ms; the 1.5 x delivery time rule is confirmed against the game's flag for fish and vegetables only. Check that it holds for the other types, ideally on a run without warehouses.

## The curve and its defaults
- **Shape.** Five settings with straight lines between them: bonus at 100% freshness, where the bonus starts to fall, break-even, where the penalty is at its maximum, and the penalty at 0% and when spoiled. A smooth curve could be added later as an option without changing the five settings.
- **Defaults.** Current: +20% bonus down to 40% freshness (60% of the limit used), break-even at 20% freshness (80% used), -100% penalty at 0% fresh and below. Replayed over nine primary runs (1.06 billion base pay) it nets +8.0% pooled (+5.8% without the 333 save, which is 43% of the pay); per run from -30.0% (QZZZ, 36% of units spoiled) to +19.1% (the flat saves, almost nothing spoils). The same runs net +16.8% at +30% / -100% and +34.9% at +50% / -95%. No single default nets zero: the bonus that does is 0% to 8% on saves that rarely spoil and 34% to 71% on saves that spoil a lot; pooled it is 11%. Most cargo is either very fresh or spoiled, so the two fade points barely matter (about 2 points pooled across their whole range); the bonus size sets the baseline and the penalty size decides how hard a badly run save is hit. Open: whether to aim at roughly zero (about +11% bonus at -100%) or reward good logistics (the current ones). Settle with more saves, ideally one with Cargo Income at 150% and a rank 13 save.
- **Bonus.** Positive bookings are verified (see [findings](../findings.md)). The bonus creates money the base game never pays, so the default stays a deliberate choice, not a side effect; the settings allow up to +200%.
- **Full-pay deductions.** The penalty allows -100% and the deduction cap is 100% of the predicted pay. All 2,850 spoiled units on the QZZZ save were deducted 99.99% to 100.01% of their predicted pay, none beyond rounding. The prediction is good to about 1%, so a unit can still end a hair negative in the ledger when the prediction is a little high.
- **In-game settings for the curve.** The five settings are meant to be changeable in the game's mod settings (`mod.json` `params` and `options`, which `mod.json` leaves empty and the mod does not yet read). If the settings reach the script only at load, changing them needs a reload. Settle with a probe that reads `params` and logs them.

## The account can go negative
- **Decided: no cap.** The mod never holds back a deduction because the account is low. Its purpose is to penalize delivering spoiled cargo: the player is paid nothing for a spoiled unit, and a prediction a hair too high can leave a unit a small fine (rounding-sized). A deduction that depended on the balance would also make pay depend on when a unit arrives.
- **What happened.** On the QZZZ save with the +30% / -100% curve the account fell from $54.7M to -$7.9M in one run (low point -$8.4M): -$26.1M of net adjustments on top of $205.7M of running costs. The game showed no error and the run continued.
- **Still unknown.** What the game does with a negative account over a longer time (loans, bankruptcy, vehicle sales). Only worth a longer run or a read of the game's bankruptcy rules if it turns out to matter for players.

## Housekeeping
- **The CPU cost of the log levels** is unmeasured. Plan: the same save and the same game-time stretch at `off`, `summary`, `curve` and `full`, each at least twice, with `tools/cpu_sample.py` running; compare the simulation threads' CPU seconds per game month. If the levels differ by less than two runs of one level do, the cost does not matter.
- **The income-function logging stub** in `mod.script.tl` replaces `cargoIncomeScript`, which only one mod can do. Keep it while the logging is useful; remove it before a release.
- **The landing check in the verifier** is a rate of exact steps (about 0.6 to 0.96) because deductions can share a step with pay. A controlled save with one flow would allow an exact check.
