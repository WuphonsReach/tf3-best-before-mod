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

- [ ] A third image (`3-stale-warning.jpg`): a line window with the Stale Cargo banner, taken in 1.2 (text "below the mod's stale freshness setting"); add the [L] line manager with the icon on that line's row if it fits in one frame.
- [ ] Recheck the mod.io page: clicking the second thumbnail did not show the settings image right after the 1.3 upload (30 Oct 2026), although the image itself loads ([Gallery](docs/publishing.md#gallery)). The next upload carries it as `2-settings.jpg`, which may fix it.
- [ ] At the next upload (with a release, not on its own), check that the dialog shows `1-cover.jpg` then `2-settings.jpg`, that the page shows both in that order and drops the `workshop_preview` images, and whether the upload writes a `workshop_preview.jpg` of its own ([Gallery](docs/publishing.md#gallery)).

## Review fixes (30 Oct 2026)

A whole-repo review; the stale take-down retry, `guardLog`, the `CRITICAL`/`logError` scan, the rate check and the stricter version check are in. One clean 21-month run at `summary` on WR26A 1904 (log `local/logs/stdout-20261030-1900-review-fixes.txt`): no `logError`, no errors, monthly summaries steady.

In-game checks still open:

- [x] A run at `curve`, then `verify_run.py`: passed on the 3 to 5 Nov 2026 run (266,625 arrivals after the last load: all rates match the curve, no error lines, no `logError`) and on the 5 Nov first session on the 1974 save (1,952 arrivals). See [changing-settings.md](docs/changing-settings.md#test-half-bonus-late-log-trains-on-the-1974-save-5-nov-2026).
- [x] Untick "Show Stale Cargo warnings" on a save that holds a warning: checked on 5 Nov 2026 on the 1974 save (one `staleWarnings ... count=0 lines=none` line, no `error=`, not repeated over about four game years; Active tab and top-bar icon clear, History keeps the entry), see [stale-line-warnings.md](docs/stale-line-warnings.md#the-off-switch-on-the-1974-save-5-nov-2026). The retry after a refused send is still tested only against a mocked API.

Review findings left for later:

- [ ] Logging work at `logLevel = off`: the arrival handler still reads the pay scale and predicts each unit's pay for a summary that is never written, and the summary counters grow; a save first played at `off` and then at `summary` overstates its first summary's arrivals (`logSummary` sets `summaryTime` without zeroing them).
- [ ] Freshness is worked out in three places in `probe.script.tl` (the ticket answer, its log, the arrival); one helper would keep them from drifting.
- [ ] Deliveries counted since the last roll are dropped when a line's route changes.
