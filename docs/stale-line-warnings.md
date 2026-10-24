# Stale line warnings

## In short

- **What it does.** A line whose deliveries are mostly stale gets a "Stale Cargo" warning from the game's own notification system. The warning shows as a pop-up icon, in the notification log and as an icon on the line in the [L] Line & Vehicle Management window; clicking it opens the line. It is a Caution, and players can filter it out in the notification log ("Stale Cargo (Best Before)"). It does not show in the F2 line statistics list: that list's Problems column shows only the game's "Problem" type, and we chose Caution on purpose (a stale line is a pay issue, not a fault).
- **The rule.** A delivered unit is stale when its freshness is below the in-game setting "Warn on cargo below freshness percent" (0% to 25% in 5% steps, default 10%; 0% counts only spoiled cargo), or when the game flags it spoiled. The rule is about freshness, not pay, and does not move with the pay curve's settings. The setting is new in 1.2-dev and not yet checked in the game. It counts for the line of its last leg. Each line keeps 12 monthly buckets. Once a game month the mod compares their average: above 50% the line is warned, below 25% the warning goes, in between nothing changes. A line has to be bad for about 7 clock months before it warns, and needs about 10 good ones to clear. A clock month is one twelfth of a game clock year (121,750 units), not a calendar month: the save's calendar speed stretches or shrinks it on screen (at 0.25x it is about 7.6 calendar days, so 7 clock months are about 7.5 calendar weeks; at 1x it is a calendar month; at 4x about 4 calendar months). The rule runs on game time because cargo spoils on game time. The game's own periods also run on the clock: the Finances tab's yearly and quarterly columns and the line statistics' monthly figures are clock periods (reported by the player; the journal's time is the clock, see [findings.md](findings.md)).
- **Lines that change.** A new line starts with 12 buckets at 0% stale. A month without deliveries inherits the previous bucket's share. A month with fewer than 10 deliveries also inherits, and those deliveries carry over into the next month until there are 10. A line whose stops change, or whose entity is replaced, starts over; a deleted line is dropped and loses its warning. Adding or removing vehicles keeps the history.
- **How sure we are.** Sure: the game registers the type, the warning comes up after 7 game months of stale deliveries, in the pop-up, the notification log and the [L] manager, with the line's name, and a click opens the line; it clears again once the line recovers, and comes back when the line goes stale again (the same line, warned at month 130, cleared at 204 after a tunnel shortened the route, warned again at 249 after the loaded leg was lengthened; `tools/verify_run.py` passes on every run). When a line lands only just below the stale threshold, the warn takes longer: with 56% of units stale it needed about 10 clock months. Not yet seen in the game: a line's stops being edited, the notification log's filter.
- **Unknown.** Whether editing a line's *stops* changes its revision number (the log says which check fired). One test so far, with a waypoint and not a stop: no reset (see the end). Why two lines of the big save were reset for `reason=route` with nobody editing anything (a reset now logs the old and new stops, so the next one shows what moved). What the extra game script state costs on a big save: no difference was visible in one pair of runs (see the end), which is not proof of none.
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

The threshold is an in-game setting, `bestBefore.staleBelow` in `mod.json` (Mods tab, the mod's gear; kept in the save and read on every update like the curve, see [changing-settings.md](changing-settings.md)). It is logged in `curveSettings` as `staleBelowFreshness` and in `loadParams` as the list position `staleBelow` (1 = 0%, 3 = 10%). The other settings are in `settings.tl` (not in-game settings), read on each load:

| Setting | Default | Meaning |
|---|---|---|
| `staleWarnings` | `true` | `false` removes the warnings shown and forgets the history |
| `staleBelowFreshness` | `0.1` | only the fallback for the in-game threshold, used when the game hands the mod no settings; keep it equal to the `mod.json` default |
| `staleMonths` | `12` | buckets per line (a change keeps the newest, or adds defaults in front) |
| `staleMinUnits` | `10` | deliveries a month needs to be measured |
| `staleWarnAbove` | `0.5` | warn when the average share is above this |
| `staleClearBelow` | `0.25` | clear when it is below this |

Log lines (all start with `BEST_BEFORE`):

| Line | When | Level |
|---|---|---|
| `staleRoll` | once a game month, with the thresholds in force: `staleBelow` (the freshness a unit has to fall below to count as stale, from the in-game setting) | `curve`, `full` |
| `staleLine decision=new` | a line's first delivery | `curve`, `full` |
| `staleLine decision=hold\|warn\|clear\|reset\|gone` | each line at each roll, with its share, buckets (`m0.2500,i0.2500,...`) and carried counters; `reset` gives `reason=route`, `revision` or `revision+route` and the old and new revision and stops (`oldRev`, `newRev`, `oldRoute`, `newRoute`, each stop as `stationGroup:station:terminal`); the line name at `full` | every roll at `curve` and `full`; at `summary` a warning that comes or goes, and a reset |
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

- This save plays on its own in-game curve (the save's state: +25% bonus down to 50% freshness, break-even 30%, -100% below 0%), not the defaults, so the stale threshold here was 0.5 x 30% = 15% freshness, not 10% (the threshold was then half the break-even; it is now its own setting). Lines at 25% to 33% freshness pay less (down to 79% of base) but are not stale. A line has to deliver below 15%, or spoiled cargo, to warn. The log's `BEST_BEFORE settings` line (labelled "settings.tl; its curve is only the fallback" since this run) prints the `settings.tl` numbers (break-even 0.2), not the curve in force. The curve in force is in the `loadParams` line and the `curveSettings` lines, in the save's `probe.gs` state (`curve`), and each `staleRoll` line carries `staleBelow` (the stale threshold in force, not the pay curve).
- Line 221500 (SHE Crops 1): first delivery at month 123, then 5 measured months at 100% stale and 2 inherited (a month without deliveries). Shares 8%, 17%, 25%, 33%, 42%, 50% (all `hold`), then 58.3% at month 130 (`decision=warn`, one `staleWarnings` send with `count=1`). No repeat pop-up followed.
- **What the player sees (screenshots, 7).** A yellow pop-up icon at the top of the screen with the tooltip "Stale Cargo". Clicking the notification opens the line's window with the warning as a banner at the top. The notification log's History tab lists it with a Caution bar. The [L] line manager shows the icon at the right of the line's row.
- **The F2 line statistics list shows nothing.** Its "!" Problems column (`statistics_react_util.tl`, `getSortedProblemIds`) keeps only notifications of the "Problem" type; the game's own line warnings are all "Problem". The [L] manager does not filter by type. Keeping Caution means no F2 icon.
- **The warning text changes only after a game restart.** The first text (about 270 characters) was cut off in the notification log's row after "a shorter route or less…". It was shortened at about 21:25 local, and the game showed the shorter text only after a restart (the log's `Application startup` at 01:26:33Z; the earlier copy of the log was overwritten then). A second edit ("for a long time" instead of "for months", then the last sentence dropped) made while the game ran was not shown until the next restart either: screenshots from 22:01 to 22:04 (Apr 4 to May 17 1903, same session, no restart in between) still show "for months ... Faster delivery would help" in the notification log, the line window banner and the tooltip; after a restart at 22:07:28 (log `Application startup` 02:07:28Z) and a load of the saved game, both show the new text. So a text change needs a restart, not just a save load. The final text ("Most cargo delivered by "SHE Crops 1" has arrived stale for a long time (below half the break-even freshness, or spoiled), so it pays less.", 139 characters) fits two lines in the notification log's Active tab (the row also shows its date on hover: "Sep 17, 1902") and three in the line window banner.
- **A warning survives a restart and a save load.** The saved game ("…2206 waiting for message clear", made after the warning came up) holds the notification (id 136, line 221500, dismissed, tracked, persisting, `param = 1` and no text: the words are drawn from the script each time) and the mod's `probe.gs` state with the five lines' rings (`staleLines`), `staleMonth` 164 and `staleSent = "221500"`. After the restart the warning is in the notification log's Active tab and in the line window. The earlier restart at 01:26Z (`Application startup` 01:26:33Z) loaded an autosave from 1902-05-23, before line 221500 had delivered anything: the line started again as `decision=new` and the same monthly shares came out (8%, 17%, 25%, 33%, 42%, 50%, 58.3%), with the warning at month 130 again (`staleWarnings count=1`). So the rule gives the same result from the same deliveries.
- **The deductions show in the world.** Each spoiled unit's deduction floats as a red number over the building that took it (details in [findings.md](findings.md)).

### Timeline of the warning (screenshots against the log)

The save's calendar runs at 0.25x. Line 221500's first delivery into Sherman was at 01:32:55Z (Jul 27, 1902; "Time to Celebrate!" pop-up for Sherman, first red figures over the buildings). All 80 units (about $991,000 deducted, all flagged spoiled) arrived by 01:36:02Z. The warning was logged at 01:37:04Z; the pop-up icon was on screen at Sep 18, 1902 (not yet on Sep 9). That is 843,600 clock units, or 0.577 of a clock year, which at 0.25x is 53 calendar days (Jul 27 to about Sep 17). The 1.0 and 4x numbers in the In short follow from the same ratio.
- **DMG trucks on SHE Crops 1 (screenshots 22:02 to 22:04, Apr to May 1903).** Eight "DMG Cannstatt" trucks (Road Vehicle 73 to 80, "1 month" old at May 17) replaced the old vehicles on the line, which shows 25 km/h as the speed in the vehicle window (15 km/h in one frame, while turning). The line window showed utilization 15%, frequency 7 min 43 s, rate 19, balance $100,275, with the yellow "Stale Cargo" icon still on the line in the [L] manager. The first deliveries after the swap (after a restart, log `local/logs/stdout-20261018-dmg.txt`, 02:17:57Z to 02:18:10Z, Aug 1903): 6 units arrived at 13.9% to 17.4% freshness (age 1.39 to 1.45 million ms against a 1.6875 million limit), which pays 46% to 58% of base, and 3 of the 6 were below the 15% stale threshold (`breakeven=0.3 staleBelow=0.15` in the `staleRoll` lines). The line's monthly rolls stayed at share 1.0 (month 172: 2 units, 2 stale; month 173: 8 units, 5 stale) and the warning stayed. The old trucks put the line at about -37% (spoiled); these first six were the best sample, not a trend (see the 90-unit read below). For the warning to clear, the 12-month average has to fall below 25%, so a line that is stale half the time never clears: it needs about three quarters of its units above 15%.
- **The vehicle window shows the cargo's freshness as a bar (probably).** Road Vehicle 79 on the new run shows a clock icon and a blue bar beside the load that falls from 64% (Jun 16 1903) to 44% (Jul 7), 20% (Aug 1) and 16% (Aug 5, unloading), the last matching the log's 13.9% to 17.4% for the units that arrived at that moment. A player can read a unit's freshness there before it arrives.
- **The session before 01:26Z is gone from the log.** The first warning came at month 130 in a session whose log (00:35 to 01:26Z) was overwritten by the restart; its figures above (81 monthly rolls, the Sherman timeline and the verifier result) were taken before that.

### SHE Crops 1 after 90 units (log `local/logs/stdout-20261018-dmg.txt`, restart at 02:12Z, to clock 23.1M; screenshots to Dec 1 1903)

90 units, 66 stale (below 15% or spoiled). By pickup time (clock, in bands of 200,000):

| Pickup band | Units | Mean age (ms) | Mean freshness | Stale |
|---|---|---|---|---|
| 19.4M | 6 | 1,429,000 | 15.3% | 3 |
| 20.0M | 6 | 1,429,000 | 15.3% | 3 |
| 20.2M | 12 | 1,437,000 | 14.9% | 5 |
| 20.4M | 6 | 1,431,000 | 15.2% | 2 |
| 20.6M | 24 | 1,497,000 | 11.3% | 17 |
| 20.8M | 24 | 1,756,000 | -4.1% | 24 |
| 21.4M | 12 | 1,490,000 | 11.7% | 12 |

- **It did not improve with time.** Cargo picked up before about 20.6M arrived near the threshold (15%); from 20.6M on it was staler, and the 20.8M units were all spoiled (age above the 1,687,500 limit, pay 0%). The `staleLine` share went 0.66 (months 183 to 188, history from the old trucks and the first DMG months) to 0.70 (month 189) and 0.73 (month 190), with 8 or 9 of 8 or 9 units stale in each measured month. The warning stayed.
- **Why it got worse is not known.** At Dec 1 1903 the line has 17 vehicles (it had 8 in May), utilization 28%, frequency 2 min 56 s, rate 50. More trucks may mean more waiting at the farm; the log has no vehicle or waiting time, so this is a guess.
- **A tunnel was added (the player, Dec 1 1903, paused at about clock 22.9M).** The route (green dashed line in the screenshots) now runs through the tunnel and back to the main road, cutting the V. Units picked up after that clock are the first to show it; units picked up earlier are not the comparison. They take about 1.4 million clock units (about 6 minutes at 4x) to arrive.
- **The tunnel worked (log to 02:31Z, clock 23.1M; screenshots to Jan 27 1904).** Units picked up after the tunnel (from clock 22.8M) arrived at a mean age of 0.83 to 0.88 million ms against 1.43 million for the units picked up just before (band 22.4M): freshness 48% to 51% instead of 13% to 16%, which pays 123% to 124% (the curve's bonus at 50% freshness and above) instead of 44% to 54%. Ten units so far, two batches (clock 22.8M and 23.0M). The age fell by 42%, more than a route cut alone would obviously give, so part of it may be fewer trucks waiting; the log cannot say.
- **The warning cleared in the game, at month 204, as predicted.** Log `local/logs/stdout-20261018-dmg.txt`: shares 0.88 (month 195), 0.76, 0.68, 0.60, 0.52, 0.43 (201), then month 204 `decision=clear line=221500 share=0.2107 warned=false` and `staleWarnings count=0 lines=none` at 02:35:00Z; `verify_run.py` passes with 0 lines warned (40 monthly rolls, 195 bucket rolls rebuilt, 169 units for the line). The prediction (7 more good months to 0.255, an 8th to 0.20, clear at month 204) was made from the buckets at month 196. The screenshots show it from the player's side: at Mar 1 and Mar 21 1904 the line window still carries the yellow banner and the notification log's Active tab still lists the warning; at Apr 3 1904 (02:35:05Z, five seconds after the clear) the banner is gone, the row is gone from the Active tab and the pop-up icon is off the top bar. Units after the tunnel (clock 22.8M and later, 100+ units): freshness 47% to 51%, pay 121% to 125%, none stale.
- **The notification log's coloured bar is the pop-up switch.** The bar at the left of each row is coloured while the pop-up shows and dark when it is hidden; the tooltip reads "Hide Notification Pop-Up" or "Show Notification Pop-Up". A row stays in the Active tab with the bar dark, as the saved entry's dismissed flag (D) says. Hiding the pop-up does not clear the warning; toggling it back raised our icon again at the top left, once.
- **The old arrival's age had two parts we cannot separate in the log:** the time a unit waits at the pickup for the load to finish, and the drive. The tunnel only shortens the drive.

### A waypoint added to the line (screenshots 22:35 to 22:37, Apr 30 to May 6 1904)

The player added a waypoint (the line's list shows it as row 3, below the two stops Sherman Crop Farm and Sherman Station) to force one leg back onto the old road. The line window afterwards shows frequency 3 min 5 s (it was 124 to 130 s) and rate 47 (it was 70 to 71), so the new route was in force by 02:37:16Z.

- **No reset.** The monthly rolls at months 209 (02:37:33Z) and 210 (02:38:05Z) both came after the edit and logged `decision=hold` for line 221500, with the same buckets shifting along (`share=0.0064`, then `0.0000`). A reset would have logged `decision=reset reason=revision` or `reason=route`. So adding a waypoint changed neither the line's revision number (`api.engine.getRevision(line).num[1]`) nor the stop list the mod compares (`stationGroup:station:terminal` per entry of the line component's `stops`), at least within these two rolls. That fits a waypoint not being one of `stops`; it does not say what happens when a stop is added, moved or removed. A stop edit is still untested, and the revision was not read directly (the rolls only compare it).
- **The history carries on.** The line's stale share stays at 0.0 with the 12 buckets of its recent good months, so a longer route is judged by what it delivers, not by a reset. If the waypoint pushes the cargo back towards stale, the first sign is in the `arrival` lines (freshness falling below the stale threshold) and it takes about 7 clock months for the share to reach the warn threshold again.
- **Freshness before the edit was already slipping.** Units picked up before the edit (clock 24.2M to 24.5M, arriving 02:37:32Z to 02:38:01Z) had freshness 28% to 42% (age 0.98 to 1.22 million ms), against 47% to 51% right after the tunnel. The edit cannot explain that.

### The warning came back after the loaded leg was lengthened (log `local/logs/stdout-20261018-warn-again.txt`, to clock 32.9M; screenshots 22:45 to 23:09, Aug 27 1904 to Aug 15 1905)

The waypoint above sat on the return leg, which carries no cargo (a dead-head leg), so it changed nothing for freshness: units picked up to about clock 27.4M arrived at 48% to 53% (12 units, age 0.79 to 0.87 million ms). The player then sent the loaded leg, farm to Sherman Station, over the long road. Road Vehicle 74 was the last truck to load on the short route (cargo bar 74%, 64%, 56%, then 51% at unloading, Oct 6 to Oct 29 1904); Road Vehicle 88 was the first on the long route (21% on the road, 15% at unloading, Dec 6 to Dec 12 1904). Both bars fall about 1 point per game day; the long route took about 36 game days longer.

- **The long route puts the line at the edge of stale.** 204 units picked up from clock 27.45M on, all on line 221500: age 1.39 to 1.57 million ms (mean 1.45), freshness 6.9% to 17.7%, 115 of them below the 15% threshold (56%). The first stale arrival was at clock 28,916,000 (02:52:44Z), the one RV88 unloads in the Dec 12 screenshot. The stale share did not climb with time inside the 204: 37 of 66 for pickups before clock 28.5M, 78 of 138 after.
- **The warning returned at month 249.** `decision=warn line=221500 share=0.5564 warned=true units=7 stale=7` at 02:58:37Z (clock 30,315,800), 10 clock months after the first month with stale units (month 239); it was predicted from the first two months as about 10 more months, and the log agrees. The shares before it: 0.048 (239), 0.086, 0.125, 0.161, 0.198, 0.230, 0.262 (245), 0.326, 0.390 (247), 0.473 (248), 0.556 (249), then 0.616 at month 250 with `hold`. Each measured month had 6 to 8 units with 3 or 4 stale until months 247 and 249, where all 8 and all 7 were stale; that jump is what carried the average over 0.5. Months in between inherit (fewer than 10 units, carried over).
- **The player's screenshot at 23:09 (Aug 15 1905)** shows the warning in the notification log's Active tab dated Mar 10 1905, and as the banner in the SHE Crops 1 window ("Most cargo delivered by "SHE Crops 1" has arrived stale for a long time (below half the break-even freshness, or spoiled), so it pays less."), with the yellow pop-up icon among those at the top. This is the second time the warning came up for this line, after the first clear at month 204; the first one's pop-up and banner behaved the same way.
- **Warn, clear and warn again works on one line.** The line's history carried through the clear without a reset, and no edit of the line's stops was involved. `verify_run.py` passes (no error lines, 2,758 units adjusted, 106 monthly rolls, 525 bucket rolls rebuilt, 1 line warned at the end).

### A big save: 333 lines, 1,249 vehicles (log `local/logs/stdout-20261018-bigsave2.txt`, loaded 03:11:51Z; screenshots 23:11 to 23:22)

Save "333 20261017 1646 with mod" (230 MB, Jan 4 2001, Vice President, Best Before the only mod). Its own curve: break-even 25%, so the stale threshold is 12.5%. The save held no stale history, so every line started empty at the load (clock 147.5M, month 1212). The game runs fast here: one clock month rolls about every 65 to 75 s of real time.

- **The warning worked.** Line 225750 ("Dagenham - Plastic") first showed a stale month at month 1213 and warned at month 1219 (`decision=warn share=0.5375`, 03:20:45Z): six measured months at 100% stale, one at 45%, 7 rolls after its first month, as the 7-month rule says. The 23:22 screenshot shows it in the notification log's Active tab dated Aug 2 2001 ("Most cargo delivered by "Dagenham - Plastic" has arrived stale for a long time ..."), at the top of a list of about 15 of the game's own noise notifications, and its icon at the right end of the top bar. 129 lines were tracked by then; the others did not warn.
- **What made those units stale.** Arrivals on this line carry about 4.0M to 4.5M ms of delivery extension (stored cargo) against an age of 5.3M to 6.0M and a limit of 2.25M. The corrected freshness is 0.32 to 0.45, above the 12.5% threshold, yet about half the units are flagged `staleUnit=true`: those are the ones the game marks `good=false` (spoiled), pay rate 0.15 and a deduction of 19,908 on a predicted 23,421. The units flagged `good=true` at similar corrected freshness (0.42 to 0.45) get a bonus of 4,700 to 5,400. So on this line the spoiled flag, not the corrected freshness, decides what counts as stale.
- **Two lines were reset for `reason=route` with no edit.** Line 116488 at month 1214 and line 96613 at month 1217 (`decision=reset reason=route`; the revision number had not moved). The player did not edit anything. The check compares `stationGroup:station:terminal` for each stop, so a stop's terminal or station changed under the game's own hand (or the stop list is read differently early on); the log did not say which, because it recorded neither the old nor the new stops (it now does: `oldRoute` and `newRoute` on the `reset` line, needs a game restart). 2 of 129 lines in 7 months; each reset throws away that line's history, so a line that was heading for a warning would lose it.
- **No errors.** `verify_run.py` passes (5,562 units adjusted and sent, five carriers, 129 lines tracked). Its landing check is 15% on this save (it needs 40%, and counts exact hits against shifted ones, 485 to 0): a busy save moves the balance by more than our bookings.
- **CPU, warnings on against off (same save, same game dates).** `tools/cpu_sample.py`, `logLevel = curve` both times, the game's threads sampled every 5 s. Run `bigsaveon1` (warnings on) and run `bigsaveoff1` (`staleWarnings = false`, log with no `staleLine` or `staleRoll` lines), files `local/cpu/bigsave-stale-*.*` (gitignored). Both windows are cut to the same stretch of game clock, 148.21M to 148.47M (2.1 clock months), so each run is read on the same dates of the save:

  | Game threads | on: % of one core | on: CPU s / clock month | off: % of one core | off: CPU s / clock month |
  |---|---|---|---|---|
  | Sim Pool | 236 | 144.6 | 222 | 151.0 |
  | Main Pool | 233 | 142.3 | 265 | 180.0 |
  | Main Thread | 122 | 74.6 | 114 | 77.4 |
  | all sampled threads | 595 | 364 | 613 | 417 |

  The warnings-on run is not heavier in the Sim Pool, where the mod's code runs (144.6 against 151.0 CPU s per month, 4% lower), and not heavier in total (the Main Pool, which is not our code, differs the other way by 38). So with 129 lines tracked the stale-line code is below what two runs can show. How sure: low-to-medium. Each window is only 130 s and 144 s of real time (the tool warns under 5 minutes), there is one run of each, the machine's other load differed a little (busy 43.5% against 48.3%), and the game ran a little faster in the on run (1,990 against 1,790 clock units per second). A run of the whole 7 minutes of the off run (7.2 clock months, 415 CPU s per month, 576% of a core) has no on-run counterpart past clock 148.6M because the on-run's log was overwritten by the restart before it could be copied to the end of its window.
