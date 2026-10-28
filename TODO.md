# TODO

## Bookings removal (branch 2026-10-28-remove-bookings-billing)

- [ ] Test in game before pushing: set `logLevel = "curve"` in `settings.tl`, load a save, copy `crash_dump/stdout.txt` to `local/logs/` and run `python3 tools/verify_run.py` on it. Expect every ticket answer to equal its rate and no `sending adjustment` lines. Set `logLevel` back to `"summary"` afterwards (`check_repo.py` fails otherwise).
- [ ] Decide whether to clear the leftover state of older saves. Saves from 1.2 and earlier keep the unused `pending`, `units` and `batches` entries in the probe's game script state; they do no harm but are never removed. A 1.0.1 save made while a few deductions were still queued loses those few, since nothing sends the queue any more.
- [ ] Push and open the PR once the in-game test passes.

## Non-perishable cargo, issue #27 (branch 2026-10-28-perishables-only)

- [ ] Check the dialog: the two new settings show under the mod's gear with their names, tooltips and defaults (Full bonus, 25 min), and the ComboBox lists Full bonus, No bonus, No effect.
- [ ] Test each mode in game at `logLevel = "curve"` on a save that moves both food and bulk: load with No bonus, then with No effect (and one run at a cutoff other than 25 min). Check that `loadParams` logs `nonPerishable` as 1, 2 or 3 and `nonPerishableTime` as a 1-based slider position, and that `curveSettings` shows the matching `nonPerishable` and `nonPerishableSeconds`. Run `python3 tools/verify_run.py` on each log; it checks every arrival's `perishable` flag, that No bonus never pays over 1 and that No effect units get no ticket answer. Read a save header with `save_header.py` to confirm the stored positions.
- [ ] Load an old save (from before the settings) and check that it shows the defaults and plays as before.
- [ ] Push and open the PR once the in-game tests pass (it closes #27). Reply on the issue.
