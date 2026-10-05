import copy
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from game.libraries import language
from game.engine import SudMonster, SudPlayer, build_world, resolve_combat


class FixedRng:
    """Scripted dice: randint(1, 6) cycles through the given rolls."""

    def __init__(self, rolls):
        self.rolls = list(rolls)
        self.index = 0

    def randint(self, a, b):
        self.assert_bounds(a, b)
        value = self.rolls[self.index % len(self.rolls)]
        self.index += 1
        return value

    @staticmethod
    def assert_bounds(a, b):
        assert (a, b) == (1, 6)


def make_goblin():
    data = copy.deepcopy(language)["monsters"]["goblin"]
    return SudMonster("goblin", data)


class TestCombatResolution(unittest.TestCase):
    def test_player_wins_when_always_hitting(self):
        char = SudPlayer("hero")
        goblin = make_goblin()
        rng = FixedRng([1, 1, 1, 6, 6, 6])  # player hits, goblin misses
        result = resolve_combat(char, goblin, rng=rng)
        self.assertEqual(result.winner, "player")
        self.assertFalse(goblin.alive)
        self.assertLessEqual(goblin.HP, 0)
        self.assertEqual(char.HP, char.HT)  # never got hit
        self.assertGreater(result.rounds, 0)
        self.assertEqual(len(result.log), result.rounds * 2 - 1)

    def test_monster_wins_against_weak_player(self):
        char = SudPlayer("weakling")
        char.HP = 2
        goblin = make_goblin()
        rng = FixedRng([6, 6, 6, 1, 1, 1])  # player misses, goblin hits
        result = resolve_combat(char, goblin, rng=rng)
        self.assertEqual(result.winner, "monster")
        self.assertTrue(goblin.alive)
        self.assertLessEqual(char.HP, 0)

    def test_draw_when_neither_side_can_hit(self):
        char = SudPlayer("hero")
        goblin = make_goblin()
        rng = FixedRng([6, 6, 6, 6, 6, 6])  # everyone misses
        result = resolve_combat(char, goblin, rng=rng, max_rounds=10)
        self.assertEqual(result.winner, "draw")
        self.assertEqual(result.rounds, 10)
        self.assertEqual(char.HP, char.HT)
        self.assertEqual(goblin.HP, goblin.HT)

    def test_seeded_combat_is_reproducible(self):
        data = copy.deepcopy(language)
        game1 = build_world(data)
        game2 = build_world(data)
        goblin1 = game1.rooms_by_id["4"].monsters[0]
        goblin2 = game2.rooms_by_id["4"].monsters[0]
        r1 = resolve_combat(game1.cmd.char, goblin1, rng=random.Random(7))
        r2 = resolve_combat(game2.cmd.char, goblin2, rng=random.Random(7))
        self.assertEqual(r1.winner, r2.winner)
        self.assertEqual(r1.rounds, r2.rounds)
        self.assertEqual(game1.cmd.char.HP, game2.cmd.char.HP)

    def test_monster_hp_persists_after_fight(self):
        game = build_world(copy.deepcopy(language))
        goblin = game.rooms_by_id["4"].monsters[0]
        resolve_combat(game.cmd.char, goblin, rng=random.Random(1))
        self.assertNotEqual(goblin.HP, goblin.HT)


if __name__ == "__main__":
    unittest.main()
