import json
import tempfile
import unittest
from pathlib import Path

from game.engine import (
    SaveGameError,
    SudPlayer,
    build_world,
    load_game,
    save_game,
)

from tests.helpers import load_language


class SaveLoadTest(unittest.TestCase):
    def setUp(self):
        self.language = load_language("en")
        self.objects, self.rooms = build_world(self.language)
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "save.json"

    def tearDown(self):
        self.tmp.cleanup()

    def roundtrip(self, player, current_room="1"):
        save_game(player, current_room, self.rooms, self.path)
        loaded = load_game(self.path, self.language)
        self.assertIsNotNone(loaded)
        return loaded

    def test_roundtrip_preserves_inventory(self):
        player = SudPlayer("tester")
        player.take(self.objects["apple"])
        player.take(self.objects["apple"])
        player.take(self.objects["seax"])

        player2, _, _ = self.roundtrip(player)

        self.assertEqual(
            dict((name, entry["quantity"]) for name, entry in player2.inventory.items()),
            {"apple": 2, "seax": 1},
        )

    def test_roundtrip_preserves_room_state_after_pickup(self):
        player = SudPlayer("tester")
        rose = self.rooms["1"].getObject("rose")
        player.take(rose)
        self.assertNotIn("rose", self.rooms["1"].objects)

        player2, _, rooms2 = self.roundtrip(player)

        self.assertNotIn("rose", rooms2["1"].objects)
        self.assertIn("rose", player2.inventory)
        self.assertEqual(player2.inventory["rose"]["quantity"], 1)

    def test_roundtrip_preserves_dropped_item_in_room(self):
        player = SudPlayer("tester")
        player.take(self.rooms["1"].getObject("rose"))
        self.rooms["2"].addObject(player.drop("rose"))

        _, _, rooms2 = self.roundtrip(player)

        self.assertIn("rose", rooms2["2"].objects)
        self.assertNotIn("rose", rooms2["1"].objects)

    def test_roundtrip_preserves_quest_state(self):
        player = SudPlayer("tester")
        player.start_quest("rat_problem")
        player.update_quests_on_kill("giant_rat", self.language["quests"])

        player2, _, _ = self.roundtrip(player)

        self.assertEqual(
            player2.quests, {"rat_problem": {"state": "completed", "progress": 1}}
        )

    def test_roundtrip_preserves_active_quest_progress(self):
        player = SudPlayer("tester")
        player.start_quest("rat_problem")

        player2, _, _ = self.roundtrip(player)

        self.assertEqual(
            player2.quests, {"rat_problem": {"state": "active", "progress": 0}}
        )

    def test_roundtrip_preserves_player_stats_hp_and_position(self):
        player = SudPlayer("tester")
        player.ST = 12
        player.hp = 4

        player2, current_room, _ = self.roundtrip(player, current_room="2")

        self.assertEqual(current_room, "2")
        self.assertEqual(player2.ST, 12)
        self.assertEqual(player2.hp, 4)

    def test_roundtrip_preserves_monster_state(self):
        self.rooms["2"].getMonster("giant_rat").hp = 3
        self.rooms["5"].removeMonster("goblin")

        _, _, rooms2 = self.roundtrip(SudPlayer("tester"))

        self.assertEqual(rooms2["2"].getMonster("giant_rat").hp, 3)
        self.assertIsNone(rooms2["5"].getMonster("goblin"))

    def test_load_missing_file_degrades_to_none(self):
        self.assertIsNone(load_game(self.path, self.language))

    def test_load_corrupted_file_raises_save_error(self):
        self.path.write_text("this is not json{{{", encoding="utf-8")
        with self.assertRaises(SaveGameError):
            load_game(self.path, self.language)

    def test_load_unknown_item_raises_save_error(self):
        save = {
            "version": 1,
            "current_room": "1",
            "player": {"name": "x", "ST": 10, "DX": 10, "IQ": 10,
                       "HT": 10, "hp": 10, "inventory": {"dragon": 1},
                       "quests": {}},
            "rooms": {},
        }
        self.path.write_text(json.dumps(save), encoding="utf-8")
        with self.assertRaises(SaveGameError):
            load_game(self.path, self.language)

    def test_load_unknown_current_room_raises_save_error(self):
        save = {
            "version": 1,
            "current_room": "99",
            "player": {"name": "x", "ST": 10, "DX": 10, "IQ": 10,
                       "HT": 10, "hp": 10, "inventory": {}, "quests": {}},
            "rooms": {},
        }
        self.path.write_text(json.dumps(save), encoding="utf-8")
        with self.assertRaises(SaveGameError):
            load_game(self.path, self.language)


if __name__ == "__main__":
    unittest.main()
