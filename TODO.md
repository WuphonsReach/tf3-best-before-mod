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
- [x] Another cutoff: at 40 min fuel (37.5 min) is perishable and back on the curve (1974, No effect).
- [ ] Reply on issue #27 (closed by the merge, no reply posted yet).
