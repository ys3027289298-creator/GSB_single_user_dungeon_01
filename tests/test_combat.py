import random
import unittest

from game.engine import SudMonster, SudPlayer, build_world, resolve_combat

from tests.helpers import ZeroRng, load_language


class CombatTest(unittest.TestCase):
    def setUp(self):
        self.language = load_language("en")
        self.objects, self.rooms = build_world(self.language)

    def monster(self, monster_id):
        return SudMonster(monster_id, self.language["monsters"][monster_id])

    def test_player_defeats_giant_rat_exact_math(self):
        player = SudPlayer("tester")
        rat = self.monster("giant_rat")
        result = resolve_combat(player, rat, rng=ZeroRng())

        self.assertEqual(result["winner"], "player")
        self.assertEqual(result["rounds"], 2)
        self.assertEqual(rat.hp, 0)
        self.assertEqual(player.hp, 9)
        self.assertEqual(result["log"], [
            ("player", 5, 1),
            ("monster", 1, 9),
            ("player", 5, 0),
        ])

    def test_monster_defeats_weak_player(self):
        player = SudPlayer("weak")
        player.ST = 2
        player.DX = 0
        player.hp = 3
        goblin = self.monster("goblin")
        result = resolve_combat(player, goblin, rng=ZeroRng())

        self.assertEqual(result["winner"], "monster")
        self.assertEqual(result["rounds"], 1)
        self.assertEqual(player.hp, 0)
        self.assertEqual(goblin.hp, 9)

    def test_kill_completes_matching_quest(self):
        player = SudPlayer("tester")
        player.start_quest("rat_problem")
        rat = self.monster("giant_rat")
        result = resolve_combat(
            player, rat, quests=self.language["quests"], rng=ZeroRng()
        )

        self.assertEqual(result["completed_quests"], ["rat_problem"])
        self.assertEqual(
            player.quests["rat_problem"], {"state": "completed", "progress": 1}
        )

    def test_unrelated_quest_is_not_completed(self):
        player = SudPlayer("tester")
        player.start_quest("other")
        rat = self.monster("giant_rat")
        resolve_combat(
            player,
            rat,
            quests={"other": {
                "name": "Goblin Hunt",
                "description": "kill a goblin",
                "target": "goblin",
                "count": 1,
            }},
            rng=ZeroRng(),
        )
        self.assertEqual(
            player.quests["other"], {"state": "active", "progress": 0}
        )

    def test_seeded_rng_is_deterministic(self):
        def run():
            player = SudPlayer("tester")
            goblin = self.monster("goblin")
            return resolve_combat(player, goblin, rng=random.Random(7))

        self.assertEqual(run()["log"], run()["log"])

    def test_spawned_room_monster_uses_library_stats(self):
        rat = self.rooms["2"].getMonster("giant_rat")
        self.assertIsInstance(rat, SudMonster)
        self.assertEqual((rat.hp, rat.attack, rat.defense), (6, 2, 0))


if __name__ == "__main__":
    unittest.main()
