-- Freshness curve settings. Edit the numbers, restart the game and load a save to test them.
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
-- A deduction never takes more than 100% of a unit's predicted pay. Set bonusPercent = 0 for deductions only,
-- penaltyPercent = 0 for bonuses only.
--
-- stored: what to do with cargo that waited in a warehouse. A specialized warehouse pauses a unit's spoil timer, so its
-- age overstates how old it is: "corrected" takes the paused time off the age (deliveryExtensionDuration), "formula"
-- uses the plain age, and for a unit the game flags good but whose plain age is past the limit, "zero" counts it as 0%
-- fresh and "neutral" leaves its pay alone (both use the plain age for every other unit).
return {
	bonusPercent = 0.2,
	bonusDownToFreshness = 0.4,
	breakevenFreshness = 0.2,
	penaltyBelowFreshness = 0.0,
	penaltyPercent = -1.0,
	stored = "corrected",
}
