import copy
import os
import sys
import unittest
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from game.libraries import language
from game.engine import build_world


def make_game():
    return build_world(copy.deepcopy(language))


class TestMapTraversal(unittest.TestCase):
    def test_all_rooms_reachable_from_start(self):
        game = make_game()
        start = game.cmd.area
        visited = {id(start)}
        queue = deque([start])
        while queue:
            area = queue.popleft()
            for nxt in area.panorama.values():
                if id(nxt) not in visited:
                    visited.add(id(nxt))
                    queue.append(nxt)
        self.assertEqual(len(visited), len(game.rooms_by_id))

    def test_exits_are_bidirectional(self):
        game = make_game()
        for room in game.rooms_by_id.values():
            for direction, target in room.panorama.items():
                back = room.inverted_directions[direction]
                self.assertIs(target.panorama.get(back), room)

    def test_move_follows_exits(self):
        game = make_game()
        self.assertEqual(game.cmd.area.id, "1")
        game.cmd.move("south")
        self.assertEqual(game.cmd.area.id, "4")
        game.cmd.move("west")
        self.assertEqual(game.cmd.area.id, "5")

    def test_move_into_wall_stays_put_and_degrades(self):
        game = make_game()
        result = game.cmd.move("east")  # room 1 has no east exit
        self.assertIn("nothing", result.lower())
        self.assertEqual(game.cmd.area.id, "1")

    def test_move_with_empty_args_stays_put(self):
        game = make_game()
        result = game.cmd.move("")
        self.assertIn("nothing", result.lower())
        self.assertEqual(game.cmd.area.id, "1")

    def test_alias_movement(self):
        game = make_game()
        game.cmd.aliases["s"]("")
        self.assertEqual(game.cmd.area.id, "4")
        game.cmd.aliases["n"]("")
        self.assertEqual(game.cmd.area.id, "1")


if __name__ == "__main__":
    unittest.main()
