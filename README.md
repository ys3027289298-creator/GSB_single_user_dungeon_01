```
   ____     _   _     ____
  / ___|   | | | |   |  _ \
  \___ \   | | | |   | | | |
   ___) |_ | |_| | _ | |_| |_
  |____/(_) \___/ (_)|____/(_)
```

[![Python](https://img.shields.io/badge/Python_3-%23244d70?style=flat&logo=python&logoColor=%23ffde58)](https://www.python.org/) [![MIT License](https://img.shields.io/badge/License-%25?style=flat&label=MIT&color=olive)](https://en.wikipedia.org/wiki/MIT_License)


# Single User Dungeon

Text-based adventure engine  
Inspired by classic [MUDs](https://en.wikipedia.org/wiki/Multi-user_dungeon), focused on **single-player** experience.

Written in [Python](https://www.python.org)  
Create & explore interactive dungeons with RPG & sandbox elements.

Data & translations via JSON files — easy customization.

> [!Note]
> This game engine is being developed as from the scripts created by Tomas Varaneckas (Vilnius, Lithuania), and released on his blog [Paranoid Engineering](Http://paranoid-engineering.blogspot.com/2008/11/python-mud-game-example.html) on November 25th, 2008.

---

## Requirements

- Python 3.8+
- Standard libs: `json`, `os`, `locale`, `pathlib`
- No external dependencies

---

## Installation & Running

```bash
$ git clone https://github.com/nerun/single-user-dungeon.git
$ cd single-user-dungeon/src
$ python3 -m game.main
```

**Tip:** type `help` inside the game for commands.

---

## Localization

- Game content (rooms, objects, UI) in `language/` folder JSON files.
- Add new language: create `<locale_code>.json` (e.g., `fr_FR.json`).
- Edit manually or with Poedit (v3.3+).
- Auto-detects system locale, defaults to English if missing.

---

## Data Integrity Policy

The engine validates all game data at load time (`game.engine.validate_language`,
called by `game.engine.build_world`). The rule is:

**Fail fast (raises `DataIntegrityError`)** — structural problems that would
corrupt the game silently:

- a room missing `exits`/`title`/`spawns` (a dead end must say `"exits": {}`);
- duplicate object/room/monster ids in a JSON file (plain `json` would
  silently drop one);
- an exit pointing to an undefined room, or two rooms claiming contradictory
  reciprocal exits;
- a monster missing combat attributes (`ST`, `DX`, `IQ`, `HT`, `damage`);
- a corrupt, outdated or inconsistent save file.

**Degrade gracefully** — problems the player can safely survive:

- missing optional flavor text (`description`, object `look`/`touch`/`use`,
  monster `look`) falls back to default engine text;
- runtime actions with no valid target (walking into a wall, taking an item
  that is not there) return an in-game message instead of raising.

Save files (`SudGame.save` / `SudGame.load`) snapshot the live state: player
attributes and inventory, per-room object quantities, monster HP/alive flags
and quest states — so picked-up items stay picked up and completed quests stay
completed after a load.

---

## Tests

```bash
$ PYTHONPATH=src python3 -m unittest discover -s tests
```

Covers data integrity, map traversal, combat resolution and save round-trips.

---

## License

MIT License — see [LICENSE](https://github.com/nerun/single-user-dungeon/raw/main/LICENSE)
