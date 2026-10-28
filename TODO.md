# TODO

## Bookings removal (branch 2026-10-28-remove-bookings-billing)

- [ ] Test in game before pushing: set `logLevel = "curve"` in `settings.tl`, load a save, copy `crash_dump/stdout.txt` to `local/logs/` and run `python3 tools/verify_run.py` on it. Expect every ticket answer to equal its rate and no `sending adjustment` lines. Set `logLevel` back to `"summary"` afterwards (`check_repo.py` fails otherwise).
- [ ] Decide whether to clear the leftover state of older saves. Saves from 1.2 and earlier keep the unused `pending`, `units` and `batches` entries in the probe's game script state; they do no harm but are never removed. A 1.0.1 save made while a few deductions were still queued loses those few, since nothing sends the queue any more.
- [ ] Push and open the PR once the in-game test passes.
