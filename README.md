# tf3-best-before-mod

A Transport Fever 3 mod that makes cargo pay follow freshness. Fresh cargo earns a bonus; slow or spoiled cargo earns less. The curve is adjustable in game.

**Get it:** [Best Before: Cargo Freshness on mod.io](https://mod.io/g/transportfever3/m/best-before-cargo-freshness) (mod id 6459472). Subscribe there or in the game's Mod Hub (search for "Best Before"), then activate it under Mods in New Game or Load Game.

## In short

- **What it does.** Before the game pays for a delivered cargo unit, it asks scripts for a pay multiplier (the ticket price event). The mod works out how fresh the unit is and answers 1 + the curve's bonus or deduction. The game pays the changed amount and shares it along the unit's trip as usual, so every vehicle and line that carried the unit shows the change, as does the player's account. Every line the mod writes to the game log starts with `BEST_BEFORE`.
- **Status: early test version, public on mod.io** (release 1.2, 25 Oct 2026, PC and console; mod.io labels every file "1.0"). The mechanism has been checked in the game on six games, most of them replayed several times from the same starting point to try other curves or check performance: bonuses, deductions up to -100%, chains of three legs, and six calendar years against a no-mod control. The default curve (+20% bonus, break-even at 80% of the delivery limit used, -100% penalty) is a candidate: replayed over those games' seven starting points (each counted once), it nets +7.7% of base pay.
- **Stale Cargo warnings.** A line whose deliveries have been mostly stale over the past months gets a "Stale Cargo" warning in the game's notifications and in the Line & Vehicle Management window (not in the F2 statistics list). Tested in the game on two saves: one line warned, cleared once its route was shortened, and warned again when it was lengthened. See [docs/stale-line-warnings.md](docs/stale-line-warnings.md).
- **Seeing what the mod did.** The change is inside the game's own pay, so it shows wherever that pay shows: the income figure that floats over a vehicle or station as it unloads, and the income in the vehicle and line windows. There is no separate figure over the building that takes the delivery, as there was in 1.0.1. On one test line a grain train's trip showed $740,297 where the same trip paid $3,043,520 without the mod, matching the log. Red figures over vehicles are usually maintenance costs. Details in [docs/how-it-works.md](docs/how-it-works.md).
- **Known conflict in 1.2.** The published release replaces the game's cargo income function with a copy that only logs (pay unchanged), so it conflicts with any other mod that replaces that function. The next release leaves that function to the game; the copy stays in the code as a test switch (`incomeLogging` in `settings.tl`, off).
- This is an unofficial mod. It contains no files from the game.

## The pay curve

Freshness is 1 when a unit is picked up and 0 at its delivery limit, the limit the game sets for the save and the one the cargo bar in a vehicle's window runs against. Pay follows this shape:

1. A bonus at full freshness, level down to a first freshness point.
2. A straight line down to the break-even point (normal pay).
3. A straight line on to the maximum penalty at a second freshness point.
4. That penalty below the second point and for cargo the game marks spoiled.

Cargo that waited in a warehouse is judged on its age with the warehouse pause taken off (other ways of judging it: [docs/future/stored-cargo-modes.md](docs/future/stored-cargo-modes.md)).

There are nine settings, set in game: New Game or Load Game, the Mods tab, the gear next to the mod. The game keeps them in the save, and a player can change them on any load. A save without them plays on the defaults in `best_before_1/mod.json`.

- Pay for fresh cargo (100% to 200%).
- The freshness down to which that bonus lasts.
- The freshness that earns normal pay.
- The freshness at and below which the lowest pay applies.
- Pay for spoiled cargo (0% to 100%).
- The freshness below which a delivery counts as stale for the Stale Cargo warning (0% to 25%, default 10%; no effect on pay).
- A check box that turns the Stale Cargo warnings off (on by default). Before removing the mod from a save, untick it, load and save; see [docs/removing-the-mod.md](docs/removing-the-mod.md).
- How non-perishable cargo is paid: the whole curve (the default), half the bonus, penalties only, or not touched.
- The base delivery time (the cargo file's) from which a cargo counts as non-perishable (15 to 75 min, default 25 min: only food is perishable).

`logLevel` is not an in-game setting; it stays in `best_before_1/content/settings.tl` and sets how much the mod writes to the game log: `off`, `summary` (a totals line about once a game month; the default), `curve` (a line per delivered unit, enough for the tools below) or `full` (adds vehicle and line names, chains and per-vehicle ledgers). Measured on one save at 4x over the same game dates, `full` cost the simulation threads about 1 to 3% more CPU than `off`, inside the run-to-run noise, and the game ran at the same speed. So the levels differ in log size and readability, not speed.

The work is done by `best_before_1/content/probe.script.tl`, which answers the ticket price event for each delivered unit with 1 + the adjustment ([docs/future/line-billing.md](docs/future/line-billing.md) has the runs that showed the game scales the whole chain's pay by it). At `logLevel = "full"` the log names every vehicle and line a unit travelled on and the balance of each, so the split of pay along a chain can be studied.

## Tools

- `tools/verify_run.py` checks a run from the game log alone: no error lines, no gaps, every unit answered with its rate, and non-perishable cargo paid as the settings say. Run it on a copy of `crash_dump/stdout.txt` made at `logLevel` `curve` or `full`.
- `tools/extract_run.py` cuts a run's arrivals, balance snapshots and facts (save, settings, totals) out of a raw log into small CSV and JSON files under `local/runs/`. It corrects the pay prediction to the save's Cargo Income setting and earned rank, so runs from different saves can be replayed together.
- `tools/replay_curve.py` applies the five-setting curve and the non-perishable settings to the arrivals in one or more logs or extracted `.arrivals.csv` files and prints the net change in pay, each run on the curve it was played on. `--use-defaults` replays on `settings.tl`'s numbers instead; `--sweep`, `--solve-bonus` and `--tables` help tune the defaults without the game.
- `tools/cpu_sample.py` samples the game's simulation and main threads and the whole machine's CPU every few seconds while you play (two CSV files under `local/cpu/`), then reports CPU seconds per game month to compare log levels. Run `sample` for at least 5 minutes while the game runs, then `report` with the game log.
- `tools/make_preview.py` draws the listing's preview image, `best_before_1/_metadata/workshop_preview.jpg`.

## Documentation

- [docs/changing-settings.md](docs/changing-settings.md): how to change the settings on a new game and on a saved game, with screenshots.
- [docs/removing-the-mod.md](docs/removing-the-mod.md): how to take the mod out of a save (turn the Stale Cargo warnings off first, or the save will not load).
- [docs/how-it-works.md](docs/how-it-works.md): how the mod turns freshness into a pay multiplier, and where it can over-penalize.
- [docs/stale-line-warnings.md](docs/stale-line-warnings.md): the warning for lines that mostly deliver stale cargo, its rule and settings, and how it handles lines that change.
- [docs/findings.md](docs/findings.md): what we have verified in the game, and the results of the test runs.
- [docs/publishing.md](docs/publishing.md): the mod.io listing (name, summary, tags, description), how to upload an update with the game's uploader, what ships, and what is known about hub search.
- [CHANGELOG.md](CHANGELOG.md): what changed in each version, with the one-line release note for the in-game uploader.
- [docs/future/](docs/future/): ideas set aside, things that need support from the game, open questions, and the test records behind ticket billing and the delivery limit. The index is [docs/README.md](docs/README.md).

## Development

Type checking uses the Teal compiler (`tl`, install with `luarocks install --local tl`) against the game's own type definitions:

1. Copy `tlconfig.example.lua` to `tlconfig.lua` and replace `<tf3_install_folder>` with your game install path (`tlconfig.lua` is gitignored).
2. Run `tl check` on each of `best_before_1/content/mod.script.tl`, `probe.script.tl` and `stale_line_warning.script.tl`.

## Licence

MIT, see [LICENSE](LICENSE).
