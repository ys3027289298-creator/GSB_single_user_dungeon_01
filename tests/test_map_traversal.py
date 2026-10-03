import unittest

import game.engine as engine_module
from game.engine import SudGame, SudPlayer, build_world

from tests.helpers import load_language


def reachable_from(language, start):
    seen = {start}
    stack = [start]
    while stack:
        room = stack.pop()
        for target in language["rooms"][room]["exits"].values():
            if target not in seen:
                seen.add(target)
                stack.append(target)
    return seen


class MapTraversalTest(unittest.TestCase):
    def setUp(self):
        self.language = load_language("en")
        self.objects, self.rooms = build_world(self.language)
        engine_module.clear = lambda: None

    def test_all_rooms_reachable_from_start(self):
        for code in ("en", "pt_BR"):
            language = load_language(code)
            all_rooms = set(language["rooms"].keys())
            self.assertEqual(reachable_from(language, "1"), all_rooms)

    def test_exits_are_bidirectionally_consistent(self):
        inverse = {"north": "south", "south": "north", "east": "west", "west": "east"}
        for code in ("en", "pt_BR"):
            rooms = load_language(code)["rooms"]
            for room_id, room in rooms.items():
                for direction, target in room["exits"].items():
                    back = rooms[target]["exits"].get(inverse[direction])
                    self.assertEqual(
                        back,
                        room_id,
                        f"{code}: room {room_id} {direction} -> {target} "
                        f"but no {inverse[direction]} way back",
                    )

    def test_engine_links_match_data(self):
        for room_id, room in self.language["rooms"].items():
            for direction, target in room["exits"].items():
                linked = self.rooms[room_id].relocate(direction)
                self.assertIs(linked, self.rooms[target])

    def test_move_out_of_bounds_degrades_gracefully(self):
        player = SudPlayer("tester")
        game = SudGame(player, self.rooms["2"])
        result = game.cmd.move("north")
        self.assertEqual(result, engine_module.engine["nothing_that_way"] + "\n")
        self.assertIs(game.cmd.area, self.rooms["2"])

    def test_move_with_empty_direction_degrades_gracefully(self):
        player = SudPlayer("tester")
        game = SudGame(player, self.rooms["1"])
        result = game.cmd.move("")
        self.assertEqual(result, engine_module.engine["nothing_that_way"] + "\n")
        self.assertIs(game.cmd.area, self.rooms["1"])

    def test_walk_full_loop_returns_to_start(self):
        player = SudPlayer("tester")
        game = SudGame(player, self.rooms["1"])
        route = ["north", "south", "south", "west", "east", "north"]
        expected = ["2", "1", "4", "5", "4", "1"]
        for direction, room_id in zip(route, expected):
            game.cmd.move(direction)
            self.assertIs(game.cmd.area, self.rooms[room_id])


if __name__ == "__main__":
    unittest.main()
