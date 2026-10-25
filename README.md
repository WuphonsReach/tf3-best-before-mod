# tf3-best-before-mod

Transport Fever 3 mod: cargo pay scales with freshness. Fresh cargo earns a bonus, slow or spoiled cargo earns a penalty. Adjustable curve.

**Get it:** [Best Before: Cargo Freshness on mod.io](https://mod.io/g/transportfever3/m/best-before-cargo-freshness) (mod id 6459472). Subscribe there or in the game's Mod Hub (search for "Best Before"), then activate it under Mods in New Game or Load Game.

## In short

- **What it does.** For each delivered cargo unit the mod works out a freshness adjustment (a bonus or a deduction) and hands the game a pay multiplier for the unit before the game pays it (the ticket price event). The game pays the changed amount and shares it along the unit's chain, so the vehicles and lines that carried it show the change, not only the player's account (from 1.2; 1.0.1 booked the adjustment to the player's account only, which `billing = "bookings"` in `settings.tl` still does). It logs everything with lines starting `BEST_BEFORE`.
- **Status: early test version, public on mod.io** (release 1.2, 25 Oct 2026, PC and console; mod.io labels it "1.0"; the first upload, 17 Oct, did not load, fixed in 1.0.1). The mechanism is checked in the game on six games, most of them replayed several times from the same starting point to try other curves or check performance: bonuses, deductions up to -100%, chains of three legs, six calendar years against a no-mod control. The default curve (+20% bonus, break-even at 80% of the spoil limit used, -100% penalty) is a candidate; replayed over those games' seven starting points (each counted once) it nets +7.7% of base pay.
- **Stale line warnings (since 1.0.1).** A line whose deliveries are mostly stale over the past months gets a "Stale Cargo" warning in the game's notifications and in the Line & Vehicle Management window (not in the F2 statistics list). Tested in the game on two saves: one line warned, cleared once its route was shortened, and warned again when it was lengthened. See [docs/stale-line-warnings.md](docs/stale-line-warnings.md).
- **Seeing what the mod did.** Watch the building that takes a delivery: the game floats a small number over it for each unit, and the mod's bonus or deduction for that unit shows there (checked against the log to the dollar on road and ship lines; units unloading together add up in one number). The game's own pay shows too, over the station or ship, and passenger fares over bus stops. Red numbers over vehicles are usually maintenance costs. Details in [docs/findings.md](docs/findings.md).
- **Not done.** The mod still replaces the game's cargo income function with a logging copy, so it conflicts with other mods that replace it.
- This is an unofficial mod. It contains no files from the game.

## The pay curve

Pay changes with the unit's freshness (1 at pickup, 0 at the cargo's delivery limit as the game sets it for the save, the limit the vehicles' cargo bar runs against): a bonus at full freshness that stays level down to a first freshness point, a straight line down to the break-even point (full pay), a straight line on to a maximum penalty at a second freshness point, then the same penalty down to 0% freshness and for spoiled cargo. Seven settings, set in game (New Game or Load Game, Mods tab, the mod's gear; the game keeps them in the save and a player can change them on any load): pay for fresh cargo (100% to 200%), the freshness down to which that bonus lasts, the freshness that earns normal pay, the freshness at and below which the lowest pay applies, the pay for spoiled cargo (0% to 100%), the freshness below which a delivery counts as stale for the Stale Cargo warning (0% to 25%, default 10%; no effect on pay), and a check box that turns the Stale Cargo warnings off (on by default; before removing the mod from a save, untick it, load and save, see [docs/removing-the-mod.md](docs/removing-the-mod.md)). A save without them plays on the defaults in `best_before_1/mod.json`. Cargo that waited in a warehouse is always judged by its corrected age (other modes: [docs/future/stored-cargo-modes.md](docs/future/stored-cargo-modes.md)). `logLevel` is not an in-game setting and stays in `best_before_1/content/settings.tl`: picks how much the mod writes to the game log: `off`, `summary` (a totals line about once a game month, the default), `curve` (a line per delivered unit, enough for the tools below) or `full` (adds vehicle and line names, chains and per-vehicle ledgers). Measured on one save at 4x over the same game dates, `full` cost the simulation threads about 1 to 3% more CPU than `off` (inside the run-to-run noise) and the game ran at the same speed, so the levels are about log size and readability, not speed.

The probe in `best_before_1/content/probe.script.tl` answers the ticket price event for each delivered unit with 1 + the adjustment ([docs/future/line-billing.md](docs/future/line-billing.md) has the runs that showed the game scales the whole chain's pay by it). With `billing = "bookings"` it computes the adjustment for each arriving unit instead, queues it in the game script state, and `update` sends it, summed per carrier, to the player's account with no result callback. At `logLevel = "full"` the log names every vehicle and line a unit travelled on and the balance of every vehicle and line involved, so the split of pay along a chain can be studied.

## Tools

- `tools/verify_run.py` checks a run from the game log alone (no error lines, no gaps; with ticket billing every unit answered with its rate, with bookings units sent equal units adjusted and the bookings visible in the player's balance). Run it on a copy of `crash_dump/stdout.txt` made at `logLevel` `curve` or `full`.
- `tools/extract_run.py` cuts a run's arrivals, balance snapshots and facts (save, settings, totals) out of a raw log into small CSV and JSON files under `local/runs/`, and corrects the pay prediction to the save's Cargo Income setting and earned rank, so runs from different saves can be replayed together.
- `tools/replay_curve.py` applies the five-setting curve to the arrivals in one or more logs or extracted `.arrivals.csv` files and prints the net change in pay, each run on the curve it was played on (`--use-defaults` replays on `settings.tl`'s numbers instead; `--sweep`, `--solve-bonus` and `--tables` help tune the defaults without the game).
- `tools/cpu_sample.py` samples the game's simulation and main threads and the whole machine's CPU every few seconds while you play (two appended CSV files under `local/cpu/`), and reports CPU seconds per game month, to compare log levels (`sample` while the game runs for at least 5 minutes, then `report` with the game log).
- `tools/make_preview.py` draws the listing's preview image, `best_before_1/_metadata/workshop_preview.jpg`.

## Documentation

- [docs/changing-settings.md](docs/changing-settings.md): how to change the curve settings on a new game and on a saved game, with screenshots.
- [docs/removing-the-mod.md](docs/removing-the-mod.md): how to take the mod out of a save (clear the Stale Cargo warnings first, or the save will not load).
- [docs/how-it-works.md](docs/how-it-works.md): how the mod turns freshness into a pay multiplier (or a booking) and where it can over-penalize.
- [docs/stale-line-warnings.md](docs/stale-line-warnings.md): the warning for lines that mostly deliver stale cargo, its rule and settings, and how it handles lines that change.
- [docs/findings.md](docs/findings.md): what we have verified in the game and the results of the test runs.
- [docs/publishing.md](docs/publishing.md): the mod.io listing (name, summary, tags, description), how to upload an update with the game's uploader, what ships, and what is known about hub search.
- [CHANGELOG.md](CHANGELOG.md): what changed in each version, with the one-line release note for the in-game uploader.
- [docs/future/](docs/future/): ideas set aside, things that need support from the game, and open questions. The index is [docs/README.md](docs/README.md).

## Development

Type checking uses the Teal compiler (`tl`, install with `luarocks install --local tl`) against the game's own type definitions:

1. Copy `tlconfig.example.lua` to `tlconfig.lua` and replace `<tf3_install_folder>` with your game install path (`tlconfig.lua` is gitignored).
2. Run `tl check` on each of `best_before_1/content/mod.script.tl`, `probe.script.tl` and `stale_line_warning.script.tl`.

## Licence

MIT, see [LICENSE](LICENSE).
