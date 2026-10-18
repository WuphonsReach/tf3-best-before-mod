# Changelog

Newest first. The number in the title is `modVersion` at the top of [mod.script.tl](best_before_1/content/mod.script.tl), which the game log prints at every load as `BEST_BEFORE version <number>`. Each entry's last line is the one-liner for the Changelog field of the in-game uploader ([how to upload](docs/publishing.md#uploading-an-update)).

## 1.1 (not released yet)

- **Fixed: the game would not start with the mod.** The 1.0 file list (`_content.json`) left out `settings.tl`, the game builds its file index from that list, so the mod's first script failed with "module 'best_before_1::/settings.tl' not found" and the game answered "Could not initialize game: try removing the mod". 1.0 never loaded for anyone.
- **Fixed: the file list is checked.** `tools/check_content_list.py` fails if `_content.json` and `content/` differ; it is part of the upload steps.
- **Fixed: a missing `settings.tl` can no longer stop the game.** Both scripts load it under `pcall` and fall back to built-in numbers that mirror it; the log says so (`BEST_BEFORE settings.tl could not be loaded`).
- **New: "Stale Cargo" warnings.** A line whose deliveries are mostly stale gets a warning in the notification log and on the line; it clears when the line recovers. Rule and settings: [docs/stale-line-warnings.md](docs/stale-line-warnings.md). Turn off with `staleWarnings = false` in `settings.tl`.
- **New: version line in the log**, so a log shows which copy of the mod ran (the published mod and a `staging_area` copy share the id `best_before_1`).
- Also: a warning that fails to send is retried at the next roll and taken down once when the warnings are off; more stale-line log lines (the threshold in force, the stops before and after a reset).

Release note: `Fixes the game not starting with the mod. Adds Stale Cargo warnings for lines that mostly deliver spoiled cargo.`

## 1.0 (17 Oct 2026)

First public version, an early test version. It did not load: see 1.1.

- The pay curve with five in-game settings (pay for fresh cargo, bonus down to freshness, normal pay at freshness, lowest pay below freshness, pay for spoiled cargo), booked as one correcting entry to the company account.
- A logging copy of the base cargo income function (pay unchanged), and the `logLevel` switch in `settings.tl`.

Release note: none was written (the page shows "No release notes provided").
