import copy
import os
import tempfile
import unittest

from game.engine import build_world, validate_world_data
from game.libraries import WorldDataError, load_language_file

from tests.helpers import LANGUAGE_DIR, load_language


def write_temp_json(raw):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write(raw)
    return path


class DataIntegrityTest(unittest.TestCase):
    def setUp(self):
        self.language = load_language("en")

    def test_shipped_language_files_are_valid(self):
        validate_world_data(load_language("en"))
        validate_world_data(load_language("pt_BR"))

    def test_room_missing_exits_raises(self):
        data = copy.deepcopy(self.language)
        del data["rooms"]["2"]["exits"]
        with self.assertRaises(WorldDataError):
            build_world(data)

    def test_room_missing_spawns_raises(self):
        data = copy.deepcopy(self.language)
        del data["rooms"]["3"]["spawns"]
        with self.assertRaises(WorldDataError):
            build_world(data)

    def test_exit_target_must_exist(self):
        data = copy.deepcopy(self.language)
        data["rooms"]["2"]["exits"]["north"] = "99"
        with self.assertRaises(WorldDataError):
            build_world(data)

    def test_exit_direction_must_be_known(self):
        data = copy.deepcopy(self.language)
        data["rooms"]["2"]["exits"]["up"] = "1"
        with self.assertRaises(WorldDataError):
            build_world(data)

    def test_spawn_must_reference_defined_object(self):
        data = copy.deepcopy(self.language)
        data["rooms"]["1"]["spawns"]["dragon"] = 1
        with self.assertRaises(WorldDataError):
            build_world(data)

    def test_room_monster_spawn_must_reference_defined_monster(self):
        data = copy.deepcopy(self.language)
        data["rooms"]["1"]["monsters"] = {"dragon": 1}
        with self.assertRaises(WorldDataError):
            build_world(data)

    def test_monster_missing_attribute_raises(self):
        data = copy.deepcopy(self.language)
        del data["monsters"]["goblin"]["attack"]
        with self.assertRaises(WorldDataError):
            build_world(data)

    def test_monster_hp_must_be_positive(self):
        data = copy.deepcopy(self.language)
        data["monsters"]["goblin"]["hp"] = 0
        with self.assertRaises(WorldDataError):
            build_world(data)

    def test_quest_target_must_be_defined_monster(self):
        data = copy.deepcopy(self.language)
        data["quests"]["bad_quest"] = {
            "name": "Bad",
            "description": "points at nothing",
            "target": "dragon",
            "count": 1,
        }
        with self.assertRaises(WorldDataError):
            build_world(data)

    def test_duplicate_object_id_raises(self):
        raw = (
            '{"objects": {"apple": {"look": "a", "touch": "b", "use": "c"},'
            ' "apple": {"look": "x", "touch": "y", "use": "z"}},'
            ' "rooms": {}, "engine": {}}'
        )
        path = write_temp_json(raw)
        try:
            with self.assertRaises(WorldDataError):
                load_language_file(path)
        finally:
            os.remove(path)

    def test_duplicate_room_id_raises(self):
        raw = (
            '{"objects": {}, "rooms": {"1": {"title": "t", "description": "d",'
            ' "exits": {}, "spawns": {}}, "1": {"title": "u",'
            ' "description": "v", "exits": {}, "spawns": {}}}, "engine": {}}'
        )
        path = write_temp_json(raw)
        try:
            with self.assertRaises(WorldDataError):
                load_language_file(path)
        finally:
            os.remove(path)

    def test_valid_file_passes_through_loader(self):
        loaded = load_language_file(LANGUAGE_DIR / "en.json")
        self.assertEqual(
            set(loaded["objects"].keys()), set(self.language["objects"].keys())
        )


if __name__ == "__main__":
    unittest.main()
