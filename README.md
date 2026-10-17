# tf3-best-before-mod

Transport Fever 3 mod: cargo pay scales with freshness. Fresh cargo earns a bonus, slow or spoiled cargo earns a penalty. Adds spoilage to the economy. Adjustable curve.

**Status: early work.** `best_before_1/` is a test probe. For each arriving cargo unit it works out a *freshness deduction* (the part of the pay the freshness curve takes away) and books it back as a negative income entry to the player's account. It logs everything with lines starting `BEST_BEFORE`. The deduction mechanism has been checked in the game on small and large saves; settings and the final curve are not done.

Planned pay curve: a bonus at full freshness that stays level down to a first freshness point, a straight line down to the break-even point (full pay), a straight line on to a maximum penalty at a second freshness point, then the same penalty down to 0% freshness and for spoiled cargo. Five settings: the maximum bonus, the three freshness points and the maximum penalty.

This is an unofficial mod. It contains no files from the game.

## Licence

MIT, see [LICENSE](LICENSE).

## Development

Type checking uses the Teal compiler (`tl`, install with `luarocks install --local tl`) against the game's own type definitions:

1. Copy `tlconfig.example.lua` to `tlconfig.lua` and replace `<tf3_install_folder>` with your game install path (`tlconfig.lua` is gitignored).
2. Run `tl check best_before_1/content/mod.script.tl`.

## Documentation

- [docs/how-it-works.md](docs/how-it-works.md): how the mod turns freshness into a booking and where it can over-penalize.
- [docs/findings.md](docs/findings.md): what we have verified in the game and the results of the test runs.
- [docs/future/](docs/future/): ideas set aside, things that need support from the game, and questions to revisit. The index is [docs/README.md](docs/README.md).

## Status

The probe in `best_before_1/content/probe.script.tl` computes the freshness deduction for each arriving unit, queues it in the game script state, and `update` sends it, summed per carrier, to the player's account with no result callback. The curve takes its five numbers from `best_before_1/content/settings.tl` (edit them, restart the game and load a save to test other values); a positive result is booked as a bonus. The log names every vehicle and line a unit travelled on, each cargo type's delivery time and price function, and the balance of every vehicle and line involved, so the split of pay along a chain can be studied.

`tools/verify_run.py` checks a run from the game log alone (no error lines, no gaps, units sent equal units deducted, bookings visible in the player's balance). Run it on a copy of `crash_dump/stdout.txt`.

`tools/extract_run.py` cuts a run's arrivals, balance snapshots and facts (save, settings, totals) out of a raw log into small CSV and JSON files under `local/runs/`, and corrects the pay prediction to the save's Cargo Income setting and earned rank, so runs from different saves can be replayed together.

`tools/replay_curve.py` applies the five-setting curve to the arrivals in one or more logs or extracted `.arrivals.csv` files and prints the net change in pay (`--sweep`, `--solve-bonus` and `--tables` help tune the defaults without the game).

Next: test the curve in the game (the bonus has never been booked), in-game settings through `mod.json` instead of the file, and a decision on freshness for cargo that waited in a warehouse (the `stored` setting). The plan and the open questions are in [docs/future/](docs/future/).
