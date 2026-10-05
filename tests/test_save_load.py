import copy
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from game.libraries import language, DataIntegrityError
from game.engine import SudGame, build_world


def played_game():
    game = build_world(copy.deepcopy(language))
    game.cmd.move("south")  # 1 -> 4
    game.cmd.move("west")   # 4 -> 5
    game.cmd.get("seax")    # quest item -> quest done, room 5 emptied
    game.cmd.move("east")   # 5 -> 4
    game.cmd.move("north")  # 4 -> 1
    game.cmd.move("west")   # 1 -> 3
    game.cmd.get("apple")   # room 3: 2 apples -> 1 left
    return game


class TestSaveRoundTrip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = self.tmp.name

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def reload(self, game):
        game.save(self.path)
        return SudGame.load(self.path, data=copy.deepcopy(language))

    def test_player_state_round_trips(self):
        game = played_game()
        loaded = self.reload(game)
        char = loaded.cmd.char
        self.assertEqual(char.name, "Test Player Name")
        self.assertEqual(char.inventory["seax"]["quantity"], 1)
        self.assertEqual(char.inventory["apple"]["quantity"], 1)
        self.assertEqual(char.ST, 10)

    def test_current_room_round_trips(self):
        game = played_game()
        loaded = self.reload(game)
        self.assertEqual(loaded.cmd.area.id, "3")

    def test_picked_items_do_not_resurrect(self):
        game = played_game()
        loaded = self.reload(game)
        self.assertNotIn("seax", loaded.rooms_by_id["5"].objects)
        self.assertEqual(
            loaded.rooms_by_id["3"].objects["apple"]["quantity"], 1
        )
        self.assertEqual(
            loaded.rooms_by_id["1"].objects["rose"]["quantity"], 1
        )

    def test_quest_state_survives_load(self):
        game = played_game()
        self.assertEqual(game.journal.get("arm-yourself").state, "done")
        loaded = self.reload(game)
        self.assertEqual(
            loaded.journal.get("arm-yourself").state, "done"
        )

    def test_incomplete_quest_stays_active(self):
        game = build_world(copy.deepcopy(language))
        loaded = self.reload(game)
        self.assertEqual(
            loaded.journal.get("arm-yourself").state, "active"
        )

    def test_snapshot_is_json_and_versioned(self):
        game = played_game()
        game.save(self.path)
        with open(self.path, encoding="utf-8") as file:
            payload = json.load(file)
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["current_room"], "3")
        self.assertEqual(payload["quests"]["arm-yourself"], "done")
        self.assertEqual(payload["rooms"]["5"]["objects"], {})
        self.assertEqual(payload["rooms"]["3"]["objects"], {"apple": 1})

    def test_snapshot_uses_live_room_state(self):
        game = build_world(copy.deepcopy(language))
        before = game.to_dict()["rooms"]["3"]["objects"]
        self.assertEqual(before, {"apple": 2})
        game.cmd.move("west")
        game.cmd.get("apple")
        after = game.to_dict()["rooms"]["3"]["objects"]
        self.assertEqual(after, {"apple": 1})

    def test_monster_state_round_trips(self):
        game = build_world(copy.deepcopy(language))
        goblin = game.rooms_by_id["4"].monsters[0]
        goblin.HP = 3
        goblin.alive = True
        loaded = self.reload(game)
        loaded_goblin = loaded.rooms_by_id["4"].monsters[0]
        self.assertEqual(loaded_goblin.HP, 3)
        self.assertTrue(loaded_goblin.alive)


class TestSaveCorruption(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = self.tmp.name

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_missing_file_raises(self):
        os.unlink(self.path)
        with self.assertRaises(DataIntegrityError):
            SudGame.load(self.path)

    def test_bad_json_raises(self):
        with open(self.path, "w", encoding="utf-8") as file:
            file.write("{not json")
        with self.assertRaises(DataIntegrityError):
            SudGame.load(self.path)

    def test_wrong_version_raises(self):
        payload = played_game().to_dict()
        payload["version"] = 99
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(payload, file)
        with self.assertRaises(DataIntegrityError):
            SudGame.load(self.path)

    def test_undefined_room_raises(self):
        payload = played_game().to_dict()
        payload["current_room"] = "99"
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(payload, file)
        with self.assertRaises(DataIntegrityError):
            SudGame.load(self.path)

    def test_unknown_inventory_item_raises(self):
        payload = played_game().to_dict()
        payload["player"]["inventory"]["excalibur"] = 1
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(payload, file)
        with self.assertRaises(DataIntegrityError):
            SudGame.load(self.path)

    def test_unknown_quest_state_raises(self):
        payload = played_game().to_dict()
        payload["quests"]["arm-yourself"] = "wibble"
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(payload, file)
        with self.assertRaises(DataIntegrityError):
            SudGame.load(self.path)


if __name__ == "__main__":
    unittest.main()
