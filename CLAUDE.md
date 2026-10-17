# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Transport Fever 3 script mod (`best_before_1/`) that makes cargo pay scale with freshness. It is early work: the mod is a test probe, not a release. The README and [docs/](docs/README.md) carry the status, the verified game facts ([docs/findings.md](docs/findings.md)) and the open questions ([docs/future/](docs/future/)). Read findings before changing mechanics; several approaches were tried and set aside ([docs/future/discarded.md](docs/future/discarded.md)).

There is no build step and no unit tests. The code is Teal (`.tl`) that the game loads directly, and the only checks are the type checker and testing in the game.

## Commands

```bash
# Type check (needs gitignored tlconfig.lua copied from tlconfig.example.lua, with <tf3_install_folder> filled in)
export PATH="$HOME/.luarocks/bin:$PATH"; eval "$(luarocks path --local)"
tl check best_before_1/content/mod.script.tl
tl check best_before_1/content/probe.script.tl

# Check a test run from the game log alone
python3 tools/verify_run.py local/logs/stdout-<date>-<time>.txt

# Cut a run out of a raw log into small files (local/runs/<date>-<time>-<slug>.arrivals.csv, .journal.csv, .json) for replay_curve.py
python3 tools/extract_run.py local/logs/stdout-<date>-<time>.txt [--note "no-mod control"]
```

Run `tl check` on each script you touch; there is no single command for both.

## In-game test loop

- `best_before_1/` is symlinked into the game's `staging_area/` folder, so edits show up without copying, but the game must be restarted to reload scripts.
- The game log is `crash_dump/stdout.txt` beside that folder and is overwritten at each launch. Copy it to `local/logs/` (gitignored) before reading or verifying it. It is written live, so a run can be read while the game is still running. Log timestamps are UTC.
- Every line the mod writes starts with `BEST_BEFORE`. Keep that prefix and keep `tools/verify_run.py` and `tools/extract_run.py` in step when changing the log format: they parse `arrival`, `sending adjustment` and `journal` lines by their `key=value` fields. `finance` lines (the Finances tab's investment and other rows, logged at the first snapshot and whenever the balance moves by something other than income) are for reading by hand, as are `company` lines (the company's rank and ticket price multiplier, logged at the first update and when they change).

## Architecture

Pay for a cargo unit is decided by the engine; a mod cannot see freshness at that point. So the mod lets the engine pay in full and books a correcting entry afterwards. Three pieces work together:

- **[mod.json](best_before_1/mod.json)** sets `preRunScript` to `mod.script@preRunFn`, which replaces `baseConfig.economy.cargoIncomeScript` with `calcCargoIncomeFn`. This is a logging stub only (same formula as the base game, pay unchanged). Only one mod can replace that script, so it is a conflict risk; it is meant to go before a release.
- **[probe.gs.lua](best_before_1/content/probe.gs.lua)** is the game script registration (plain Lua, not Teal). It points the game script's `update` and `handleEvent` at the functions in `probe.script.tl`. `.tl` files are referenced by the `file@function` form, for example `best_before_1::/probe.script@update`.
- **[probe.script.tl](best_before_1/content/probe.script.tl)** is the real logic. `handleEvent` receives `SimCargoSystem` `OnToArriveAtDestination` (subscribed in `update`), computes each unit's freshness (`1 - (now - pickupTime) / (timeToDeliverInSeconds x 1000 x 1.5)`), predicts the unit's pay from source and target construction positions, and queues a negative deduction in the game script state. `update` sums the queue per carrier and sends it to the player's account with `makeJournalBookAssetCmd`.

Game script constraints that shape this code (details in findings):

- `sendCommand` cannot be called from `handleEvent` and cannot take a result callback, so the handler queues and `update` sends. Success is judged from the player's balance, not from a callback.
- Module-level variables do not persist between calls. State that must survive lives in the game script `state` (`state:get()` and `state:set()`).
- Journal entries need `time = -1`.
- Guard every entity lookup with `api.engine.entityExists`. A vehicle or line sold while its cargo travels makes lookups raise "Invalid entity" and aborts the whole event. Read the carrier from the pickup point, not from the vehicle.
- Deductions go to the player only. The game pays a delivered unit once and shares the pay along its chain by an unknown formula, so booking to the first vehicle or line is wrong for transferred cargo.

## Conventions

- The pay curve's five settings (plus the stored-cargo mode) live in `best_before_1/content/settings.tl`, loaded with `ug_require "best_before_1::/settings.tl"` (the `::/` shorthand does not resolve in the mod scripts) by the probe and by `mod.script.tl` (which logs them once per game start as `BEST_BEFORE settings`); `tools/replay_curve.py` reads the same file for its defaults. The 0.96426 engine factor is a test value at the top of `probe.script.tl`.
- Keep the README short and put detail in `docs/`. Links to the sibling [tf3-save-format](https://github.com/WuphonsReach/tf3-save-format) repo are pinned to one commit (see [docs/README.md](docs/README.md)), not to its main branch.
- Lay out every doc and README for a reader who wants the answer first: an "In short" section at the top (key drivers, how we think it works, how sure we are, what is unknown), then the detail, and test results, logs and run tables at the bottom. Update "In short" when a new run changes a conclusion. Applies to the notes you create or touch.
- The mod ships no game files. `all_def.tl` and `tlconfig.example.lua` are for type checking only and point at the game's own type definitions.
