-- Freshness curve defaults. The curve is set in game: New Game (or Load Game) > Mods > the mod's gear > Settings, and the game keeps
-- those values in the save, and the game gives a save that lacks them the defaults from mod.json. So the curve numbers here are
-- only the last resort for when the game hands the mod no settings at all, and the numbers tools/replay_curve.py starts from;
-- keep them equal to the defaults in mod.json. Editing them does not change a normal game. The log line BEST_BEFORE
-- curveSettings says which source was used (params or settings.tl); the BEST_BEFORE settings line from mod.script.tl runs one
-- load behind, so trust curveSettings (written when the curve changes) and loadParams (the in-game settings of every load). logLevel is not an in-game setting and is read from this file on each load, no restart needed.
-- tools/replay_curve.py reads the same numbers (keep one "name = value," per line) to show the effect on logged runs.
--
-- Pay changes with the unit's freshness (1 = just picked up, 0 = at the delivery limit, negative = past it):
--   at or above bonusDownToFreshness                        +bonusPercent
--   bonusDownToFreshness down to breakevenFreshness         straight line from +bonusPercent to 0 (full pay at breakevenFreshness)
--   breakevenFreshness down to penaltyBelowFreshness        straight line from 0 to penaltyPercent
--   below penaltyBelowFreshness and for spoiled units       penaltyPercent
-- The two percent settings are fractions of the unit's pay: bonusPercent 0.5 is +50%, penaltyPercent -0.95 is -95%.
-- bonusPercent runs from 0 to 2 (up to +200%, a unit paying 3x in the full bonus window), penaltyPercent from -1 to 0
-- (-1 takes the whole pay); the mod clamps values outside those ranges. Keep
-- 1 >= bonusDownToFreshness >= breakevenFreshness >= penaltyBelowFreshness >= 0 (the mod clamps these into that order).
-- A unit never pays less than nothing. Set bonusPercent = 0 for deductions only,
-- penaltyPercent = 0 for bonuses only.
--
-- Non-perishable cargo: a cargo type whose file time (timeToDeliverInSeconds, the base delivery time) is at least
-- nonPerishableMinutes counts as non-perishable, and nonPerishable says how the curve pays it: "full" (the whole curve, as
-- perishable cargo), "halfBonus" (the curve with its bonus halved, penalties in full), "noBonus" (the curve capped at normal
-- pay, so penalties only) or "noEffect" (no answer, normal game pay).
-- The stale line warnings count it either way. In-game settings "Non-perishable cargo" (default Half bonus) and
-- "Non-perishable delivery time" (15 to 75 min, default 25 min, so only food is perishable); these are only their fallback,
-- keep them equal to the mod.json defaults.
--
-- logLevel: how much the mod writes to the game log (every line starts with BEST_BEFORE). Any other value counts as "summary".
--   "off"      the start-up lines only (settings.tl's numbers, the in-game settings as list positions, a warning for an unknown logLevel)
--   "summary"  plus a totals line about once a game month (units delivered, pay taken away, bonus paid), the curve in force, the
--              company's rank and pay scale when they change, the first sighting of each cargo type, and stale warnings that come or go
--   "curve"    plus a line for every delivered unit with what the curve replay needs (age, limit, predicted pay, adjustment),
--              every adjustment sent and every balance change; no vehicle or line names, chains or per-vehicle ledgers
--   "full"     plus those names, chains and ledgers, for studying how the pay splits along a chain; the biggest log
--              (tens of MB in a long session) and the slowest. tools/verify_run.py and tools/extract_run.py read "curve" and "full".
--
-- Stale line warnings: a line whose deliveries are mostly stale gets a "Stale Cargo" warning (in the notification log and on
-- the line in Line & Vehicle Management). A delivered unit is stale when its freshness is below the in-game setting "Warn on cargo
-- below freshness percent" (0% to 25%, default 10%; staleBelowFreshness here is only its fallback, keep it equal to the mod.json
-- default), or when the game flags it spoiled. It counts for the line of its last leg. Each line keeps staleMonths monthly buckets (one game month each, a new line starts with all of them
-- at 0% stale); a month whose deliveries reach staleMinUnits gets that month's stale share, a month with fewer inherits the
-- previous bucket's share and its deliveries carry into the next month. Once a month the average of the buckets is compared:
-- above staleWarnAbove the line is warned, below staleClearBelow the warning goes, in between nothing changes. A line whose
-- stops change (or that is deleted) starts over. The in-game setting "Show Stale Cargo warnings" (on by default) turns them
-- off: the warnings shown are taken down and the history is forgotten. A save that holds a warning does not load without the
-- mod, so a player removing it unticks this first, loads and saves. staleWarnings here is only its fallback, keep it equal
-- to the mod.json default.
--
-- incomeLogging (test only): true makes the mod replace the game's cargo income function with a copy of the base formula that
-- logs its first 400 calls (BEST_BEFORE income call lines, pay unchanged). Only one mod can replace that function, so it
-- conflicts with any other mod that does; false (shipped) leaves it to the game. It is read when the game loads the mod's
-- scripts, so restart the game after changing it.
--
-- ticketPriceProbe (test only): "off" (shipped) answers the game's ticket price event for each delivered unit with its pay
-- multiplier (1 + the curve's adjustment), so the game pays the changed amount and shares it along the unit's chain.
-- "observe" logs every cargo item the event names and answers nothing, so the game pays in full; "scale" answers
-- ticketPriceMultiplier for every cargo item (1 leaves the pay as it is). Read on each load like logLevel. The event's
-- lines are logged at "curve" and "full" only.
return {
	staleWarnings = true,
	staleBelowFreshness = 0.1,
	staleMonths = 12,
	staleMinUnits = 10,
	staleWarnAbove = 0.5,
	staleClearBelow = 0.25,
	logLevel = "summary",
	incomeLogging = false,
	bonusPercent = 0.2,
	bonusDownToFreshness = 0.4,
	breakevenFreshness = 0.2,
	penaltyBelowFreshness = 0.0,
	penaltyPercent = -1.0,
	nonPerishable = "halfBonus",
	nonPerishableMinutes = 25,
	ticketPriceProbe = "off",
	ticketPriceMultiplier = 1.0,
}
