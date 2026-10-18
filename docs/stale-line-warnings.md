# Stale line warnings

## In short

- **What it does.** A line whose deliveries are mostly stale gets a "Stale Cargo" warning from the game's own notification system. The warning shows as a pop-up icon, in the notification log and as an icon on the line in the [L] Line & Vehicle Management window; clicking it opens the line. It is a Caution, and players can filter it out in the notification log ("Stale Cargo (Best Before)"). It does not show in the F2 line statistics list: that list's Problems column shows only the game's "Problem" type, and we chose Caution on purpose (a stale line is a pay issue, not a fault).
- **The rule.** A delivered unit is stale when its freshness is below half the curve's break-even freshness (10% with the default 20% break-even), or when the game flags it spoiled. It counts for the line of its last leg. Each line keeps 12 monthly buckets. Once a game month the mod compares their average: above 50% the line is warned, below 25% the warning goes, in between nothing changes. A line has to be bad for about 7 clock months before it warns, and needs about 10 good ones to clear. A clock month is one twelfth of a game clock year (121,750 units), not a calendar month: the save's calendar speed stretches or shrinks it on screen (at 0.25x it is about 7.6 calendar days, so 7 clock months are about 7.5 calendar weeks; at 1x it is a calendar month; at 4x about 4 calendar months). The rule runs on game time because cargo spoils on game time. The game's own periods also run on the clock: the Finances tab's yearly and quarterly columns and the line statistics' monthly figures are clock periods (reported by the player; the journal's time is the clock, see [findings.md](findings.md)).
- **Lines that change.** A new line starts with 12 buckets at 0% stale. A month without deliveries inherits the previous bucket's share. A month with fewer than 10 deliveries also inherits, and those deliveries carry over into the next month until there are 10. A line whose stops change, or whose entity is replaced, starts over; a deleted line is dropped and loses its warning. Adding or removing vehicles keeps the history.
- **How sure we are.** Sure: the game registers the type, the warning comes up after 7 game months of stale deliveries, in the pop-up, the notification log and the [L] manager, with the line's name, and a click opens the line (one game run, 81 monthly rolls, 5 lines, 1 warned; `tools/verify_run.py` passes). Not yet seen in the game: a warning clearing, a line's stops being edited, the notification log's Active tab and filter.
- **Unknown.** Whether editing a line's stops also changes its revision number (the log says which check fired); whether a warning clears in the game as the mocked test says; what the extra game script state costs on a big save.
- **Off switch.** `staleWarnings = false` in `settings.tl` removes any warnings shown and forgets the history (needs a reload, no restart).

## How it works

Three pieces:

- `probe.script.tl`'s `handleEvent` counts each delivered unit for its last leg's line, using the freshness the pay curve judges it on (stored cargo corrected). The first unit for a line starts its history, recording the line's revision number and its stops.
- `probe.script.tl`'s `update` closes a month every 121,750 clock units (a game year is 1,461,000), counted from clock zero rather than by calendar month. It first checks each tracked line, dropping lines that are gone and starting over lines whose stops or revision changed. Then it rolls the buckets, decides warn, clear or hold, and, when the warned set changed, sends that set to the game's Notifications game script with `makeScriptingSendEventCmd("", "Notifications", "updatePersistent", ...)`.
- `stale_line_warning.res.lua` registers the notification type, and `stale_line_warning.script.tl` draws an entry (title, text with the line's name, icon, click).

Why it is built this way:

- **The whole warned set every time.** `updatePersistent` replaces this type's warnings: a line the set no longer lists loses its warning. This is the same mechanism the game uses for its own line problems.
- **No numbers in the warning.** A notification's parameters must stay the same while it is shown: changed parameters make the game drop it and add a new one, which pops up again. So the warning names the line and gives no share; the share is in the log.
- **History in the game script state.** Per line: 12 shares, one letter per bucket for where its value came from, two counters and the warned flag. It is saved with the game.
- **Where a bucket's value came from:** `d` default (0%, never measured), `i` inherited from the bucket before, `m` measured. A bucket that inherits from a default stays `d`.

The settings are in `settings.tl` (not in-game settings), read on each load:

| Setting | Default | Meaning |
|---|---|---|
| `staleWarnings` | `true` | `false` removes the warnings shown and forgets the history |
| `staleShareOfBreakeven` | `0.5` | stale below this share of the break-even freshness |
| `staleMonths` | `12` | buckets per line (a change keeps the newest, or adds defaults in front) |
| `staleMinUnits` | `10` | deliveries a month needs to be measured |
| `staleWarnAbove` | `0.5` | warn when the average share is above this |
| `staleClearBelow` | `0.25` | clear when it is below this |

Log lines (all start with `BEST_BEFORE`):

| Line | When | Level |
|---|---|---|
| `staleRoll` | once a game month, with the thresholds in force | `curve`, `full` |
| `staleLine decision=new` | a line's first delivery | `curve`, `full` |
| `staleLine decision=hold\|warn\|clear\|reset\|gone` | each line at each roll, with its share, buckets (`m0.2500,i0.2500,...`) and carried counters; `reset` gives `reason=route\|revision`; the line name at `full` | every roll at `curve` and `full`; at `summary` only a warning that comes or goes |
| `staleWarnings` | the warned set sent | all but `off` |
| `arrival ... staleLine= staleUnit=` | the line a unit counted for and whether it was stale | `curve`, `full` |

`tools/verify_run.py` replays the buckets between rolls from the arrival lines, and checks each share, each decision and each warned set sent.

## Choosing the rule: replay of logged runs

Four logged runs were replayed per line and month: stale meant below 10% corrected freshness or spoiled, and fewer than 10 units carried into the next month. The aim was to see what a guard requiring 3 measured months in the window would cost.

| Run | Lines | Lines >50% stale | Lines with <3 measured months per 12 | Of those, >50% stale |
|---|---|---|---|---|
| Emerald | 69 | 0 | 23 | 0 |
| QZZZ | 21 | 6 | 0 | 0 |
| 333 | 161 | 5 | 69 | 1 |
| Large (save2) | 29 | 8 | 8 | 2 |

Deliveries arrive in bursts (one train or ship unloads 12 to 140 units), and some lines deliver only every 4 to 8 months. Those slow lines are the ones that spoil, and the guard would have hidden 3 of the 19 mostly stale lines, so it was left out. Inheritance already covers sparse lines: one delivery fills the months up to the next.

## Test outside the game (mocked API)

`probe.script.tl` was compiled with `tl gen --gen-target=5.1` and run under Lua 5.1 and 5.4 by a harness that mocks the game API (entities, revisions, line stops, the game script state copied on every `get` and `set`). It ran 30 game months with an `update` every tenth of a month and deliveries in mid-month. The harness is kept in the gitignored `local/harness/` (run instructions at the top of `harness.lua`).

| Line | Scenario | Result |
|---|---|---|
| A | 20 units a month, all stale; all fresh from month 14 | warned at month 7, cleared at month 24 |
| B | 15 fresh units a month; revision changed in month 12 | never warned; `reset reason=revision` at month 13 |
| C | 100 stale units every 4 months | warned at month 7 (inherited buckets) |
| D | 20 stale units a month; one stop changed in month 9 | warned at 7, `reset reason=route` at 10, warned again at 17 |
| E | 20 stale units a month; deleted in month 10 | warned at 7, `gone` at 11, dropped from the warned set |
| F | 3 stale units a month | measured every 4 months, warned at month 10 |
| G | 20 units a month, 60% stale | warned at month 11 |
| (sold) | units from a line that no longer exists | counted for no line (`staleLine=none`) |

At `curve` the verifier passed all 29 rolls and rebuilt 182 bucket rolls from the arrivals. With one bucket edited, or one line dropped from a send, it failed and named the month and line. `summary`, `full` and `off` ran without errors. Turning the warnings off on a reload sent an empty set and cleared them. The warning script, run with a mocked GUI API, named the line, and its click selected the line (or did nothing once the line was gone).

## Test in the game

Save "WR26A Giga-T 1900 v2 1017 2016" (a 1900 save, the mod new to it, so every line's history started empty), log level `curve`, about 47 minutes of log (00:35 to 01:22 UTC). Log `local/logs/stdout-20261018-0039-stale-warn-start.txt`; `verify_run.py` passed (no error lines, 1,730 units adjusted and sent (the five lines below), 81 monthly rolls, 5 lines tracked, 1 warned, 317 bucket rolls rebuilt from the arrivals).

| Line | Units | Freshness (mean) | Pay (mean, % of base) | Warned |
|---|---|---|---|---|
| 183097 (probably HEM Crops 1) | 384 | 33.1% | 103.8% | no |
| 185051 (probably WIG Crops 1) | 320 | 26.4% | 87.9% | no |
| 191487 | 484 | 56.5% | 125.0% | no |
| 191956 | 462 | 74.6% | 125.0% | no |
| 221500 (SHE Crops 1) | 80 (all flagged spoiled) | -41.6% | 0% | **yes, at month 130** |

- Lines at 20% to 33% freshness pay less (down to 79% of base) but are not stale: the stale threshold is 10% with the default break-even. A line has to deliver at or below that, or spoiled cargo, to warn.
- Line 221500 (SHE Crops 1): first delivery at month 123, then 5 measured months at 100% stale and 2 inherited (a month without deliveries). Shares 8%, 17%, 25%, 33%, 42%, 50% (all `hold`), then 58.3% at month 130 (`decision=warn`, one `staleWarnings` send with `count=1`). No repeat pop-up followed.
- **What the player sees (screenshots, 7).** A yellow pop-up icon at the top of the screen with the tooltip "Stale Cargo". Clicking the notification opens the line's window with the warning as a banner at the top. The notification log's History tab lists it with a Caution bar. The [L] line manager shows the icon at the right of the line's row.
- **The F2 line statistics list shows nothing.** Its "!" Problems column (`statistics_react_util.tl`, `getSortedProblemIds`) keeps only notifications of the "Problem" type; the game's own line warnings are all "Problem". The [L] manager does not filter by type. Keeping Caution means no F2 icon.
- **The first text was too long for the log.** The log's row shows two lines (about 190 characters at most); the first text was about 270 and was cut off after "a shorter route or less…". The shortened text (167 characters, line name in quotes, "has arrived stale for a long time (below half the break-even freshness, or spoiled), so it pays less. Faster delivery would help.") fits the pop-up tooltip (four lines) and the line window banner (three lines); the notification log row with it was not photographed. The script reloads when a save is loaded, so a text change needs no game restart. "For months" became "for a long time" because the warning came after about 7.5 calendar weeks on this save.
- **A reload replays the same history.** At 01:27Z the game loaded an autosave from 1902-05-23, before line 221500 had delivered anything. The line started again as `decision=new` and the same monthly shares came out (8%, 17%, 25%, 33%, 42%, 50%, 58.3%), with the warning at month 130 again (`staleWarnings count=1`). So the rule gives the same result from the same deliveries. This is not a test that the history survives a save and reload: the line did not exist in that autosave.
- **The deductions show in the world.** Each spoiled unit's deduction floats as a red number over the building that took it (details in [findings.md](findings.md)).

### Timeline of the warning (screenshots against the log)

The save's calendar runs at 0.25x. Line 221500's first delivery into Sherman was at 01:32:55Z (Jul 27, 1902; "Time to Celebrate!" pop-up for Sherman, first red figures over the buildings). All 80 units (about $991,000 deducted, all flagged spoiled) arrived by 01:36:02Z. The warning was logged at 01:37:04Z; the pop-up icon was on screen at Sep 18, 1902 (not yet on Sep 9). That is 843,600 clock units, or 0.577 of a clock year, which at 0.25x is 53 calendar days (Jul 27 to about Sep 17). The 1.0 and 4x numbers in the In short follow from the same ratio.
