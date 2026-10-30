# Changing the mod's settings

## In short

- **Where.** The curve is set in game, in the mod's own settings dialog: the **Mods** tab, then the gear next to the mod. It is there in both **New Game** and **Load Game**. It is not under Gameplay Settings, which only holds the base game's settings.
- **How it works.** The game stores each setting in the save, shows the save's own values when you open the dialog, and hands the values to the mod when the save loads. Change a value before pressing **Load Game** and the mod uses it from that load on; the next save you make keeps it. A player can retune a save as often as they like.
- **How sure we are.** The route and the behaviour (the dialog shows the save's values, a change made before loading reaches the mod and is saved) were checked in the game on new games and on an old save. The five settings were run at the defaults and at three non-default sets, and for every setting that was not clamped, the dialog, the saved header and the value the mod logged agreed. A long run on an old save with a changed curve (1,920 deliveries, with the bookings, before 1.2) passed `verify_run.py`, and replaying the arrivals with those numbers reproduced the logged deductions (-4,636,930 against -4,636,941) and bonuses (+10,889,581 against +10,889,569).
- **Old saves.** A save from before the settings existed shows the defaults in the dialog and loads on the default curve, whatever curve it used before; the next save you make stores them. Set the values you want before pressing Load Game.
- **A mod added to an old save.** Activating the mod on a save that never had it (Load Game, Mods tab) shows the defaults in the dialog; values set there before pressing Load Game reach the game: `preRunFn` logged them as `loadParams` (list positions 14/12/8/4/6), the probe's `curveSettings` agreed (165% / 55% / 35% / 15% / 25%), and both saves made afterwards hold them (checked once).
- **Saves with the old warehouse setting.** Saves made while the mod still had a setting for warehouse cargo load fine: the dialog shows the sliders at the values the save holds, the mod ignores the extra key, and the next save leaves it out (checked on two such saves). Warehouse cargo is always judged by its corrected age.
- **Stale threshold.** A sixth setting, "Warn on cargo below freshness percent" (0% to 25%, default 10%), sets only when a delivered unit counts as stale for the Stale Cargo warning ([stale-line-warnings.md](stale-line-warnings.md)); it does not change pay. It came with 1.2 and was checked in the game on one save: the dialog shows it, a change made before Load Game reaches the mod and is saved, and the logged value agrees (see the test at the end). A save from before it shows the default and stores it at the next save.
- **Warnings switch.** A seventh setting, the check box "Show Stale Cargo warnings" (on by default), turns the Stale Cargo warnings off: the warnings shown are taken down and each line's history is forgotten, so ticking it again starts the count fresh. It is the way to clear the warnings before removing the mod from a save ([removing-the-mod.md](removing-the-mod.md)). It came with 1.2 and was checked once in the game: a save from before it shows the box ticked, and, unticked on Load Game, it reached the mod and took the warning down.
- **Non-perishable cargo.** An eighth and a ninth setting, "Non-perishable cargo" (a list: Full bonus, Half bonus, No bonus, No effect) and "Non-perishable delivery time" (15 to 75 min), choose how cargo with a long base delivery time is paid. They come with 1.3. Checked in the game on two old saves (1900 and 1974), each mode and the 25, 30 and 40 min cutoffs, about 8,000 units (see the tests at the end): the dialog showed the defaults, the game handed the list to the mod as its 1-based position like a slider and stored that position in the save, and every unit was paid as its class and mode say. No bonus held fresh non-perishable cargo at normal pay and still cut late logs below it; No effect left non-perishable cargo, late logs included, to the game; moving the cutoff from 25 to 40 min put fuel (37.5 min) back on the curve. Half bonus was added after those tests and checked on both saves: on the 1900 save every fresh non-perishable unit was paid half the bonus; on the 1974 save, replayed from the same start as the Full bonus run, 217 late logs and fuel units were cut below normal pay, and every unit both runs delivered at the same freshness was paid the same below normal pay and half the extra above it (see the tests at the end). The dialog shows no tooltips for mod settings, so the settings are explained in the mod description.
- **Unknown.** Whether backing out of the dialog without pressing Load Game leaves the save untouched (not tried).

## On a new game

1. On the New Game screen, open the **Mods** tab.

   ![The tabs on the New Game screen](images/new-game-tabs.png)

2. Find the mod's card. The mod has to be active (its button reads **Activated**; the other mods' buttons read **Activate**). Click the gear to its right.

   ![The Activated button and gear on a mod's card](images/mod-card-gear.png)

3. The dialog lists the mod's settings under **Settings**. Set the sliders, then close the dialog with the X at its top right. The dialog opens with the values of the last new game you set up, not the defaults, because the game keeps the New Game screen's choices in its `settings.lua` in your user folder. Check them before you start.

   ![The mod's settings at their defaults (taken before the stale threshold slider was added, so that sixth slider is missing)](images/mod-settings-dialog.png)

4. Start the game as usual.

## On a saved game

1. Open **Load Game**, from the main menu or from the Esc menu inside a running game.
2. On the save's card, click the gear (it is the **Details** button, next to **Load Game**).

   ![Load Game and the gear on a save's card](images/load-game-save-buttons.png)

3. Open the **Mods** tab.

   ![The tabs on a save's details page](images/load-game-tabs.png)

4. Click the gear on the mod's card, as in step 2 above. The settings show the values this save holds. Change what you want and close the dialog with the X.
5. Press **Load Game** at the bottom right of the details page. The mod uses the new values from this load, and the next save you make stores them.

## What the settings do

Pay is shown as a share of normal pay, so 100% is the pay the game gives and 150% is a 50% bonus. Freshness is 100% when cargo is picked up and falls to 0% at its delivery limit. Every percent slider moves in 5% steps. The curve is drawn out in [how-it-works.md](how-it-works.md).

| Setting | Range | Default | Meaning |
|---|---|---|---|
| Bonus pay multiplier for fresh cargo | 100% to 200% | 120% | Pay for cargo delivered at full freshness. 100% means no bonus. |
| Get full bonus down to freshness percent | 0% to 100% | 40% | The fresh-cargo pay holds while freshness is at or above this, then falls in a straight line. |
| Normal pay at freshness percent | 0% to 100% | 20% | Cargo delivered at exactly this freshness earns normal pay. |
| Lowest pay below freshness percent | 0% to 100% | 0% | At or below this freshness the spoiled pay applies. |
| Pay multiplier for spoiled cargo | 0% to 100% | 0% | The lowest pay: 0% takes the whole pay of a unit. Also used for cargo the game marks as spoiled. |
| Warn on cargo below freshness percent | 0% to 25% | 10% | Only the Stale Cargo warning ([stale-line-warnings.md](stale-line-warnings.md)): a delivered unit below this freshness, or spoiled, counts as stale. Does not change pay. 0% counts only spoiled cargo. A new threshold applies to deliveries from then on; months already measured keep the old one until they leave the 12-month window, so a warned line clears only gradually after a change. |
| Show Stale Cargo warnings | on or off | on | Only the Stale Cargo warning. Off takes down every warning shown and forgets the lines' history; on again starts it fresh. Untick it, load and save before removing the mod: a save that holds a warning does not load without it ([removing-the-mod.md](removing-the-mod.md)). Does not change pay. |
| Non-perishable cargo | Full bonus, Half bonus, No bonus, No effect | Half bonus | How cargo at or above the non-perishable delivery time is paid: the whole curve, the curve with half its bonus (120% becomes 110%; penalties in full), the curve's penalties only (pay never above normal), or normal game pay. Stale Cargo warnings count it in every case. |
| Non-perishable delivery time | 15 to 75 min, 5 min steps | 25 min | The base delivery time (the cargo file's `timeToDeliverInSeconds`) from which a cargo is non-perishable. At 25 min only food is perishable (meat 15 min, fish, vegetables and beverages 18.75 min, grain 21.4 min); goods sit at 25 to 37.5 min, raw and bulk cargo at 50 and 75 min. The Delivery Time tab shows the base time x 1.5 in 1900, falling to x 0.75 from 2020. |

If the freshness points are not in order (full bonus >= normal pay >= lowest pay), the mod lowers the later point to the earlier one: with 35%, 45% and 70% it runs on 35%, 35% and 35%, while the dialog keeps showing what was set. The mod writes the values it used to the game log as `BEST_BEFORE curveSettings`, with the source (`params` for the in-game settings) and `adjusted=yes` when it had to lower points. That line comes only when the curve differs from the one stored in the save; the `BEST_BEFORE loadParams` line (the settings as list positions, one per load) is what the tools read to know the curve a run was played on.

Saves made before the settings existed have none, and the game fills in the defaults, so the mod plays them on the default curve (checked on one such save). The curve in [settings.tl](../best_before_1/content/settings.tl) is only a fallback for when the game hands over no settings.

## Test: the stale threshold slider (24 Oct 2026)

One old save with the mod already active (save series WR26A Giga-Tv3 1915, 1.2-dev from the staging folder), three saves in a row. The values are the stored list positions (1-based; 3 is 10%, 5 is 20%); the header was read with `save_header.py` of the [tf3-save-format](https://github.com/WuphonsReach/tf3-save-format) repo.

| Step | Save header (`best_before_1` params) | Game log |
|---|---|---|
| Save made before the slider existed (`1024-1545`) | five keys, no `bestBefore.staleBelow` | |
| Load Game, dialog showed 10%, saved as `1024-1606` | `bestBefore.staleBelow` = 3 | `loadParams ... staleBelow=3` |
| Load Game with the slider raised to 20%, saved as `1024-1620` | `bestBefore.staleBelow` = 5 | `loadParams ... staleBelow=5`, `staleRoll ... staleBelow=0.2` |

`verify_run.py` passed on the 20% run with 229 units checked against the threshold. Not tried: a 0% or 25% setting, and what the warning does on a line whose recent months were measured at the old threshold.

## Test: non-perishable cargo (28 Oct 2026)

Two old saves made before the settings existed, 1.3-dev from the staging folder, `logLevel` curve. These runs predate Half bonus, when the list had three entries: position 2 was No bonus and 3 No effect (now 3 and 4), so `verify_run.py` and `replay_curve.py` misread the mode of these logs' `loadParams`. Each run passed `verify_run.py`, and a separate recomputation of every unit's rate from its freshness, the logged curve and the non-perishable rule matched all of them. Cargo type numbers are the log's: 1 grain, 6 fish, 7 meat, 9 vegetables, 12 logs, 13 planks, 18 crude oil, 20 fuel.

### No bonus on the 1900 save

WR26A Giga-Tv3 1900 (Jan 1900, its own curve 150% / 50% / 15% / 0% / 0%). The dialog showed Full bonus and 25 min; No bonus was picked before Load Game. The log had `loadParams ... nonPerishable=2 nonPerishableTime=3` and `curveSettings ... nonPerishable=noBonus nonPerishableSeconds=1500`. About 11 minutes of play, 722 units, `verify_run.py` passed:

| Class | Cargo type | Base time | Units | Pay | Freshness (corrected) |
|---|---|---|---|---|---|
| Perishable | 6 | 1125 s | 148 | x1.50 | 0.79 to 0.83 |
| Perishable | 9 | 1125 s | 120 | x1.49 on average | 0.48 to 0.56 |
| Non-perishable | 18 | 3000 s | 251 | x1.00 | 0.83 to 0.85 |
| Non-perishable | 12, 13 | 3000 s | 120 | x1.00 | 0.77 to 0.93 |
| Non-perishable | 20 | 2250 s | 83 | x1.00 | 0.44 to 0.52 |

Every non-perishable unit was fresh enough for the full bonus and was paid normal pay. All 722 units were counted for the Stale Cargo warning; none was stale. No non-perishable unit fell below break-even, so the penalty side of No bonus was not exercised. The autosaves made during the run store `bestBefore.nonPerishable` = 2 and `bestBefore.nonPerishableTime` = 3 (read with `save_header.py`), the same positions the log showed.

### Four runs on the 1974 save

WR26A Giga-Tv3 1974-test (Jun 1974, rank CEO, delivery limit x1.0375), loaded four times from the same Load Game, so the runs replay largely the same deliveries; each ran about 6 to 8 minutes. The save's own curve is 150% / 50% / 15% / 0% / 0% with the warning at 5%; run B used 170% / 60% / 20% / 0% / 0%. On this save the logs and part of the fuel arrive below break-even. It carries no cargo with a base time between 21.4 min (grain) and 37.5 min (fuel), so any cutoff from 25 to 35 min splits it the same way.

| Run | Mode, cutoff | `loadParams` | Units | Left alone |
|---|---|---|---|---|
| A | Full bonus, 25 min | `nonPerishable=1 nonPerishableTime=3` | 2,007 | 0 |
| B | No bonus, 30 min | `nonPerishable=2 nonPerishableTime=4` (`nonPerishableSeconds=1800`) | 1,631 | 0 |
| C | No effect, 25 min | `nonPerishable=3 nonPerishableTime=3` | 1,715 | 1,205 |
| D | No effect, 40 min | `nonPerishable=3 nonPerishableTime=6` (`nonPerishableSeconds=2400`) | 1,964 | 917 |

Average pay multiplier by cargo (units paid below x1 in brackets; "game" is a unit the mod left alone, paid in full):

| Cargo | Base time | A | B | C | D |
|---|---|---|---|---|---|
| Fish (6) | 18.75 min | x1.43 | x1.52 | x1.43 | x1.43 |
| Vegetables (9) | 18.75 min | x1.26 | x1.25 | x1.27 | x1.26 |
| Grain (1), mostly late | 21.4 min | x0.38 (64) | x0.32 (93) | x0.35 (64) | x0.38 (64) |
| Fuel (20) | 37.5 min | x1.21 (95) | x0.94 (78) | game | x1.22 (90) |
| Logs (12) | 50 min | x0.69 (all) | x0.59 (all) | game | game |
| Crude oil (18), planks (13) | 50 min | x1.48, x1.50 | x1.00 | game | game |

- No bonus (B): crude oil, planks and the 302 fresh fuel units were held at exactly x1.00, while all 64 logs and 78 late fuel units still lost pay.
- No effect (C, D): every non-perishable unit logged `billing=none` and got no ticket answer. The log train (line 412766, 64 units at freshness 0.11 to 0.13, about $4.8M of predicted pay) was paid in full; the same unit was answered x0.805 in A and x0.603 in B.
- The 40 min cutoff (D) made fuel perishable again: its pay matched run A, unit for unit on 411 of the 468 units both runs delivered (the others arrived seconds apart in the replay, so their freshness differed).
- The player's income matched base pay times the answers plus passenger fares within 1% in every run (C: 1.000). All units were counted for the Stale Cargo warning in every mode; one grain line stayed warned throughout.

## Test: Half bonus (29 Oct 2026)

WR26A Giga-Tv3 1900 1029-0458 (Jan 1900, 1.3-dev from the staging folder after a restart, `logLevel` curve). The save was made before the restart with No bonus picked on the three-entry list (stored position 2); after the restart the dialog showed Half bonus for it, so the renumbered list moved the save to Half bonus as expected. Curve 150% / 30% / 15% / 0% / 0%, warning at 10%. Log `loadParams ... freshPay=11 bonusDownTo=7 breakeven=4 nonPerishable=2 nonPerishableTime=3` and `curveSettings ... nonPerishable=halfBonus nonPerishableSeconds=1500`. About 12 minutes of play (09:10 to 09:22Z), 1,587 units, `verify_run.py` passed (its Half bonus check: no non-perishable rate above x1.25). A recomputation of every unit's rate from its freshness, the curve and the halved bonus matched all 1,587.

| Class | Cargo type | Base time | Units | Pay | Freshness (corrected) |
|---|---|---|---|---|---|
| Perishable | 6 fish | 1125 s | 326 | x1.50 | 0.75 to 0.83 |
| Perishable | 9 vegetables | 1125 s | 231 | x1.50 | 0.51 to 0.56 |
| Non-perishable | 18 crude oil | 3000 s | 492 | x1.25 | 0.85 to 0.89 |
| Non-perishable | 20 fuel | 2250 s | 248 | x1.25 | 0.40 to 0.52 |
| Non-perishable | 19 chemicals | 1800 s | 197 | x1.25 | 0.73 to 0.76 |
| Non-perishable | 12 logs, 13 planks | 3000 s | 93 | x1.25 | 0.77 to 0.93 |

Every unit arrived above the full-bonus freshness (30%), so none was paid below normal and none was stale; the penalty side of Half bonus was not exercised. The estimated bonus over the run was $7,172,312, and the player's income matched base pay times the answers plus passenger fares at 0.999.

## Test: Half bonus on the 1974 save (30 Oct 2026)

WR26A Giga-Tv3 1974-test 1025-1103, the save of the four 28 Oct runs (Jun 1974, rank CEO), 1.3-dev from the staging folder after a restart, with Half bonus as the shipped default; `logLevel` curve. The dialog showed the save's curve 150% / 50% / 15% / 0% / 0%, warning at 5%, Half bonus and 25 min. Log `loadParams bonusDownTo=11 breakeven=4 freshPay=11 nonPerishable=2 nonPerishableTime=3 ...` and `curveSettings ... nonPerishable=halfBonus nonPerishableSeconds=1500`. Played from Jun 18 to about Aug 27, 1974 (12:10 to 12:18Z), 1,997 units, 1,419 of them non-perishable; `verify_run.py` passed (income 0.991 of base pay times the answers plus fares, as in run A). A recomputation of every unit's rate from its freshness, the curve and the halved bonus matched all 1,997.

| Cargo | Class | Freshness band | Units | Pay |
|---|---|---|---|---|
| Crude oil (18) | non-perishable | full bonus (50% and up) | 708 | x1.250 |
| Crude oil (18) | non-perishable | slope (15% to 50%) | 63 | x1.136 to x1.182 |
| Planks (13) | non-perishable | full bonus | 48 | x1.250 |
| Fuel (20) | non-perishable | full bonus | 60 | x1.250 |
| Fuel (20) | non-perishable | slope | 323 | x1.000 to x1.249 |
| Fuel (20) | non-perishable | below normal (under 15%) | 89 | x0.417 to x0.999 |
| Logs (12) | non-perishable | below normal | 128 | x0.539 to x0.839 |
| Fish (6) | perishable | full bonus / slope | 127 / 110 | x1.500 / x1.276 to x1.429 |
| Vegetables (9), meat (7) | perishable | slope | 227 / 14 | x1.116 to x1.485 / x1.229 to x1.267 |
| Grain (1) | perishable | slope / spoiled | 36 / 64 | x1.040 to x1.075 / x0 |

Against run A (Full bonus, same start), 1,822 units were delivered in both runs and 1,626 of them at identical freshness. Every one of those was paid as Half bonus says, to within 1e-13: the 204 non-perishable and 64 perishable units at or below normal pay got exactly run A's rate, the 1,079 non-perishable units above it got 1 plus half of run A's extra, and the 279 perishable units above it got run A's rate. The estimated bonus fell from $8,674,502 (run A) to $5,051,515 while the deductions stayed about the same ($6,652,850 and $6,580,228). The grain line "CRA-DER CXR West Grain" was warned for stale cargo, as in the earlier runs; no other warning came.

