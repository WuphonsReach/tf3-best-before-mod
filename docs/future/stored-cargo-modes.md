# Stored cargo modes

## In short

- **What ships.** One way of judging cargo that waited in a warehouse: `corrected`. A specialized warehouse pauses a unit's spoil timer, so its plain age overstates how old it is; the mod takes the paused time (`deliveryExtensionDuration`) off the age. It is not a setting: the dropdown is gone from the in-game settings and `settings.tl`, and `storedMode` in `probe.script.tl` is fixed at `"corrected"`.
- **Why that one.** On the logged runs the corrected age removes every disagreement with the game's own good flag, and it is the fairest reading of "how old was this cargo while it was spoiling". The other modes are kept in the code only to compare against.
- **The other modes.** `formula` (plain age), `zero` and `neutral`; what each does and what it costs is below. The branches are still in `curveAdjustment` and `handleEvent` in [probe.script.tl](../../best_before_1/content/probe.script.tl), and `tools/replay_curve.py --stored` replays logged arrivals under any of them.
- **How sure we are.** The corrected mode is checked on three saves (see [findings](../findings.md)). `formula` was run live once with a changed curve and its logged deductions matched the replay to about $12; `zero` and `neutral` have only been replayed, never run in the game.
- **Unknown.** The game's exact spoil rule for stored cargo, and whether a player would ever want something other than corrected.

## The modes

A unit counts as stored when the game flags it good but its plain age is past the spoil limit (freshness below 0).

| Mode | Freshness used | Effect on stored cargo |
|---|---|---|
| `corrected` (shipped) | age minus the time the warehouse paused it | Judged as if the warehouse stay never counted. On the large flat save 132 units scored about 0.65 and earned the full bonus. |
| `formula` | plain age for every unit | Stored cargo looks long past its limit, so the curve's lowest pay applies although the game paid it normally. On the large flat save that would have cost about $5.7M of $66M base pay. |
| `zero` | plain age, but a stored unit counts as 0% fresh | Stored cargo earns the pay at 0% freshness (between normal pay and the lowest pay), not the full deduction. |
| `neutral` | plain age, but a stored unit gets no adjustment | Stored cargo keeps the game's pay, no bonus and no deduction. |

A unit the game flags as spoiled always takes the spoiled pay, in every mode.

One run with `formula` and a changed curve (150%, 60%, 30%, 10%, 20% pay) on a busy old save: 289 of 1,920 units were stored, `formula` deducted -4,636,941 and the corrected mode would have deducted only -1,059,169 on the same arrivals.

## Ideas for later

- **Bring the dropdown back.** Add a `ComboBox` param to `mod.json` (`bestBefore.stored`, values in the order corrected, formula, zero, neutral, `defaultIndex` 0), read its 1-based position in `readParamCurve` and map it with `{"corrected", "formula", "zero", "neutral"}`, falling back to corrected. A save that lacks it gets the default from the game.
- **Partial credit.** Count only part of the paused time (for example half), for a player who thinks a warehouse should preserve cargo but not for free.
- **No bonus for stored cargo.** Pay stored cargo normal pay when it is fresh by the corrected age, but never the bonus; a warehouse then cannot be used to farm the fresh-cargo window.
- **Per-cargo rules.** Some cargo could be exempt (bricks, say) while perishable cargo is not; this needs the cargo's own spoil data and a way to set it in game.

Any of these needs a game run to see how many units are stored on a normal save and what the choice costs.
