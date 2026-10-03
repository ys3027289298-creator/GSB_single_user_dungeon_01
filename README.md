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

## World data (libraries)

Each language JSON provides the world definition in sections of `id -> attributes`:

- `objects` — item definitions (`look`, `touch`, `use`).
- `rooms` — room definitions (`title`, `description`, `exits`, `spawns`, optional `monsters`).
- `monsters` — monster definitions (`name`, `hp`, `attack`, `defense`, optional `look`).
- `quests` — kill-quest definitions (`name`, `description`, `target` monster, `count`).

`game.engine.build_world(language)` validates the data and builds objects,
rooms (with exits linked and monsters spawned) ready for `SudGame`.
`game.engine.save_game(...)` / `game.engine.load_game(...)` persist and restore
the full run state (player stats, hp, inventory, quests, current room, and
per-room object/monster state) as JSON.

### Missing data: error or degrade?

| Situation | Policy | Behavior |
| --- | --- | --- |
| Room missing `exits`/`spawns`, exit to undefined room, unknown direction, spawn of undefined object/monster | **Error** | `WorldDataError` at load/validation time (fail fast) |
| Duplicate ids in a language JSON | **Error** | `WorldDataError` raised by the loader (JSON would otherwise silently keep the last duplicate) |
| Monster/quest missing required fields, non-positive `hp` | **Error** | `WorldDataError` at validation time |
| Optional monster `look` missing | **Degrade** | Defaults to empty string |
| Player walks where no exit exists, takes/uses missing items | **Degrade** | Friendly message, game continues |
| Save file does not exist | **Degrade** | `load_game` returns `None` |
| Save file corrupted, wrong version, or references unknown ids | **Error** | `SaveGameError` (a half-restored state is never trusted) |

Rationale: broken *static data* is a content bug and must fail fast instead of
silently producing an inconsistent world; *runtime player actions* and a missing
save are recoverable situations and degrade gracefully.

---

## Tests

```bash
$ make test          # pytest if installed, otherwise stdlib unittest
```

Covers data integrity (validation + duplicate ids), map traversal
(reachability, exit symmetry, out-of-bounds moves), combat resolution
(deterministic, seedable RNG), and save/load round-trips.

---

## License

MIT License — see [LICENSE](https://github.com/nerun/single-user-dungeon/raw/main/LICENSE)
