import unittest

from chess_coach.engine import Analysis
from chess_coach.guide import build_guide
from chess_coach.rules import Board


class GuideTests(unittest.TestCase):
    def test_cannon_check_explanation_counts_screens(self):
        board = Board.from_fen("4k4/9/9/9/9/4c4/9/5C3/4A4/4K4 w - - 0 1")
        self.assertTrue(board.in_check("w"))
        self.assertIn("f2e2", board.legal_moves())
        result = build_guide(board, Analysis("f2e2", 0, ("f2e2",), 6, 1), "w")
        self.assertEqual(result["focus"]["threat_move"], "e4e0")
        self.assertTrue(result["focus"]["threat_straight"])
        self.assertIn("一枚", result["focus"]["problem"])
        self.assertIn("兩枚", result["focus"]["solution"])
        self.assertFalse(board.play("f2e2").in_check("w"))


if __name__ == "__main__":
    unittest.main()
