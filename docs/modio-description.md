# The mod.io listing text

## In short

- **What this is.** The text for the mod's mod.io page: name, summary, tags and description, kept here so it can be pasted into the listing and mirrored into [modinfo.json](../best_before_1/_metadata/modinfo.json). Edit it here first, then copy it to `modinfo.json`.
- **Name:** "Best Before: Cargo Freshness". The Mod Hub search matches the name only, not the summary or the description, so the name carries the search words.
- **Tags:** "Script Mod" only. It sits under the hub's Misc group. Other cargo mods listed there (Route-Based Cargo Income, Slower Town Cargo Demand) carry the same single tag; the mod changes no industries, so no Industry tag.
- **How sure we are.** The search finding comes from searching the hub for words that appear only in another mod's summary or description (nothing found) and for words in names (found). The in-game upload tool (Mod Hub, My Mods) reads `modinfo.json`: it showed our name, tag and description, and picked up `workshop_preview.jpg` as a gallery image. The cover (its Preview slot) is set in that dialog by clicking the slot. A downloaded mod ships without a `_metadata` folder, so the hub page is built from mod.io's own copy of the text.
- **Preview image.** `best_before_1/_metadata/workshop_preview.jpg` is drawn by `tools/make_preview.py`. `best_before_1/_metadata/0.jpg` is the cover: the in-game uploader made it when the image was picked in the dialog's Preview slot, and it is byte-identical to `workshop_preview.jpg`. See [Preview image](#preview-image) to re-create it.
- **Unknown.** Whether mod.io's page can be edited after the upload; whether cargo from other mods works in the game (the description says it is expected to).

## Name

Best Before: Cargo Freshness

## Tags

Script Mod

## Summary

Cargo pay follows freshness: fresh deliveries earn a bonus, slow or spoiled cargo earns less. Five adjustable settings.

## Description

The text below is what `modinfo.json` holds, with line breaks as `\n`.

```
Cargo pay follows freshness. Cargo delivered fresh earns a bonus on top of its normal pay, cargo that took too long earns less, and cargo that spoiled earns the lowest pay.

EARLY TEST VERSION. This is early work, checked in the game on a handful of saves. Expect rough edges and changes. Keep a backup of any save you play with it.

HOW IT WORKS
- The game pays every delivered cargo unit in full, as usual. The mod then books one correcting entry to your account: a bonus for fresh cargo, a deduction for slow or spoiled cargo.
- Freshness is 100% when cargo is picked up and falls to 0% at its delivery limit (1.5 times the cargo's delivery time). Cargo that waited in a warehouse is judged on its age with the warehouse pause taken off.
- Only cargo is adjusted. Passenger income is not touched.

CARGO FROM OTHER MODS
- Expected to work, for example the cargo of the Sugar Cane Industry mod (sugar cane, sugar, molasses, rum). The mod reads each cargo's own delivery time and price from the game's cargo list and has no list of cargo names, so a cargo that sets those the usual way is judged like the base game's. This has not been tried in the game yet.

THE DEFAULT CURVE
- Freshness 40% and above: 120% of normal pay.
- 40% down to 20%: falls in a straight line to normal pay.
- 20% down to 0%: falls in a straight line to no pay.
- Spoiled cargo: no pay.

FIVE SETTINGS
Set them under Mods, with the gear next to the mod, in New Game or in Load Game. The game keeps them in the save, so you can retune a save on any load. All sliders move in 5% steps.
- Pay for fresh cargo: 100% to 200% (default 120%).
- Full bonus down to freshness: 0% to 100% (default 40%).
- Normal pay at freshness: 0% to 100% (default 20%).
- Lowest pay below freshness: 0% to 100% (default 0%).
- Pay for spoiled cargo: 0% to 100% (default 0%).

GOOD TO KNOW
- With the default settings a spoiled unit pays nothing, so a save with a lot of spoiled cargo can lose money. Raise the spoiled pay if that is too harsh.
- The entry goes to your company account. The per-vehicle and per-line figures in the game still show the full pay.
- A unit whose source or target building is gone before it arrives gets no entry.
- Works on a save that did not have the mod before. Settings of a save from before the mod existed show the defaults.

COMPATIBILITY
- The mod replaces the game's cargo income function with a copy of the base formula, so that it can log what the engine passes in. Pay is unchanged. Another mod that replaces the cargo income calculation will conflict with it; use one or the other.
- It contains no files from the game.
- Gameplay mods may disable achievements.

Source and notes: https://github.com/WuphonsReach/tf3-best-before-mod (MIT licence).
```

## Preview image

Both files sit in `best_before_1/_metadata/` and are committed. `0.jpg` follows the name the developer's own mods use for their cover (`0.png`).

To re-create `0.jpg` after the image is redrawn, or if it is lost:

1. Redraw (optional): `python3 tools/make_preview.py [--version 0.1]` writes `workshop_preview.jpg` (1920x1080; needs `rsvg-convert` and the Lato font).
2. Copy it: `cp best_before_1/_metadata/workshop_preview.jpg best_before_1/_metadata/0.jpg`. Check with `cmp` that the two are identical.
3. In the game, open Mod Hub, My Mods, the mod's dialog and click the Preview slot (camera icon) to pick the image, so the uploader takes it as the cover. Before the cover was set the card showed a "?".

Whether the uploader needs step 2 or makes `0.jpg` from step 3 alone is not known: the file appeared when the cover was picked, and was not there before.
