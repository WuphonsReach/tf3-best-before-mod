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
-- stored: what to do with a unit the game flags good but whose age says it is past the limit (cargo that waited in a
-- warehouse): "formula" keeps the age-based freshness, "zero" counts it as 0% fresh, "neutral" leaves its pay alone.
return {
	bonus = 0.5,
	bonusFrom = 0.5,
	breakeven = 0.3,
	penaltyFrom = 0.0,
	penalty = 0.0,
	stored = "formula",
}
