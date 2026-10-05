import copy
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from game.libraries import (
    LANGUAGE_DIR,
    DataIntegrityError,
    language,
    load_language_file,
)
from game.engine import SudMonster, build_world, validate_language


def valid_data():
    return copy.deepcopy(language)


class TestShippedData(unittest.TestCase):
    def test_en_data_is_valid(self):
        validate_language(load_language_file(LANGUAGE_DIR / "en.json"))

    def test_pt_br_data_is_valid(self):
        validate_language(load_language_file(LANGUAGE_DIR / "pt_BR.json"))

    def test_build_world_from_shipped_data(self):
        game = build_world(valid_data())
        self.assertEqual(sorted(game.rooms_by_id), ["1", "2", "3", "4", "5"])


class TestRoomExits(unittest.TestCase):
    def test_room_missing_exits_raises(self):
        data = valid_data()
        del data["rooms"]["5"]["exits"]
        with self.assertRaises(DataIntegrityError) as ctx:
            validate_language(data)
        self.assertIn('"5"', str(ctx.exception))
        self.assertIn("exits", str(ctx.exception))

    def test_room_missing_title_raises(self):
        data = valid_data()
        del data["rooms"]["2"]["title"]
        with self.assertRaises(DataIntegrityError):
            validate_language(data)

    def test_empty_exits_is_a_valid_dead_end(self):
        data = valid_data()
        data["rooms"]["5"]["exits"] = {}
        data["rooms"]["4"]["exits"] = {"north": "1"}
        validate_language(data)

    def test_dangling_exit_raises(self):
        data = valid_data()
        data["rooms"]["1"]["exits"]["east"] = "99"
        with self.assertRaises(DataIntegrityError) as ctx:
            validate_language(data)
        self.assertIn("99", str(ctx.exception))

    def test_conflicting_reciprocal_exit_raises(self):
        data = valid_data()
        data["rooms"]["2"]["exits"]["south"] = "3"
        with self.assertRaises(DataIntegrityError) as ctx:
            validate_language(data)
        self.assertIn("exit mismatch", str(ctx.exception))

    def test_invalid_direction_raises(self):
        data = valid_data()
        data["rooms"]["1"]["exits"]["up"] = "2"
        with self.assertRaises(DataIntegrityError):
            validate_language(data)

    def test_spawn_of_undefined_object_raises(self):
        data = valid_data()
        data["rooms"]["1"]["spawns"]["dragon"] = 1
        with self.assertRaises(DataIntegrityError):
            validate_language(data)


class TestDuplicateObjectIds(unittest.TestCase):
    def test_duplicate_ids_are_rejected_not_silently_dropped(self):
        raw = (
            '{"objects": {'
            '"apple": {"look": "first", "touch": "t", "use": "u"},'
            '"apple": {"look": "second", "touch": "t", "use": "u"}'
            "}}"
        )
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(raw)
            path = tmp.name
        try:
            with self.assertRaises(DataIntegrityError) as ctx:
                load_language_file(path)
            self.assertIn("apple", str(ctx.exception))
        finally:
            os.unlink(path)

    def test_plain_json_silently_loses_duplicates(self):
        # Documents the bug being guarded against.
        raw = '{"a": 1, "a": 2}'
        self.assertEqual(json.loads(raw), {"a": 2})


class TestMonsterAttributes(unittest.TestCase):
    def test_missing_monster_attribute_raises_at_load(self):
        data = valid_data()
        del data["monsters"]["goblin"]["HT"]
        with self.assertRaises(DataIntegrityError) as ctx:
            validate_language(data)
        self.assertIn("goblin", str(ctx.exception))
        self.assertIn("HT", str(ctx.exception))

    def test_sudmonster_rejects_incomplete_definition(self):
        with self.assertRaises(DataIntegrityError):
            SudMonster("goblin", {"ST": 8, "DX": 12, "IQ": 6})

    def test_monster_look_is_optional_and_degrades(self):
        data = valid_data()
        del data["monsters"]["goblin"]["look"]
        game = build_world(data)
        goblin = game.rooms_by_id["4"].monsters[0]
        self.assertIn("goblin", goblin.sight)

    def test_encounter_with_undefined_monster_raises(self):
        data = valid_data()
        data["encounters"]["4"] = ["dragon"]
        with self.assertRaises(DataIntegrityError):
            validate_language(data)


class TestGracefulDegradation(unittest.TestCase):
    def test_missing_object_flavor_fields_degrade(self):
        data = valid_data()
        del data["objects"]["apple"]["touch"]
        game = build_world(data)
        apple = game.objects_by_id["apple"]
        self.assertTrue(apple.collide)  # default text, no crash

    def test_missing_description_degrades(self):
        data = valid_data()
        del data["rooms"]["2"]["description"]
        game = build_world(data)
        self.assertIn("No description", game.rooms_by_id["2"].sight)


if __name__ == "__main__":
    unittest.main()
