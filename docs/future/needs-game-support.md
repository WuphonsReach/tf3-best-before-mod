# Needs support from the game

## In short

Four limits where the mod works around what the game exposes: freshness is not an input to pay, the pay split is not visible, the game's own age for a unit is not exposed, and commands cannot be sent from event handlers. None of them blocks the mod today. The per-unit hook before pay that this list once asked for exists (the ticket price event) and is how the mod has paid since 1.2 ([line-billing.md](line-billing.md)), so the pay split no longer matters for pay, and the command limit only for the Stale Cargo warnings.

This is a record of where the limits are, not a request to anyone. If the game ever offers one of these, the mod gets simpler or more accurate.

- **Freshness as an input to pay.** If the income function received the unit (or its age and quality), the mod could set the pay in one place. The ticket price event already lets it scale each unit's pay. What would still go is the straight-line pay prediction and the pay scale the mod copies to estimate each adjustment in money for the log.
- **The pay split, or the ledgers it goes to.** Journal entries carry no vehicle or line, and the game shares a delivered unit's pay along its chain by a formula we cannot see. Ticket billing does not need it, since the engine shares the answered pay itself; the formula would only explain the per-ledger figures the log records at `full`.
- **The game's own age for a unit.** `isGoodQuality` is exposed, but the age behind it is not. The mod's corrected age (now minus `pickupTime`, less `deliveryExtensionDuration`) agrees with the game's flag on all but 7 of 69,907 units on one save ([delivery-limit-tests.md](delivery-limit-tests.md)), but what `deliveryExtensionDuration` equals exactly, and how a universal warehouse counts, are inferred. An exposed age would make freshness exact.
- **Sending commands from event handlers.** `sendCommand` is refused inside `handleEvent`, and a result cannot be waited for from `update` either. So the Stale Cargo warnings are sent from `update`.
