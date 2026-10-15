# tf3-best-before-mod

Transport Fever 3 mod: cargo payment scales with freshness.

**Status: early work.** `best_before_1/` is a logging scaffold. It pays exactly as the base game does and writes what the engine passes to the income function to the game log (lines starting `BEST_BEFORE`). It has not been run in the game yet.

Planned pay curve: full rate above a freshness threshold, then a straight line down to a minimum rate at 0% freshness, then a fixed rate (default 0%) once the cargo is spoiled.

This is an unofficial mod. It contains no files from the game.

## Licence

MIT, see [LICENSE](LICENSE).

## Development

Type checking uses the Teal compiler (`tl`, install with `luarocks install --local tl`) against the game's own type definitions:

1. Copy `tlconfig.example.lua` to `tlconfig.lua` and replace `<tf3_install_folder>` with your game install path (`tlconfig.lua` is gitignored).
2. Run `tl check best_before_1/content/mod.script.tl`.
