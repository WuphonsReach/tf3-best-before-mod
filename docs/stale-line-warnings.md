# Stale line warnings

## In short

- **What it does.** A line whose deliveries are mostly stale gets a "Stale Cargo" warning from the game's own notification system. The warning shows in the notification log and pop-ups, and as an icon on the line in Line & Vehicle Management; clicking it selects the line. It is a Caution, and players can filter it out in the notification log ("Stale Cargo (Best Before)").
- **The rule.** A delivered unit is stale when its freshness is below half the curve's break-even freshness (10% with the default 20% break-even), or when the game flags it spoiled. It counts for the line of its last leg. Each line keeps 12 monthly buckets. Once a game month the mod compares their average: above 50% the line is warned, below 25% the warning goes, in between nothing changes. A line has to be bad for about 7 months before it warns, and needs about 10 good months to clear.
- **Lines that change.** A new line starts with 12 buckets at 0% stale. A month without deliveries inherits the previous bucket's share. A month with fewer than 10 deliveries also inherits, and those deliveries carry over into the next month until there are 10. A line whose stops change, or whose entity is replaced, starts over; a deleted line is dropped and loses its warning. Adding or removing vehicles keeps the history.
- **How sure we are.** The code has only been run outside the game: compiled to Lua and driven through 30 game months with a mocked game API (see the test at the bottom). `tools/verify_run.py` passes that log and catches tampered buckets and sends. **It has not run in the game yet.**
- **Unknown until the first game run.** Whether the game registers a mod's notification type from `stale_line_warning.res.lua`; whether the type path `best_before_1::/stale_line_warning.script` resolves and the icon shows in Line & Vehicle Management; whether editing a line's stops also changes its revision number (the log says which check fired); and what the extra game script state costs on a big save.
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
