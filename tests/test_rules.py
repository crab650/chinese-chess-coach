import unittest

from chess_coach.rules import Board, START_FEN


def board_with(pieces, side="w"):
    rows = [["."] * 9 for _ in range(10)]
    rows[0][4] = "k"
    rows[9][4] = "K"
    rows[5][4] = "P"  # Prevent the two generals from facing each other.
    for row, col, piece in pieces:
        rows[row][col] = piece
    return Board(tuple(tuple(row) for row in rows), side)


class RulesTests(unittest.TestCase):
    def test_start_position_and_round_trip(self):
        board = Board.from_fen(START_FEN)
        self.assertEqual(board.to_fen(), START_FEN)
        self.assertEqual(len(board.legal_moves()), 44)
        self.assertIn("b0c2", board.legal_moves())
        self.assertFalse(board.in_check("w"))

    def test_horse_leg_blocks_both_forward_jumps(self):
        board = board_with([(9, 1, "N"), (8, 1, "P")])
        self.assertNotIn("b0a2", board.legal_moves())
        self.assertNotIn("b0c2", board.legal_moves())

    def test_cannon_needs_exactly_one_screen_to_capture(self):
        board = board_with([(7, 1, "C"), (5, 1, "P"), (2, 1, "r")])
        self.assertIn("b2b7", board.legal_moves())
        no_screen = board_with([(7, 1, "C"), (2, 1, "r")])
        self.assertNotIn("b2b7", no_screen.legal_moves())

    def test_elephant_cannot_cross_river(self):
        board = board_with([(6, 2, "B")])
        self.assertNotIn("c3e5", board.legal_moves())

    def test_moving_blocker_cannot_expose_facing_generals(self):
        board = board_with([(5, 4, "R")])
        self.assertNotIn("e4f4", board.legal_moves())

    def test_king_must_answer_check(self):
        board = board_with([(5, 4, "."), (7, 4, "r"), (9, 0, "R")])
        self.assertTrue(board.in_check("w"))
        self.assertNotIn("a0a1", board.legal_moves())

    def test_pawn_moves_sideways_only_after_river(self):
        before = board_with([(6, 0, "P")])
        after = board_with([(4, 0, "P")])
        self.assertNotIn("a3b3", before.legal_moves())
        self.assertIn("a5b5", after.legal_moves())


if __name__ == "__main__":
    unittest.main()
