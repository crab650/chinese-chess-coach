import unittest

from chess_coach.opponent_lesson import inspect_move
from chess_coach.rules import Board


class OpponentLessonTests(unittest.TestCase):
    def test_check_takes_priority(self):
        fen = "4k4/9/9/9/9/4P4/9/9/r8/4K4 b - - 0 1"
        lesson = inspect_move(fen, "a1e1", "w")
        self.assertEqual(lesson["category"], "check")
        self.assertIn("將軍", lesson["explanation"])
        self.assertEqual(lesson["threat_move"], "e1e0")

    def test_capture_explains_the_piece_taken(self):
        fen = "4k4/9/9/9/9/4P4/r2N5/9/9/4K4 b - - 0 1"
        lesson = inspect_move(fen, "a3d3", "w")
        self.assertEqual(lesson["category"], "capture")
        self.assertIn("傌", lesson["explanation"])
        self.assertEqual(lesson["highlights"], ["a3", "d3"])

    def test_threat_explains_a_possible_next_capture(self):
        fen = "4k4/9/9/9/r8/4P4/9/3N5/9/4K4 b - - 0 1"
        lesson = inspect_move(fen, "a5d5", "w")
        self.assertEqual(lesson["category"], "capture")
        self.assertEqual(lesson["threat_move"], "d5d2")
        self.assertIn("可能", lesson["explanation"])

    def test_quiet_move_does_not_claim_a_forced_plan(self):
        fen = "4k4/9/n8/9/9/4P4/9/9/9/4K4 b - - 0 1"
        lesson = inspect_move(fen, "a7b5", "w")
        self.assertEqual(lesson["category"], "quiet")
        self.assertIsNone(lesson["threat_move"])
        self.assertIn("沒有立即", lesson["explanation"])


if __name__ == "__main__":
    unittest.main()
