-- Freshness curve settings. Edit the numbers, restart the game and load a save to test them.
-- tools/replay_curve.py reads the same numbers (keep one "name = value," per line) to show the effect on logged runs.
--
-- Pay changes with the unit's freshness (1 = just picked up, 0 = at the delivery limit, negative = past it):
--   at or above bonusFrom    +bonus
--   bonusFrom down to breakeven   straight line from +bonus to 0 (full pay at breakeven)
--   breakeven down to penaltyFrom  straight line from 0 to -penalty
--   below penaltyFrom and for spoiled units   -penalty
-- bonus and penalty are fractions of the unit's pay (0.5 = 50%). Keep 1 >= bonusFrom >= breakeven >= penaltyFrom >= 0.
-- A deduction never takes more than 99% of a unit's pay. Set bonus = 0 for deductions only, penalty = 0 for bonuses only.
--
-- stored: what to do with cargo that waited in a warehouse. A specialized warehouse pauses a unit's spoil timer, so its
-- age overstates how old it is: "corrected" takes the paused time off the age (deliveryExtensionDuration), "formula"
-- uses the plain age, and for a unit the game flags good but whose plain age is past the limit, "zero" counts it as 0%
-- fresh and "neutral" leaves its pay alone (both use the plain age for every other unit).
return {
	bonus = 0.5,
	bonusFrom = 0.5,
	breakeven = 0.3,
	penaltyFrom = 0.0,
	penalty = 0.0,
	stored = "corrected",
}
