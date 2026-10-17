# Changing the mod's settings

## In short

- **Where.** The curve is set in game, in the mod's own settings dialog: the **Mods** tab, then the gear next to the mod. It is there in both **New Game** and **Load Game**. It is not under Gameplay Settings, which only holds the base game's settings.
- **How it works.** The game stores each setting in the save, shows the save's own values when you open the dialog, and hands the values to the mod when the save loads. Change a value before pressing **Load Game** and the mod uses it from that load on; the next save you make keeps it. A player can retune a save as often as they like.
- **How sure we are.** The route and the behaviour (the dialog shows the save's values, a change made before loading reaches the mod and is saved) were checked in the game on new games and on an old save. The five settings were run at the defaults and at three non-default sets, and for every setting that was not clamped the dialog, the saved header and the value the mod logged agreed. A long run on an old save with a changed curve booked 1,920 deliveries, `verify_run.py` passed, and replaying the arrivals with those numbers reproduced the logged deductions (-4,636,930 against -4,636,941) and bonuses (+10,889,581 against +10,889,569).
- **Old saves.** A save from before the settings existed shows the defaults in the dialog and loads on the default curve, whatever curve it used before; the next save you make stores them. Set the values you want before pressing Load Game.
- **Unknown.** Whether backing out of the dialog without pressing Load Game leaves the save untouched (not tried).

## On a new game

1. On the New Game screen, open the **Mods** tab.

   ![The tabs on the New Game screen](images/new-game-tabs.png)

2. Find the mod's card. The mod has to be active (its button reads **Activated**; the other mods' buttons read **Activate**). Click the gear to its right.

   ![The Activated button and gear on a mod's card](images/mod-card-gear.png)

3. The dialog lists the mod's settings under **Settings**. Set the sliders, then close the dialog with the X at its top right. The dialog opens with the values of the last new game you set up, not the defaults, because the game keeps the New Game screen's choices in its `settings.lua` in your user folder. Check them before you start.

   ![The mod's five settings at their defaults](images/mod-settings-dialog.png)

4. Start the game as usual.

## On a saved game

1. Open **Load Game**, from the main menu or from the Esc menu inside a running game.
2. On the save's card, click the gear (it is the **Details** button, next to **Load Game**).

   ![Load Game and the gear on a save's card](images/load-game-save-buttons.png)

3. Open the **Mods** tab.

   ![The tabs on a save's details page](images/load-game-tabs.png)

4. Click the gear on the mod's card, as in step 2 above. The settings show the values this save holds. Change what you want and close the dialog with the X.
5. Press **Load Game** at the bottom right of the details page. The mod uses the new values from this load, and the next save you make stores them.

## What the settings do

Pay is shown as a share of normal pay, so 100% is the pay the game gives and 150% is a 50% bonus. Freshness is 100% when cargo is picked up and falls to 0% at its delivery limit. Every slider moves in 5% steps, and in the dialog each name starts with "Best Before:". The curve is drawn out in [how-it-works.md](how-it-works.md).

| Setting | Range | Default | Meaning |
|---|---|---|---|
| Pay for fresh cargo | 100% to 200% | 120% | Pay for cargo delivered at full freshness. 100% means no bonus. |
| Full bonus down to freshness | 0% to 100% | 40% | The fresh-cargo pay holds while freshness is at or above this, then falls in a straight line. |
| Normal pay at freshness | 0% to 100% | 20% | Cargo delivered at exactly this freshness earns normal pay. |
| Lowest pay below freshness | 0% to 100% | 0% | At or below this freshness the spoiled pay applies. |
| Pay for spoiled cargo | 0% to 100% | 0% | The lowest pay: 0% takes the whole pay of a unit. Also used for cargo the game marks as spoiled. |

If the freshness points are not in order (full bonus >= normal pay >= lowest pay), the mod lowers the later point to the earlier one: with 35%, 45% and 70% it runs on 35%, 35% and 35%, while the dialog keeps showing what was set. The mod writes the values it used to the game log as `BEST_BEFORE curveSettings`, with the source (`params` for the in-game settings).

Saves made before the settings existed have none, and the game fills in the defaults, so the mod plays them on the default curve (checked on one such save). The curve in [settings.tl](../best_before_1/content/settings.tl) is only a fallback for when the game hands over no settings.
