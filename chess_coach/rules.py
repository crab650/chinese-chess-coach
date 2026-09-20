"""Portable Xiangqi board rules and UCCI coordinate conversion."""

from __future__ import annotations

from dataclasses import dataclass


START_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
FILES = "abcdefghi"
PIECES = set("rnbakcpRNBAKCP")
RED_NAMES = {"R": "俥", "N": "傌", "B": "相", "A": "仕", "K": "帥", "C": "炮", "P": "兵"}
BLACK_NAMES = {"r": "車", "n": "馬", "b": "象", "a": "士", "k": "將", "c": "砲", "p": "卒"}


def side_of(piece: str) -> str:
    return "w" if piece.isupper() else "b"


def opponent(side: str) -> str:
    return "b" if side == "w" else "w"


def square_to_coord(row: int, col: int) -> str:
    return FILES[col] + str(9 - row)


def coord_to_square(coord: str) -> tuple[int, int]:
    if len(coord) != 2 or coord[0] not in FILES or coord[1] not in "0123456789":
        raise ValueError("無效的棋盤座標")
    return 9 - int(coord[1]), FILES.index(coord[0])


def move_to_squares(move: str) -> tuple[int, int, int, int]:
    if len(move) != 4:
        raise ValueError("無效的走法")
    r1, c1 = coord_to_square(move[:2])
    r2, c2 = coord_to_square(move[2:])
    return r1, c1, r2, c2


@dataclass(frozen=True)
class Board:
    rows: tuple[tuple[str, ...], ...]
    side: str = "w"

    @classmethod
    def from_fen(cls, fen: str) -> "Board":
        parts = fen.strip().split()
        if not parts:
            raise ValueError("空的 FEN")
        raw_rows = parts[0].split("/")
        if len(raw_rows) != 10:
            raise ValueError("FEN 必須有十列")
        rows: list[tuple[str, ...]] = []
        for raw in raw_rows:
            expanded: list[str] = []
            for char in raw:
                if char in "123456789":
                    expanded.extend("." for _ in range(int(char)))
                elif char in PIECES:
                    expanded.append(char)
                else:
                    raise ValueError("FEN 包含無效棋子")
            if len(expanded) != 9:
                raise ValueError("FEN 每列必須有九格")
            rows.append(tuple(expanded))
        side = parts[1] if len(parts) > 1 else "w"
        if side not in ("w", "b"):
            raise ValueError("FEN 走棋方無效")
        return cls(tuple(rows), side)

    def to_fen(self) -> str:
        encoded = []
        for row in self.rows:
            text = ""
            blanks = 0
            for piece in row:
                if piece == ".":
                    blanks += 1
                else:
                    if blanks:
                        text += str(blanks)
                        blanks = 0
                    text += piece
            if blanks:
                text += str(blanks)
            encoded.append(text)
        return "/".join(encoded) + f" {self.side} - - 0 1"

    def piece(self, row: int, col: int) -> str:
        return self.rows[row][col]

    def _can_land(self, row: int, col: int, side: str) -> bool:
        return 0 <= row < 10 and 0 <= col < 9 and (
            self.rows[row][col] == "." or side_of(self.rows[row][col]) != side
        )

    def _pseudo_from(self, row: int, col: int) -> list[str]:
        piece = self.piece(row, col)
        if piece == ".":
            return []
        side = side_of(piece)
        kind = piece.lower()
        result: list[str] = []

        def add(r: int, c: int) -> None:
            if self._can_land(r, c, side):
                result.append(square_to_coord(row, col) + square_to_coord(r, c))

        if kind in ("r", "c"):
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                r, c, screened = row + dr, col + dc, False
                while 0 <= r < 10 and 0 <= c < 9:
                    target = self.piece(r, c)
                    if kind == "r":
                        if target == ".":
                            add(r, c)
                        else:
                            add(r, c)
                            break
                    elif not screened:
                        if target == ".":
                            add(r, c)
                        else:
                            screened = True
                    elif target != ".":
                        add(r, c)
                        break
                    r += dr
                    c += dc
        elif kind == "n":
            for dr, dc, lr, lc in (
                (-2, -1, -1, 0), (-2, 1, -1, 0), (2, -1, 1, 0), (2, 1, 1, 0),
                (-1, -2, 0, -1), (1, -2, 0, -1), (-1, 2, 0, 1), (1, 2, 0, 1),
            ):
                r, c = row + dr, col + dc
                if 0 <= r < 10 and 0 <= c < 9 and self.piece(row + lr, col + lc) == ".":
                    add(r, c)
        elif kind == "b":
            for dr, dc in ((-2, -2), (-2, 2), (2, -2), (2, 2)):
                r, c = row + dr, col + dc
                own_half = r >= 5 if side == "w" else r <= 4
                if 0 <= r < 10 and 0 <= c < 9 and own_half and self.piece(row + dr // 2, col + dc // 2) == ".":
                    add(r, c)
        elif kind == "a":
            for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
                r, c = row + dr, col + dc
                palace = (7 <= r <= 9 if side == "w" else 0 <= r <= 2) and 3 <= c <= 5
                if palace:
                    add(r, c)
        elif kind == "k":
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                r, c = row + dr, col + dc
                palace = (7 <= r <= 9 if side == "w" else 0 <= r <= 2) and 3 <= c <= 5
                if palace:
                    add(r, c)
            for dr in (-1, 1):
                r = row + dr
                while 0 <= r < 10 and self.piece(r, col) == ".":
                    r += dr
                if 0 <= r < 10 and self.piece(r, col).lower() == "k" and side_of(self.piece(r, col)) != side:
                    add(r, col)
        elif kind == "p":
            forward = -1 if side == "w" else 1
            add(row + forward, col)
            crossed = row <= 4 if side == "w" else row >= 5
            if crossed:
                add(row, col - 1)
                add(row, col + 1)
        return result

    def _apply_unchecked(self, move: str) -> "Board":
        r1, c1, r2, c2 = move_to_squares(move)
        rows = [list(row) for row in self.rows]
        rows[r2][c2] = rows[r1][c1]
        rows[r1][c1] = "."
        return Board(tuple(tuple(row) for row in rows), opponent(self.side))

    def king_square(self, side: str) -> tuple[int, int] | None:
        king = "K" if side == "w" else "k"
        for row in range(10):
            for col in range(9):
                if self.piece(row, col) == king:
                    return row, col
        return None

    def in_check(self, side: str) -> bool:
        square = self.king_square(side)
        if square is None:
            return True
        return bool(self.checking_attackers(side))

    def checking_attackers(self, side: str) -> list[str]:
        square = self.king_square(side)
        if square is None:
            return []
        target = square_to_coord(*square)
        enemy = opponent(side)
        attackers: list[str] = []
        for row in range(10):
            for col in range(9):
                piece = self.piece(row, col)
                if piece != "." and side_of(piece) == enemy:
                    if any(move[2:] == target for move in self._pseudo_from(row, col)):
                        attackers.append(square_to_coord(row, col) + target)
        return attackers

    def legal_moves(self) -> list[str]:
        legal: list[str] = []
        if self.king_square(self.side) is None:
            return legal
        for row in range(10):
            for col in range(9):
                piece = self.piece(row, col)
                if piece != "." and side_of(piece) == self.side:
                    for move in self._pseudo_from(row, col):
                        if not self._apply_unchecked(move).in_check(self.side):
                            legal.append(move)
        return legal

    def play(self, move: str) -> "Board":
        if move not in self.legal_moves():
            raise ValueError("這一步不符合象棋走法")
        return self._apply_unchecked(move)

    def result(self) -> str | None:
        if self.king_square("w") is None:
            return "b"
        if self.king_square("b") is None:
            return "w"
        if not self.legal_moves():
            return opponent(self.side)
        return None


def describe_move(board: Board, move: str) -> str:
    r1, c1, r2, c2 = move_to_squares(move)
    piece = board.piece(r1, c1)
    if piece == ".":
        return move
    name = RED_NAMES.get(piece, BLACK_NAMES.get(piece, piece))
    captured = board.piece(r2, c2)
    target = RED_NAMES.get(captured, BLACK_NAMES.get(captured, captured))
    text = f"{name}從{FILES[c1]}{9-r1}走到{FILES[c2]}{9-r2}"
    return text + (f"，吃{target}" if captured != "." else "")
