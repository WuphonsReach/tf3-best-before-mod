# How it works and where it can over-penalize

## In short

- **What it does.** When a cargo unit is delivered, the game asks scripts for a multiplier on its pay before it pays (the ticket price event, which the base game uses for the company level and for subsidies). The mod works out how fresh the unit was and answers 1 + the curve's adjustment: above 1 for fresh cargo, below 1 for slow or spoiled cargo, and 1 at the break-even point. The game pays the changed amount and shares it along the unit's chain by its own formula, so every vehicle and line that carried the unit shows the bonus or deduction at delivery: in its window, in its income chart and in the income figure that floats over it as it unloads.
- **What drives the result.** Freshness (how much of the unit's delivery limit was used, judged at delivery) and the curve settings (set in game and kept in the save). The game's own pay is the base, so there is no pay prediction to get wrong.
- **Where it can over-penalize.** A unit the game flags as spoiled takes the full penalty whatever its age. Cargo that waited in a warehouse is judged on a corrected age; if that correction were wrong, it would over-penalize (the code keeps a `formula` mode to compare, see [stored-cargo-modes.md](future/stored-cargo-modes.md)).
- **How sure we are.** One save, about seven game months (WR26A, 4,617 units): every answer matched the unit's freshness, the player's income matched the base pay times the answers plus passenger fares to 0.1%, every tracked line's income moved by the average answer of the units it carried (boats and trucks of two-leg chains alike), and the grain train's window showed $827,966 for a trip worth $3,043,520 in full ([line-billing](future/line-billing.md)).
- **Fallback.** With `billing = "bookings"` in `settings.tl` the game pays in full, and the mod books a correcting entry to the player's account only, worked out from a prediction of the pay (below). The vehicle and line windows then show the full pay.
- **Side effect to know.** With the default -100% penalty a spoiled unit pays nothing, and a save that spoils a lot can run its account down. By design the mod does not soften this for a low balance; see [future/revisit-later.md](future/revisit-later.md).
- **Removing the mod.** A save loaded without the mod drops the mod's game script and its event subscription, so the billing leaves nothing behind. A shown Stale Cargo warning does, see [removing-the-mod.md](removing-the-mod.md).
- **Unknown.** How the mod's answer combines with a subsidy's x2 (the game multiplies the answers, so most likely the product).

## The steps

1. A unit arrives. Before paying, the game raises the ticket price event naming it; the mod reads the unit's pickup time and its warehouse pause. The unit's *delivery limit* is the game's adjusted delivery time for its cargo (`api.engine.util.stock.getAdjustedDeliveryTime`, the limit the vehicles' cargo bar runs against). It shrinks as the game years pass: 1.5 x the cargo file's delivery time in 1900, falling 0.00625 a year to 0.75 x in 2020, and 0.75 x from then on ([findings](findings.md)). If that call fails, the mod falls back to 1.5 x. Freshness is `1 - age / limit`, where age is the time since pickup (for stored cargo, minus the paused time). 1 is just picked up, 0 is at the limit, below 0 is past it.
2. The curve turns freshness into a share of the unit's pay: `+bonusPercent` while at or above `bonusDownToFreshness`, a straight line down to 0 at `breakevenFreshness`, a straight line on to `penaltyPercent` at `penaltyBelowFreshness`, and `penaltyPercent` below that and for spoiled units. The five in-game settings behind these names are described in [changing-settings.md](changing-settings.md).
3. The mod answers `1 + share` for the unit (never below 0). The game multiplies it with any other answers (the company level's, a subsidy's), pays the unit, and shares the pay along its chain.
4. The arrival event follows at the same clock time. There the mod counts the unit for the Stale Cargo warning and, at `logLevel` `curve` or `full`, logs the unit with an estimate of the adjustment in money from a prediction of its pay (price x distance x the Cargo Income setting x the company's ticket price multiplier); the monthly summary line adds those estimates up.

With `billing = "bookings"` steps 3 and 4 differ: the game pays in full, and the arrival handler turns the share into money with the predicted pay (rounded, a deduction capped at 100% of the prediction, nothing below 1 money), queues it, and the game script's `update` books the sum per carrier to the player's account.

The curve comes from the mod's in-game settings: seven settings in `mod.json` (five for the pay curve, the stale threshold, and the switch for the Stale Cargo warnings) that the game shows under Mods, in New Game and in Load Game, stores in the save and hands to the game script as list positions (1-based; the `numbers` field is not passed, so the script turns positions into values itself). The game script reads them again on each load, so a player can retune a save by changing them in Load Game before loading. A save with no in-game settings (from before they existed) gets the settings' defaults from the game, in the dialog and in the script, so it plays on the default curve until its player sets one; `settings.tl`'s curve is only a fallback for when the game hands over no settings at all. The log shows the source in `BEST_BEFORE curveSettings source=params|settings.tl ...`, written when the source or the numbers change. `logLevel` is not an in-game setting and comes from the file. Checked in the game with probe settings (positions, 5% steps, edit on load, and the dialog showing the save's own values) and with the real five settings on new games (defaults, out-of-order and in-order values) and on one old save without settings.

Ranges the mod enforces: bonus 0 to +200% (a unit can pay 3x in the full bonus window), penalty 0 to -100%, freshness points in the order 1 >= bonusDown >= breakeven >= penaltyBelow >= 0. Values outside are clamped. The in-game sliders cannot leave their ranges; when the freshness points are out of order the mod lowers the later ones and the `curveSettings` line says `adjusted=yes` (at any log level but `off`). A range clamp of the `settings.tl` fallback curve is not logged.

## Where it can over-penalize

- **Spoiled units.** The game's own "good" flag decides what is spoiled. A flagged unit always takes `penaltyPercent`, even if its computed freshness looks fine. For cargo that did not wait in a warehouse the flag flipped at the delivery limit on every save where units spoiled ([findings](findings.md)).
- **Stored cargo.** A specialized warehouse pauses a unit's spoil timer, so its plain age overstates how old it is. The mod takes the paused time (`deliveryExtensionDuration`) off the age (the `corrected` mode, the only one offered). On the large flat save, 132 units that went rail to warehouse to road had a plain freshness near -0.45 but the game flagged them good, and corrected they scored about 0.65 and earned the full bonus. Judged on plain age they would have lost about $5.7M of $66M base pay. The other modes (`formula`, `zero`, `neutral`) are kept in the code to compare, see [stored-cargo-modes.md](future/stored-cargo-modes.md).

## Where it can miss

- **An error in the answer.** The answer is worked out under `pcall`; if it fails, the unit is paid in full and the log says `BEST_BEFORE ticketPrice error=`. None has been seen.
- **Passengers.** Passenger income is not part of the mod at all, only cargo.

## With billing "bookings"

- **Prediction error.** The mod does not read the pay the game gave; it rebuilds it. That is good to about 1% on average, but a single unit can differ more (derived pay over predicted pay ran from 0.92 to 1.21 across vehicles, their share of a chain's pay). With a -100% penalty the deduction equals the predicted pay, so a prediction a little too high leaves that unit a hair negative.
- **Where the entry goes.** The adjustment is booked to the player only. The game's per-vehicle and per-line balances still show the full pay, so they overstate a vehicle's earnings when a deduction applies.
- **Missing entities and small units.** A unit whose source or target building cannot be found (sold or rebuilt in transit) gets no entry, and adjustments below 1 money are not booked.
- **Pay beyond the prediction.** Pay the game gives beyond the prediction is not adjusted. Player income ran above the prediction on some saves; on WR26A passenger fares explain it ([findings](findings.md)).

## Evidence

- Ticket billing, WR26A (Hard, Dec 1917 to Jul 1918), save curve +50%/0%: 4,617 units, every answer equal to the unit's rate, player income 1.001 of base pay x answers plus passenger fares, line ledgers moved by their units' average answer; details in [future/line-billing.md](future/line-billing.md).
- Runs with the bookings (the only billing before 1.2):
  - QZZZ, +30%/-100% curve: 7,921 units, 2,850 spoiled, each deducted its whole predicted pay (ratio 0.99988 to 1.00009), none beyond rounding; the player ratio is 1.575 there because that save has income the prediction does not cover, so it says nothing about the margin.
  - Flat large save, rank 1, Inflation High, +50%/-95% curve: 1,572 units, all sent, derived/predicted pay 1.001 at player level, 99% of booked entries landed as exact steps of the balance.
  - Second flat save (potential level 2): 1.001 over 2,289 units, see [findings.md](findings.md).
- Curve replays across the saved runs: [future/revisit-later.md](future/revisit-later.md).
