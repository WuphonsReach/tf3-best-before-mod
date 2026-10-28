# TODO

## Bookings removal (branch 2026-10-28-remove-bookings-billing)

- [x] Test in game: done with the non-perishable No bonus run below (28 Oct 2026, 722 units): every ticket answer equal to its rate, no `sending` lines, `verify_run.py` passed.
- [ ] Decide whether to clear the leftover state of older saves. Saves from 1.2 and earlier keep the unused `pending`, `units` and `batches` entries in the probe's game script state; they do no harm but are never removed. A 1.0.1 save made while a few deductions were still queued loses those few, since nothing sends the queue any more.
- [x] Push and open the PR (merged as #33).

## Non-perishable cargo, issue #27 (branch 2026-10-28-perishables-only)

- [x] Check the dialog: the two new settings show under the mod's gear with their names and defaults (Full bonus, 25 min), and the list offers Full bonus, No bonus, No effect.
- [ ] Check the two tooltips (not in any screenshot yet).
- [x] No bonus in game (save WR26A Giga-Tv3 1900, 722 units): `loadParams nonPerishable=2 nonPerishableTime=3`, `curveSettings nonPerishable=noBonus nonPerishableSeconds=1500`, `verify_run.py` passed; the 454 non-perishable units were paid x1.00 and the food kept its bonus.
- [ ] No bonus on late cargo: a non-perishable unit below break-even must still lose pay (none was late enough in the first run).
- [ ] No effect in game: units at or above the cutoff log `billing=none` and get no ticket answer; `verify_run.py` checks both.
- [ ] A cutoff other than 25 min (for example 50 min, which moves the 37.5 min goods to the perishable side).
- [ ] Read a save header with `save_header.py` to confirm the stored positions (2 for No bonus, 3 for 25 min).
- [x] Old save: the 1900 save, made before the settings existed, showed the defaults in the dialog and kept its own curve.
- [ ] Reply on issue #27 once the PR merges.
