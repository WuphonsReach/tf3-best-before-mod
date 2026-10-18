# Publishing on mod.io

## In short

- **Where it is.** [Best Before: Cargo Freshness](https://mod.io/g/transportfever3/m/best-before-cargo-freshness) on mod.io, mod id 6459472. Public since 17 Oct 2026 as an early test version, tag Script Mod, creator WuphonsReach, two files (one for Windows, Mac and Linux, one for Xbox Series X/S and PlayStation 5; 19.22 KB each since 1.0.1). mod.io labels every file "1.0" whatever we upload and serves the newest file of each platform; the older files stay under "View 2 other versions" and can still be downloaded by hand. The changelog text is attached to each file, so it is what tells them apart. Players subscribe on that page or in the game's Mod Hub.
- **How it gets there.** Only through the game's own uploader: Mod Hub, My Mods, the mod's dialog. The mod.io website refuses uploads for Transport Fever 3. The uploader reads the name, summary, description and tags from [modinfo.json](../best_before_1/_metadata/modinfo.json) and the images from `best_before_1/_metadata/`. At the first upload it wrote `best_before_1/_metadata/mod.io_fileid.txt` (the mod id). Keep that file committed: with it the dialog updates the existing mod, without it the next upload would create a second one.
- **Editing the page.** The mod belongs to the game's own mod.io account, which the website's Steam login does not reach. So the page text changes only through the uploader (Update Metadata ticked), from the text kept here and copied into `modinfo.json`.
- **What ships.** The whole `content/` folder plus `mod.json` and `_content.json`, but no `_metadata`. The game builds the mod's file index from `_content.json`: a file the list leaves out is on disk but cannot be loaded. The 1.0 list named three of the four scripts, so the game refused to start ("Could not initialize game: try removing the mod"); see [CHANGELOG.md](../CHANGELOG.md).
- **How sure we are.** First upload (private), Set Public, and Update Metadata have each been done once, and the public page shows the cover, description and tag from `modinfo.json`. A subscribed copy of 1.0 was compared byte for byte with the repo, but it was not loaded until 18 Oct, and then it failed (the file list above); so a release is only good once a save has loaded with the published copy. Search in the Mod Hub matches the mod's name only (see below).
- **Update replaces the files (seen on 1.0.1).** The page is about a minute behind after an upload: reload before judging its file list. The version label stays "1.0" (`mod.json` has only `revision` 1; whether `revision` drives the label is untried). **Unknown.** Whether cargo from other mods works (the description says it is expected to).

## Uploading an update

1. Edit the listing text below first, then copy it into `modinfo.json` (the description with line breaks as `\n`).
2. Keep `best_before_1/_content.json` in step with `best_before_1/content/`: every file under `content/` listed (the game cannot load one that is missing). Run `python3 tools/check_content_list.py` (it fails if the list and the folder differ). Set `modVersion` in `mod.script.tl`, move the `CHANGELOG.md` entry from "not released yet" to the version and date, and put `settings.tl`'s `logLevel` back to `summary`.
3. Start the game, open **Mod Hub**, then **My Mods**, and click the mod's card.
4. In the dialog:
   - **Validation** should read "No Issues Found" (**Re-Validate** runs it again).
   - **PC** and **Console** both ticked gives the two file entries.
   - **Set Public** ticked. Unticked, the page is hidden: visitors see "'best before cargo freshness' is hidden ... preview access is required".
   - **Update Metadata** ticked, so the page takes the name, summary, description and tags from `modinfo.json`.
   - **Changelog**: write one, a one-liner is enough; the text is the "Release note" line of the version's entry in [CHANGELOG.md](../CHANGELOG.md). An empty one shows on the page as "No release notes provided".
   - The button reads **Update** with the line "The existing mod on mod.io will be updated". If it reads **Upload** with "A new mod will be created on mod.io", `mod.io_fileid.txt` is missing: stop and restore it.
5. Press **Update**. The dialog shows "Uploading... Please Wait" and a counter ("Uploading Mods (1/1)", or 2/2), then "Upload Successful".
6. Open the page (**Open Mod Page** in the dialog) and check the text, the files and their dates.
7. Test the published copy: remove the `staging_area` link (with the link in place the game loads the staging copy even when the mod is subscribed: it logs `Multiple (2) mods with same id found best_before_1, the one from .../staging_area/best_before_1/ has been selected`, so such a run says nothing about the published file), subscribe, load a save with the mod active, and look in the log for `BEST_BEFORE version <the new number>` and the downloaded `_content.json` for all files. Only then tell anyone it works. Unsubscribe and restore the link afterwards.

The dialog's other parts: **Preview** (the cover, see [Preview image](#preview-image)), a gallery that picks up `workshop_preview.jpg` by itself, **Tags** (with + to add), **Author**, **View**, **Report**, and at the top a pencil, **Open Folder** and **Refresh**.

## Hub search and tiles

- **Search matches the name only.** In the Mod Hub, words that appear only in another mod's summary or description find nothing, and words in names do (case-insensitive part of a word: "namer" finds Auto Line Namer, "names" does not). So the name carries the search words: "best before", "cargo", "freshness".
- **Tiles show the whole 16:9 preview, uncropped.** On a 4K screen a tile is about 620 px wide in the game and about 455 px on mod.io. The game's tile shows name, downloads and subscribers. mod.io's tile adds the author, the summary cut after about 130 characters, the first tag and the size.
- **Downloads ship without `_metadata`.** A subscribed mod's folder holds `mod.json`, `_content.json`, `content/` and any top-level files, but no `_metadata`; the hub builds its page from mod.io's own copy of the text.

## Name

Best Before: Cargo Freshness

## Tags

Script Mod

It sits under the hub's Misc group. Other cargo mods there (Route-Based Cargo Income, Slower Town Cargo Demand) carry the same single tag; the mod changes no industries, so no Industry tag.

## Summary

Cargo pay follows freshness: fresh deliveries earn a bonus, slow or spoiled cargo earns less. Five adjustable settings, and warnings for lines that deliver stale cargo.

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

STALE CARGO WARNINGS
- A line whose deliveries are mostly stale gets a "Stale Cargo" warning: a pop-up, an entry in the notification log, and an icon on the line in the Line & Vehicle Management window (click it to open the line). It is a Caution, not a fault: stale cargo costs pay, nothing is broken.
- A unit counts as stale when its freshness is below half of the "normal pay at freshness" setting, or when the game marks it spoiled. It counts for the line of its last leg.
- The mod looks at the last 12 game months, once a month, so a line has to deliver mostly stale cargo for several months before it is warned, and run well for several months before the warning goes.
- To hide the warnings, filter "Stale Cargo (Best Before)" out of the notification log.

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

`best_before_1/_metadata/workshop_preview.jpg` is drawn by `tools/make_preview.py`. `best_before_1/_metadata/0.jpg` is the cover: the uploader made it when the image was picked in the dialog's Preview slot, and it is byte-identical to `workshop_preview.jpg`. Both are committed. The name `0.jpg` follows the developer's own mods, whose cover is `0.png`.

To re-create `0.jpg` after the image is redrawn, or if it is lost:

1. Redraw (optional): `python3 tools/make_preview.py [--version 0.1]` writes `workshop_preview.jpg` (1920x1080; needs `rsvg-convert` and the Lato font).
2. Copy it: `cp best_before_1/_metadata/workshop_preview.jpg best_before_1/_metadata/0.jpg`. Check with `cmp` that the two are identical.
3. In the game, open the mod's dialog in My Mods and click the Preview slot (camera icon) to pick the image, so the uploader takes it as the cover. Without a cover the card shows a "?".

Whether the uploader needs step 2 or makes `0.jpg` from step 3 alone is not known.

## What was checked

All on 17 Oct 2026, from screenshots of the game's dialog and the mod.io site.

- **First upload.** Dialog with Set Public unticked: "Uploading Mods (1/1)", "Upload Successful". The button then changed from Upload to Update, the dialog gained Open Mod Page, and `mod.io_fileid.txt` appeared. The page was hidden to visitors.
- **Going public.** Same dialog, Set Public ticked, Update: "Uploading Mods (2/2)", "Upload Successful". A logged-out visitor then saw the mod first in Script Mod sorted by recently added, with cover, summary, tag and 13.36 KB. The page showed ID 6459472, version 1.0 twice (files `modfile_6459472-dxam.zip` for Xbox Series X/S and PlayStation 5, `modfile_6459472-0qwo.zip` for Windows, Mac and Linux, both "No release notes provided"), and the creator's profile listed one mod.
- **Description.** The public page shows the description above, the cargo-from-other-mods paragraph included.
- **Package contents.** Subscribed to 1.0 at 19:05: `~/snap/steam/common/mod.io/common/10640/mods/6459472/` holds `mod.json`, `_content.json` and the four files in `content/`, all identical to the repo at the upload, including `settings.tl`, which that `_content.json` does not list. No `_metadata`. In seven other downloaded mods the files outside `content/` (README, licence, `strings.json`, `texture_metadata_cache.lua`) ship as well.
