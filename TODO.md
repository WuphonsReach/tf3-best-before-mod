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

- [x] Check that the uploader takes `1.jpg` into the gallery: it does, ordered by file name before `workshop_preview.jpg` (1.3 upload, 30 Oct 2026; [Gallery](docs/publishing.md#gallery)). The settings image came first, so the thumbnails were moved in the dialog, which swapped the files: the cover is now `1.jpg`, the settings image `workshop_preview.jpg`.
- [x] Settings image (now `workshop_preview.jpg`): the settings at their defaults with each group explained beside them, drawn by `tools/make_gallery.py` from shot 08:24:13 (30 Oct 2026, kept in `art/gallery/`). The same capture replaces `docs/images/mod-settings-dialog.png` in `docs/changing-settings.md`.
- [ ] A third image: a line window with the Stale Cargo banner, taken in 1.2 (text "below the mod's stale freshness setting"); add the [L] line manager with the icon on that line's row if it fits in one frame.
- [ ] Recheck the mod.io page: clicking the second thumbnail did not show the settings image right after the 1.3 upload (30 Oct 2026), although the image itself loads ([Gallery](docs/publishing.md#gallery)). If it still fails, rename to `0.jpg`/`1.jpg`/`2.jpg` without `workshop_preview.jpg`, as Industry Upgrades does, and re-upload.
- [ ] Whether a `2.jpg` joins the gallery, and where it sorts (needed for the third image).
