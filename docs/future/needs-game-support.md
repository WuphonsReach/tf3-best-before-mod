# Needs support from the game

Things we cannot do cleanly with what a mod can reach today. If the game ever offers one of these, the mod gets simpler or more accurate. Nothing here is a request to anyone; it is a record of where the limit is.

- **Freshness as an input to pay.** If the income function received the unit (or its age and quality), the mod could change the pay itself: no correcting bookings, line and vehicle panels would be right, and the 0.96426 factor and the straight-line prediction would not need copying into the mod.
- **A per-unit hook before pay is booked.** The arrival event fires at the final delivery and the mod books a correction a tick later. A hook that could scale the pay of that unit would remove the window in which the full pay shows first.
- **The pay split, or the ledgers it goes to.** Journal entries carry no vehicle or line, and the game shares a delivered unit's pay along its chain by a formula we cannot see. To put a deduction where the pay went we would need the formula, or an event that lists the shares paid.
- **The game's own age for a unit.** `isGoodQuality` is exposed but the age behind it is not. For cargo that sat in a warehouse our age (now minus `pickupTime`) disagrees with the game's flag. An exposed age (or the rule for warehouses and `deliveryExtensionDuration`) would make freshness exact.
- **Sending commands from event handlers.** `sendCommand` is refused inside `handleEvent`, so deductions are queued and sent from `update`, and results can not be waited for from there either.
- **In-game settings for the curve.** We want the five curve settings changeable in the game's mod settings (`mod.json` `params` and `options`, not yet read). If the settings reach the script only at load, changing them would need a reload.
