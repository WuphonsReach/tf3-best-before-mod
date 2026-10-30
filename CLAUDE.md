# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Transport Fever 3 script mod (`best_before_1/`) that makes cargo pay scale with freshness. It is public on mod.io as an early test version ([Best Before: Cargo Freshness](https://mod.io/g/transportfever3/m/best-before-cargo-freshness), mod id 6459472, release 1.3; mod.io labels every upload "1.0"), and still logs heavily for testing. The README and [docs/](docs/README.md) carry the status, the verified game facts ([docs/findings.md](docs/findings.md)) and the open questions ([docs/future/](docs/future/)). Read findings before changing mechanics; several approaches were tried and set aside ([docs/future/discarded.md](docs/future/discarded.md)).

There is no build step and no unit tests. The code is Teal (`.tl`) that the game loads directly, and the only checks are the type checker and testing in the game.

## Commands

```bash
# Type check (needs gitignored tlconfig.lua copied from tlconfig.example.lua, with <tf3_install_folder> filled in)
export PATH="$HOME/.luarocks/bin:$PATH"; eval "$(luarocks path --local)"
tl check best_before_1/content/mod.script.tl
tl check best_before_1/content/probe.script.tl
tl check best_before_1/content/stale_line_warning.script.tl

# Check that _content.json lists every file under content/ (the game cannot load a file the list leaves out); run before every upload
python3 tools/check_content_list.py

# Cheap consistency checks (JSON parses, mod.io_fileid.txt, modVersion vs CHANGELOG, settings.tl vs mod.json defaults, logLevel "summary"); CI runs this and check_content_list.py on every PR
python3 tools/check_repo.py

# Check a test run from the game log alone
python3 tools/verify_run.py local/logs/stdout-<date>-<time>.txt

# Cut a run out of a raw log into small files (local/runs/<date>-<time>-<slug>.arrivals.csv, .journal.csv, .json, plus index.csv) for
# replay_curve.py. It rebuilds the pay scale from the save the run loaded, so run it while that save still exists.
python3 tools/extract_run.py local/logs/stdout-<date>-<time>.txt [--note "no-mod control"]
python3 tools/replay_curve.py local/runs/<name>.arrivals.csv [more]   # pool the runs marked primary in index.csv (one per starting point); each run on the curve it was played on (--use-defaults: on settings.tl's)

# Compare the CPU cost of the log levels (sample while the game runs; report reads the game log for the game clock)
python3 tools/cpu_sample.py sample local/cpu/<name> [--also "steam|code"]   # writes <name>.process.csv and <name>.system.csv; run at least 5 minutes
python3 tools/cpu_sample.py report local/cpu/<name> [--log local/logs/<log>.txt | --game-months N]

# Redraw the mod's cover (best_before_1/_metadata/1.jpg, the gallery's first image, 1920x1080; needs rsvg-convert and the Lato font)
python3 tools/make_preview.py [--version 0.1] [--keep-svg local/preview/workshop_preview.svg]   # the version goes in the upper right corner, kept clear for it; --keep-svg also saves the SVG it was drawn from (not into best_before_1/)
cp best_before_1/_metadata/1.jpg best_before_1/_metadata/0.jpg   # 0.jpg is the Preview slot's cover (byte-identical); copy again after every redraw

# Redraw the gallery's second image (workshop_preview.jpg; the gallery orders by file name, see docs/publishing.md): the settings at their defaults with each group explained beside them, on the cover's background
python3 tools/make_gallery.py [--shot art/gallery/<screenshot>.png]   # cuts the dialog from the screenshot kept in art/gallery/ (not shipped); also rewrites docs/images/mod-settings-dialog.png from the same cut
```

Run `tl check` on each script you touch; there is no single command for both.

`.github/workflows/checks.yml` runs on every PR: a `python-checks` job (`check_content_list.py`, `check_repo.py`, `py_compile` of `tools/`) and a `teal-syntax` job (`tl gen` on each `.tl` file, which fails on syntax errors only). CI cannot run `tl check` because the game's type definitions are not in the repo, so the type check stays a local step. `check_repo.py` fails while `settings.tl` carries a test `logLevel`, so set it back to `summary` before pushing. Actions in workflows are pinned to full commit SHAs with the version in a trailing comment (`uses: actions/checkout@<sha> # v7.0.1`), at the latest release when added or bumped; look the SHA up with `gh api repos/<owner>/<action>/git/ref/tags/<tag>` and never use a floating tag like `@v4`. The repo ruleset `pr-checks` (on the default branch, no bypass actors) requires a pull request and the status checks `python-checks` and `teal-syntax`, so a PR cannot merge until both have run to completion and passed. The job names in `checks.yml` are the check names the ruleset matches: renaming a job means updating the ruleset (Settings > Rules) in the same change, or every PR will wait for a check that never reports.

## In-game test loop

- `best_before_1/` is symlinked into the game's `staging_area/` folder, so edits show up without copying, but the game must be restarted to reload the scripts and `mod.json`. `settings.tl` is the exception: its edits (`logLevel`) take effect on the next load, no restart.
- The game log is `crash_dump/stdout.txt` beside that folder and is overwritten at each launch. Copy it to `local/logs/` (gitignored) before reading or verifying it. It is written live, so a run can be read while the game is still running. Log timestamps are UTC.
- `logLevel` in `settings.tl` (`off`, `summary`, `curve`, `full`) sets what is logged; set `curve` or `full` for any run that `verify_run.py`, `extract_run.py` or `replay_curve.py` will read (`verify_run.py` refuses a log with no per-unit lines). Log work is skipped, not just the write, so keep new per-unit log strings inside the `logUnits`/`logFull` checks in `probe.script.tl`.
- To check what a save stored for the in-game settings, read its header with the sibling repo's `tools/save_header.py` (`tf3-save-format`; the mod's keys are under `params`, as 1-based list positions, so 3 is 10% on the stale slider) and compare with the log's `loadParams`. The sibling's screenshot index (`python3 tools/screenshot_index.py find --work local/screenshots TERM`, see its `.claude/skills/screenshot-index`) finds the dialog shots for a test.
- Every line the mod writes starts with `BEST_BEFORE`. Keep that prefix and keep `tools/verify_run.py` and `tools/extract_run.py` in step when changing the log format: they parse `arrival`, `journal`, `loadParams`, `curveSettings` and (verify_run.py) `staleRoll`, `staleLine` and `staleWarnings` lines by their `key=value` fields; `verify_run.py` also checks each arrival's `staleUnit` against the `staleBelow` in the `staleRoll` lines, so keep the arrival's `corrected`, `good` and `staleUnit` fields. `verify_run.py` (and `tools/ticket_probe.py`) also read the `ticketItem` and `ticketPrice` lines and the arrival's `rate` and `billing` fields: each arrival with `billing=ticket` must follow a `ticketItem` for the same unit whose `multiplier` equals its rate, and each with `billing=none` (non-perishable cargo under No effect) one whose `multiplier` is `none`; it checks the arrival's `perishable` against its `fileSeconds` and the non-perishable settings in `loadParams`. `loadParams` is written by `mod.script.tl`'s `preRunFn` once per load (the in-game settings as list positions, keys without the `bestBefore.` prefix) and is how the tools learn the curve a run was played on; `curveSettings` is written by the probe only when the curve differs from the one stored in the save, so a reload with unchanged settings logs none. `deliveryLimit` and `lineName` lines (the game's adjusted delivery time per cargo type, and each tracked line's entity id with its name; `verify_run.py` and `extract_run.py` skip them) and `finance` lines (the Finances tab's investment and other rows, logged at the first snapshot and whenever the balance moves by something other than income) are for reading by hand, as are `company` lines (the company's rank and ticket price multiplier, logged at the first update and when they change).

## Architecture

Pay for a cargo unit is decided by the engine, and the income function cannot see freshness. But before it pays a delivered unit the engine raises `OnCalcTicketPrice`, and the mod answers a pay multiplier for the unit (1 + the curve's adjustment); the engine pays that and shares it along the unit's chain, so every vehicle and line that carried it sees the change (runs in [docs/future/line-billing.md](docs/future/line-billing.md)). These pieces work together:

- **[mod.json](best_before_1/mod.json)** sets `preRunScript` to `mod.script@preRunFn`, which logs the version and settings of each load. Only with `incomeLogging = true` in `settings.tl` (test only, read when the game starts; `check_repo.py` fails unless it is `false`) does it replace `baseConfig.economy.cargoIncomeScript` with `calcCargoIncomeFn`, a logging stub (same formula as the base game, pay unchanged). Only one mod can replace that script, so the shipped mod leaves it to the game (1.2 and earlier replaced it).
- **[probe.gs.lua](best_before_1/content/probe.gs.lua)** is the game script registration (plain Lua, not Teal). It points the game script's `update` and `handleEvent` at the functions in `probe.script.tl`. `.tl` files are referenced by the `file@function` form, for example `best_before_1::/probe.script@update`.
- **[probe.script.tl](best_before_1/content/probe.script.tl)** is the real logic. `handleEvent` receives `OnCalcTicketPrice` (subscribed in `update` once per save, remembered in the state as `ticketPriceSubscribed`) and answers it in `ticketPrice`, judging each unit as below with the curve read straight from the in-game settings and nothing written to the state. It also receives `SimCargoSystem` `OnToArriveAtDestination` (subscribed in `update`), which comes at the same clock time after the ticket event, and computes each unit's freshness (`1 - (now - pickupTime) / limit`, the limit being the game's adjusted delivery time, `api.engine.util.stock.getAdjustedDeliveryTime`, with 1.5 x `timeToDeliverInSeconds` as the fallback, with the time `deliveryExtensionDuration` took off the age: stored cargo is always judged `corrected`, the other modes are kept in the code, see [docs/future/stored-cargo-modes.md](docs/future/stored-cargo-modes.md)), predicts the unit's pay from source and target construction positions, and logs an estimate of the curve's adjustment in money (for the log and the monthly summary; the engine has already paid the real one). The same handler counts each unit for its last leg's line, and `update` keeps a 12-month ring of stale shares per line and raises or clears "Stale Cargo" warnings once a game month ([docs/stale-line-warnings.md](docs/stale-line-warnings.md)).
- **[stale_line_warning.res.lua](best_before_1/content/stale_line_warning.res.lua) and [stale_line_warning.script.tl](best_before_1/content/stale_line_warning.script.tl)** register and draw that warning as a game notification type. The probe hands the whole warned set to the game's Notifications game script (`updatePersistent`); the warning's params must not change while it is shown, or the game re-creates it and it pops up again.

Game script constraints that shape this code (details in findings):

- `sendCommand` cannot be called from `handleEvent` and cannot take a result callback, so the Stale Cargo warnings are sent from `update`, under `pcall`.
- Module-level variables do not persist between calls. State that must survive lives in the game script `state` (`state:get()` and `state:set()`).
- Guard every entity lookup with `api.engine.entityExists`. A vehicle or line sold while its cargo travels makes lookups raise "Invalid entity" and aborts the whole event. Read the carrier from the pickup point, not from the vehicle.
- The ticket price handler writes no state: game scripts may run in one Lua state per thread, so a write there could be lost. It reads the curve with `readParamCurve` and works under `pcall` (an error must not abort the engine's event; an unanswered unit is paid in full).

## Conventions

- The pay curve's five settings, the stale-warning threshold and the stale-warning switch (`bestBefore.staleBelow` and `bestBefore.staleWarnings`, a check box, carried in the probe's `Curve` record as `staleBelowFreshness` and `staleWarnings` but not part of the pay), and the non-perishable settings (`bestBefore.nonPerishable`, a ComboBox stored as its 1-based position, and `bestBefore.nonPerishableTime`, a slider of minutes; `nonPerishable` and `nonPerishableSeconds` in the `Curve`, compared with the cargo file's `timeToDeliverInSeconds`, not the adjusted time, so a cargo's class does not change with the year) are in-game settings: the `params` in `mod.json`, read by the probe with `api.engine.config.getModParams()` on every `update` (see [docs/changing-settings.md](docs/changing-settings.md)). `best_before_1/content/settings.tl` holds `logLevel`, the numbers `tools/replay_curve.py` starts from, and a curve used only if the game hands over no settings; keep its curve equal to the `mod.json` defaults. It is loaded with `ug_require "best_before_1::/settings.tl"` (the `::/` shorthand does not resolve in the mod scripts) by the probe and by `mod.script.tl` (whose `preRunFn` logs them on every load as `BEST_BEFORE settings`, one load behind, and shows settings.tl's numbers, not the curve in force; that one is in `loadParams` and `curveSettings`; each `staleRoll` line carries only the stale threshold); `tools/replay_curve.py` reads the same file for its defaults. The pay scale (Cargo Income setting x the company's ticket price multiplier) is read at run time; the 0.96426 at the top of `probe.script.tl` is only the fallback when the multiplier cannot be read.
- Keep the README short and put detail in `docs/`. Links to the sibling [tf3-save-format](https://github.com/WuphonsReach/tf3-save-format) repo are pinned to one commit (see [docs/README.md](docs/README.md)), not to its main branch.
- Lay out every doc and README for a reader who wants the answer first: an "In short" section at the top (key drivers, how we think it works, how sure we are, what is unknown), then the detail, and test results, logs and run tables at the bottom. Update "In short" when a new run changes a conclusion. Applies to the notes you create or touch.
- The mod ships no game files. `all_def.tl` and `tlconfig.example.lua` are for type checking only and point at the game's own type definitions.

## Publishing

Details and the step-by-step are in [docs/publishing.md](docs/publishing.md).

- Uploads go only through the game's own uploader (Mod Hub, My Mods, the mod's dialog); the mod.io website refuses Transport Fever 3 uploads, and the website login does not reach the account that owns the mod. Uploading is outward-facing: the user does it, never a script.
- The uploader reads `best_before_1/_metadata/modinfo.json` (name, summary, description, tags) and the images in `_metadata/`. Edit the listing text in `docs/publishing.md` first, then mirror it into `modinfo.json`.
- `best_before_1/_metadata/mod.io_fileid.txt` holds the mod id and makes the dialog update the existing mod. Keep it committed and never delete it, or the next upload creates a second mod.
- The upload takes the whole `best_before_1/` folder except `_metadata/` (checked on a subscribed copy of 1.0), so anything put there ships. `best_before_1/_content.json` lists the files under `content/`, and the game builds the mod's file index from that list: a script file missing from it cannot be loaded (1.0 shipped without `settings.tl` in it and the game refused to start). Keep it in step when a script file is added, renamed or removed, and after every upload load a save with the published copy before calling the release good (staging link removed, subscribed copy only: with both present the game picks the staging copy and logs a `Multiple (2) mods with same id` warning). Keep `modVersion` in `mod.script.tl` and the top of `CHANGELOG.md` in step; the log line `BEST_BEFORE version` shows which copy loaded.
