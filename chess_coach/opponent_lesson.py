"""Beginner question about the most recent computer move."""

from __future__ import annotations

from .rules import Board, BLACK_NAMES, RED_NAMES, describe_move, move_to_squares


CHOICES = {
    "check": "正在將軍",
    "capture": "吃子或捉子",
    "quiet": "調整棋子位置",
    "unsure": "我還看不出來",
}

PIECE_VALUES = {"R": 9, "C": 5, "N": 4, "B": 2, "A": 2, "P": 1}


def _name(piece: str) -> str:
    return RED_NAMES.get(piece, BLACK_NAMES.get(piece, piece))


def _straight(move: str, piece: str) -> bool:
    return piece.lower() in ("r", "c", "k") and (move[0] == move[2] or move[1] == move[3])


def inspect_move(fen_before: str, move: str, human_side: str) -> dict:
    before = Board.from_fen(fen_before)
    if move not in before.legal_moves() or before.side == human_side:
        raise ValueError("無法分析這一步電腦走法")
    after = before.play(move)
    r1, c1, r2, c2 = move_to_squares(move)
    moved_piece = before.piece(r1, c1)
    captured = before.piece(r2, c2)
    label = describe_move(before, move)
    attackers = after.checking_attackers(human_side)

    if attackers:
        threat = attackers[0]
        ar, ac, _, _ = move_to_squares(threat)
        attacker = after.piece(ar, ac)
        explanation = f"電腦這步{label}。現在{_name(attacker)}在 {threat[:2]} 將軍；你下一步必須先解除將軍。"
        if captured != ".":
            explanation += f"這步同時吃掉了你的{_name(captured)}。"
        category = "check"
        highlights = [threat[:2], threat[2:]]
        threat_straight = _straight(threat, attacker)
    elif captured != ".":
        category = "capture"
        threat = move
        threat_straight = _straight(move, moved_piece)
        highlights = [move[:2], move[2:]]
        explanation = f"電腦這步{label}，已經吃掉你的{_name(captured)}。走下一步前，先看看還有沒有棋子受攻擊。"
    else:
        # Ask whether the piece just moved could capture on its next turn.
        # This describes a concrete threat, without claiming it is forced.
        opponent_turn = Board(after.rows, before.side)
        captures = []
        for candidate in opponent_turn.legal_moves():
            if candidate[:2] != move[2:]:
                continue
            tr, tc = move_to_squares(candidate)[2:]
            target = after.piece(tr, tc)
            if target != "." and target.lower() != "k":
                captures.append((PIECE_VALUES.get(target.upper(), 0), candidate, target))
        if captures:
            _, threat, target = max(captures)
            category = "capture"
            highlights = [threat[:2], threat[2:]]
            threat_straight = _straight(threat, moved_piece)
            explanation = (f"電腦這步{label}。如果你不處理，剛移動的{_name(moved_piece)}"
                           f"下一步可能從 {threat[:2]} 到 {threat[2:]} 吃你的{_name(target)}。")
        else:
            category = "quiet"
            threat = None
            threat_straight = False
            highlights = [move[:2], move[2:]]
            explanation = (f"電腦這步{label}。它沒有立即將軍或吃子；"
                           "目前也沒有看到剛移動的棋子下一步能直接吃你的棋子。先留意它的新位置。")

    return {"category": category, "answer": CHOICES[category], "explanation": explanation,
            "highlights": highlights, "threat_move": threat, "threat_straight": threat_straight}
