# Needs support from the game

## In short

Four limits where the mod works around what the game exposes: freshness is not an input to pay, the pay split is not visible, the game's own age for a unit is not exposed, and commands cannot be sent from event handlers. A fifth, a per-unit hook before pay, turned out to exist (the ticket price event) and is how the mod pays from 1.2, so the split and the commands now matter only for the `bookings` fallback. Nothing here blocks the mod today.

Things we cannot do cleanly with what a mod can reach today. If the game ever offers one of these, the mod gets simpler or more accurate. Nothing here is a request to anyone; it is a record of where the limit is.

- **Freshness as an input to pay.** If the income function received the unit (or its age and quality), the mod could change the pay itself, in one place. The ticket price event (next item) already does this per unit; what would still go is the straight-line prediction and the pay scale the mod copies to estimate each unit's adjustment for the log.
- **A per-unit hook before pay is booked: found.** The engine raises `OnCalcTicketPrice` for each delivered unit before it pays, and an answer scales the unit's whole pay before the game shares it along the chain. The mod pays this way from 1.2 ([line-billing.md](line-billing.md)). Only the `bookings` fallback still books a correction a tick after the arrival event.
- **The pay split, or the ledgers it goes to.** Journal entries carry no vehicle or line, and the game shares a delivered unit's pay along its chain by a formula we cannot see. Ticket billing does not need it. For the `bookings` fallback to put a deduction where the pay went we would need the formula, or an event that lists the shares paid.
- **The game's own age for a unit.** `isGoodQuality` is exposed but the age behind it is not. For cargo that sat in a warehouse our age (now minus `pickupTime`) disagrees with the game's flag. An exposed age (or the rule for warehouses and `deliveryExtensionDuration`) would make freshness exact.
- **Sending commands from event handlers.** `sendCommand` is refused inside `handleEvent`, so the `bookings` fallback queues its deductions and sends them from `update` (the Stale Cargo warnings are sent from `update` too), and results can not be waited for from there either.
