# TODO

## Bookings removal (merged as PR #33)

- [ ] Decide whether to clear the leftover state of older saves. Saves from 1.2 and earlier keep the unused `pending`, `units` and `batches` entries in the probe's game script state; they do no harm but are never removed. A 1.0.1 save made while a few deductions were still queued loses those few, since nothing sends the queue any more.

## Non-perishable cargo, issue #27 (merged as PR #34, which closed the issue)

In-game tests are at the end of `docs/changing-settings.md`.

- [ ] Reply on issue #27 (closed by the merge, no reply posted yet).

## Half bonus for non-perishable cargo

Half bonus is second in the "Non-perishable cargo" list, so No bonus and No effect moved from 2 and 3 to 3 and 4.

- [ ] No bonus and No effect still behave as before at their new positions (`loadParams` 3 and 4).

## Listing gallery images

The cover `0.jpg` already draws the pay curve; a third image showing pay in play was considered and skipped.

- [ ] A third image: a line window with the Stale Cargo banner, taken in 1.2 (text "below the mod's stale freshness setting"); add the [L] line manager with the icon on that line's row if it fits in one frame.
- [ ] Recheck the mod.io page: clicking the second thumbnail did not show the settings image right after the 1.3 upload (30 Oct 2026), although the image itself loads ([Gallery](docs/publishing.md#gallery)). The next upload carries it as `2.jpg`, which may fix it.
- [ ] At the next upload, check whether the upload writes a `workshop_preview.jpg` of its own (if it does, keep or delete it as the dialog's order needs) and that the page shows `2.jpg` second ([Gallery](docs/publishing.md#gallery)).

## Review fixes (30 Oct 2026)

A whole-repo review; the stale take-down retry, `guardLog`, the `CRITICAL`/`logError` scan, the rate check and the stricter version check are in. One clean 21-month run at `summary` on WR26A 1904 (log `local/logs/stdout-20261030-1900-review-fixes.txt`): no `logError`, no errors, monthly summaries steady.

In-game checks still open:

- [ ] A run at `curve`, then `verify_run.py`: the new "rates against the curve" check passes on a live log, no `logError` line.
- [ ] Untick "Show Stale Cargo warnings" on a save that holds a warning: one `staleWarnings ... count=0 lines=none` line with no `error=`, not repeated the next month. The retry after a refused send is tested only against a mocked API.

Review findings left for later:

- [ ] Logging work at `logLevel = off`: the arrival handler still reads the pay scale and predicts each unit's pay for a summary that is never written, and the summary counters grow; a save first played at `off` and then at `summary` overstates its first summary's arrivals (`logSummary` sets `summaryTime` without zeroing them).
- [ ] Freshness is worked out in three places in `probe.script.tl` (the ticket answer, its log, the arrival); one helper would keep them from drifting.
- [ ] The fallback delivery limit (1.5 x the file time when the game's call fails) could use the settled year rule instead.
- [ ] `lastCurveNote` in the probe state is written and never read.
- [ ] Deliveries counted since the last roll are dropped when a line's route changes.
- [ ] `fallbackSettings` in `mod.script.tl` lacks the stale and non-perishable keys although its comment says it mirrors `settings.tl`.
- [ ] `cpu_sample.py report --from/--until` places the times on the first sample's date, so a window across midnight UTC is wrong (a window after midnight reports 0 CPU).
- [ ] `verify_run.py` and `ticket_probe.py` crash on a log whose last line was cut mid-write (a copy taken while the game writes); drop an unfinished last line.
- [ ] `verify_run.py` pairs ticket items with arrivals by unit id only; ids are reused, so also requiring the same `now` would close a gap.
- [ ] `extract_run.py --slug` doubles the name for logs without an HHMM time; a log ending in a line without a timestamp breaks its save lookup (caught, logged as an error in the run's json).
- [ ] `make_preview.py` and `make_gallery.py` hard-code the default curve and texts; nothing checks them against `mod.json`.
