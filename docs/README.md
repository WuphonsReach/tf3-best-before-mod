# Notes

## In short

The mod is public on mod.io as an early test version; [publishing.md](publishing.md) has the listing and how to upload an update. Start with [how-it-works.md](how-it-works.md) for what the mod does and where it can be wrong, then [findings.md](findings.md) for the verified game facts and test results. The `future/` notes hold what was set aside, what the game would need to offer, the open questions, and the test records behind ticket billing and the delivery limit. Each note opens with an "In short" section.

| Note | Covers |
|---|---|
| [changing-settings.md](changing-settings.md) | How a player changes the mod's settings on a new game and on a saved game, with screenshots, and what each setting does |
| [removing-the-mod.md](removing-the-mod.md) | How to take the mod out of a save: clear the Stale Cargo warnings first, with screenshots and the test |
| [how-it-works.md](how-it-works.md) | How the mod turns freshness into a pay multiplier, and where it can over-penalize or miss |
| [stale-line-warnings.md](stale-line-warnings.md) | The "Stale Cargo" warning for lines that mostly deliver stale cargo: the rule, the settings, lines that change, and the tests so far |
| [findings.md](findings.md) | What we have verified in the game: how pay works, cargo units and freshness, what a mod can and cannot do, test results |
| [publishing.md](publishing.md) | The mod.io listing (name, summary, tags, description, mirrored into `modinfo.json`), how to upload an update with the game's uploader, what ships, and what is known about hub search |
| [future/discarded.md](future/discarded.md) | Ideas we tried or weighed and set aside, why, and what would bring them back |
| [future/needs-game-support.md](future/needs-game-support.md) | Things the mod cannot do cleanly with what the game exposes today |
| [future/stored-cargo-modes.md](future/stored-cargo-modes.md) | The other ways of judging cargo that waited in a warehouse, kept in the code but not offered, and ideas for later |
| [future/line-billing.md](future/line-billing.md) | How ticket billing was found and proved: the engine's ticket price event, the test probe, and the runs that showed the answer reaches every line in a chain |
| [future/delivery-limit-tests.md](future/delivery-limit-tests.md) | What sets a cargo's delivery limit (the game year, not the difficulty or the vehicle) and where the spoiled flag flips; the runs, and the tests still open |
| [future/revisit-later.md](future/revisit-later.md) | Open questions and options that depend on something we have not learned yet |

## About links to tf3-save-format

Game facts about the save format, the clock, finances, cargo and spoilage are kept in the [tf3-save-format](https://github.com/WuphonsReach/tf3-save-format) notes. Links to them from here point at one commit, `00c4039160d26f4fd15df0fdaf9466e67c737f7d`, not at the main branch, so they keep working when that repo moves files. When a note here is rechecked against newer save-format notes, update the commit in its links.
