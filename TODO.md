# TODO

## Bookings removal (merged as PR #33)

- [x] Test in game: done with the non-perishable No bonus run below (28 Oct 2026, 722 units): every ticket answer equal to its rate, no `sending` lines, `verify_run.py` passed.
- [ ] Decide whether to clear the leftover state of older saves. Saves from 1.2 and earlier keep the unused `pending`, `units` and `batches` entries in the probe's game script state; they do no harm but are never removed. A 1.0.1 save made while a few deductions were still queued loses those few, since nothing sends the queue any more.

## Non-perishable cargo, issue #27 (merged as PR #34, which closed the issue)

All in-game tests passed on 28 Oct 2026 (one 1900 run, four 1974 runs; details at the end of `docs/changing-settings.md`).

- [x] Dialog: both settings show with their names and defaults (Full bonus, 25 min); the list offers Full bonus, No bonus, No effect. The game shows no tooltips for mod settings, so there is nothing to check there.
- [x] Old saves: the 1900 and 1974 saves, made before the settings existed, showed the defaults and kept their own curves.
- [x] Save header: the 1900 run's autosaves store `bestBefore.nonPerishable` = 2 and `bestBefore.nonPerishableTime` = 3.
- [x] No bonus: fresh non-perishable cargo held at x1.00 (1900 and 1974), late logs and fuel still lose pay (1974, 30 min, break-even 20%).
- [x] No effect: non-perishable units log `billing=none` and get no ticket answer, the late log train included (1974, 25 min).
- [x] Another cutoff: at 40 min, fuel (37.5 min) is perishable and back on the curve (1974, No effect).
- [ ] Reply on issue #27 (closed by the merge, no reply posted yet).

## Half bonus for non-perishable cargo

A fourth entry in the "Non-perishable cargo" list, second after Full bonus: the curve with any bonus halved (120% becomes 110%), penalties in full. Not released, so the list was renumbered (No bonus 2 -> 3, No effect 3 -> 4); the 28 Oct test saves that store 2 now load as Half bonus.

- [x] Renumbering: a 1900 test save that stored position 2 (No bonus on the old list, dialog shot 05:02) showed Half bonus after the restart and logged `nonPerishable=halfBonus` (29 Oct 2026).
- [x] Dialog: the list opened shows Full bonus, Half bonus, No bonus, No effect, and a save that never had the mod (Hatchet River Valley 1945, saved after as "Hatchet River Valley 1945 - test best-before defaults 1030") shows all nine defaults, Half bonus among them (shots 08:24:13 and 08:24:29, 30 Oct 2026).
- [x] Half bonus, bonus side: on the 1900 save (150% curve) all 1,030 non-perishable units were paid x1.25 and all 557 perishable ones x1.50; `verify_run.py` passed (29 Oct 2026, 1,587 units).
- [x] Half bonus, penalty side: on the 1974 save, 217 logs and late fuel units below break-even were paid exactly run A's (Full bonus) rate, unit for unit; `verify_run.py` passed (30 Oct 2026, 1,997 units).
- [ ] No bonus and No effect still behave as before at their new positions (`loadParams` 3 and 4).

## Listing gallery images

The cover `0.jpg` already draws the pay curve; a third image showing pay in play was considered and skipped.

- [x] Check that the uploader takes `1.jpg` into the gallery: it does, ordered by file name before the settings image (1.3 upload, 30 Oct 2026; [Gallery](docs/publishing.md#gallery)). The settings image came first, so the thumbnails were moved in the dialog, which swapped the files: the cover is now `1.jpg`. The settings image has since been renamed `2.jpg`.
- [x] Settings image (`2.jpg`): the settings at their defaults with each group explained beside them, drawn by `tools/make_gallery.py` from shot 08:24:13 (30 Oct 2026, kept in `art/gallery/`). The same capture replaces `docs/images/mod-settings-dialog.png` in `docs/changing-settings.md`.
- [ ] A third image: a line window with the Stale Cargo banner, taken in 1.2 (text "below the mod's stale freshness setting"); add the [L] line manager with the icon on that line's row if it fits in one frame.
- [ ] Recheck the mod.io page: clicking the second thumbnail did not show the settings image right after the 1.3 upload (30 Oct 2026), although the image itself loads ([Gallery](docs/publishing.md#gallery)). The next upload carries it as `2.jpg`, which may fix it.
- [ ] At the next upload, check in the dialog that `2.jpg` (the settings image) joins the gallery after `1.jpg`, and whether the dialog writes a `workshop_preview.jpg` of its own; if it does, keep or delete it as the dialog's order needs ([Gallery](docs/publishing.md#gallery)).

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
