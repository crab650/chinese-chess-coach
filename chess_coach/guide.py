"""Explain verifiable board facts and build non-persistent engine variations."""

from __future__ import annotations

from .engine import Analysis, EngineError
from .rules import Board, RED_NAMES, BLACK_NAMES, describe_move, move_to_squares


def _piece_name(piece: str) -> str:
    return RED_NAMES.get(piece, BLACK_NAMES.get(piece, piece))


def _between_count(board: Board, move: str) -> int | None:
    r1, c1, r2, c2 = move_to_squares(move)
    if r1 != r2 and c1 != c2:
        return None
    dr = (r2 > r1) - (r2 < r1)
    dc = (c2 > c1) - (c2 < c1)
    r, c, count = r1 + dr, c1 + dc, 0
    while (r, c) != (r2, c2):
        count += board.piece(r, c) != "."
        r += dr
        c += dc
    return count


def _focus(board: Board, move: str) -> dict:
    r1, c1, r2, c2 = move_to_squares(move)
    piece = board.piece(r1, c1)
    captured = board.piece(r2, c2)
    next_board = board.play(move)
    attackers = board.checking_attackers(board.side)
    threat = attackers[0] if attackers else None
    threat_straight = False
    if threat:
        ar, ac, _, _ = move_to_squares(threat)
        attacker = board.piece(ar, ac)
        threat_straight = attacker.lower() in ("r", "c", "k") and _between_count(board, threat) is not None
        name = _piece_name(attacker)
        problem = f"眼前的問題：對方的{name}在 {threat[:2]} 對你的帥／將形成將軍。"
        if attacker.lower() == "c" and _between_count(board, threat) == 1:
            problem += "炮吃子時須剛好隔一枚棋子；目前這條線上正好有一枚。"
        if next_board.piece(ar, ac) != attacker:
            solution = f"這步{describe_move(board, move)}，直接吃掉了將軍的棋子。"
        elif next_board.king_square(board.side) != board.king_square(board.side):
            solution = f"這步{describe_move(board, move)}，讓帥／將離開原本受攻擊的位置。"
        elif attacker.lower() == "c" and _between_count(next_board, threat) == 2:
            solution = f"這步{describe_move(board, move)}，讓炮線上變成兩枚隔子；對方的炮無法再沿這條線吃你的帥／將。"
        elif attacker.lower() == "r" and (_between_count(next_board, threat) or 0) > 0:
            solution = f"這步{describe_move(board, move)}，在車和帥／將之間擋住了直線攻擊。"
        else:
            solution = f"這步{describe_move(board, move)}解除了將軍。"
    else:
        problem = "眼前沒有必須立刻應對的將軍。"
        if captured != ".":
            solution = f"這步{describe_move(board, move)}，直接吃掉對方的{_piece_name(captured)}；接著要看對方能否反吃。"
        elif next_board.in_check(next_board.side):
            solution = f"這步{describe_move(board, move)}形成將軍，對方下一步必須先處理帥／將的安全。"
        else:
            solution = f"這步把{_piece_name(piece)}走到 {move[2:]}，沒有立即吃子或將軍。引擎偏好它的後續局面；可以從推演和另一種走法的比較看差別。"
    return {"problem": problem, "solution": solution, "threat_move": threat, "threat_straight": threat_straight}


def _line(board: Board, moves: list[str], human_side: str, first_reason: str) -> list[dict]:
    line: list[dict] = []
    current = board
    for move in moves[:6]:
        if move not in current.legal_moves():
            break
        actor = "human" if current.side == human_side else "computer"
        label = describe_move(current, move)
        next_board = current.play(move)
        if not line:
            explanation = first_reason
        elif actor == "computer":
            explanation = f"對方可能{label}。這是引擎推演的一種回應。"
        else:
            explanation = f"如果對方照剛才那步回應，我們可以考慮{label}。"
        if line and actor == "human" and next_board.in_check(next_board.side):
            explanation += "這步形成將軍。"
        line.append({"move": move, "label": label, "actor": actor, "fen": next_board.to_fen(), "explanation": explanation})
        current = next_board
        if current.result() is not None:
            break
    return line


def _with_plan(reason: str, line: list[dict]) -> str:
    if len(line) >= 3:
        reason += f" 若對方照推演走{line[1]['label']}，我們接著可考慮{line[2]['label']}。"
    elif len(line) >= 2:
        reason += f" 對方可能回應{line[1]['label']}。"
    line[0]["explanation"] = reason
    return reason


def build_guide(board: Board, analysis: Analysis, human_side: str) -> dict:
    if analysis.best_move not in board.legal_moves():
        raise EngineError("引擎回傳不合法的建議走法")
    focus = _focus(board, analysis.best_move)
    reason = focus["problem"] + focus["solution"]
    moves = list(analysis.pv[:6]) if analysis.pv and analysis.pv[0] == analysis.best_move else [analysis.best_move]
    line = _line(board, moves, human_side, reason)
    reason = _with_plan(reason, line)
    return {"fen": board.to_fen(), "best_move": analysis.best_move,
            "best_label": describe_move(board, analysis.best_move), "reason": reason,
            "focus": focus, "line": line, "depth": analysis.depth}


def build_alternative(board: Board, move: str, analysis: Analysis | None, human_side: str) -> dict:
    if move not in board.legal_moves():
        raise ValueError("這一步不符合象棋走法")
    focus = _focus(board, move)
    reason = focus["problem"] + focus["solution"]
    moves = [move]
    if analysis:
        next_board = board.play(move)
        if analysis.best_move in next_board.legal_moves():
            moves += list(analysis.pv[:5]) if analysis.pv and analysis.pv[0] == analysis.best_move else [analysis.best_move]
    line = _line(board, moves, human_side, reason)
    reason = _with_plan(reason, line)
    return {"fen": board.to_fen(), "best_move": move, "best_label": describe_move(board, move),
            "reason": reason, "focus": focus, "line": line, "depth": analysis.depth if analysis else 0}


def compare_guides(board: Board, recommended: dict, alternative: dict,
                   best_analysis: Analysis, alternative_analysis: Analysis | None) -> dict:
    if alternative["best_move"] == recommended["best_move"]:
        summary = "你選的正是推薦走法，可以直接看推演。"
    elif alternative_analysis and best_analysis.score is not None and alternative_analysis.score is not None:
        loss = best_analysis.score + alternative_analysis.score
        if loss >= 150:
            summary = "這次淺層分析認為兩步差距明顯。"
        elif loss >= 60:
            summary = "這次淺層分析較偏好推薦走法。"
        elif loss <= -60:
            summary = "這次淺層分析對兩步的判斷不穩定，無法可靠地說推薦走法更好。"
        else:
            summary = "這次淺層分析認為兩步接近；不能斷言你的想法較差。"
    elif Board.from_fen(alternative["line"][-1]["fen"]).result() == board.side:
        summary = "你選的這步已取得勝利，可以回看它如何結束對局。"
    else:
        summary = "先比較兩條路線的具體回應；目前沒有足夠分數判定優劣。"
    if len(alternative["line"]) >= 2:
        reply = alternative["line"][1]
        before_reply = Board.from_fen(alternative["line"][0]["fen"])
        _, _, r2, c2 = move_to_squares(reply["move"])
        if before_reply.piece(r2, c2) != ".":
            summary += f" 你選的這步後，對方可能{reply['label']}，直接吃子。"
        elif Board.from_fen(reply["fen"]).in_check(board.side):
            summary += f" 你選的這步後，對方可能{reply['label']}，形成將軍。"
        else:
            summary += f" 你選的這步後，對方可能{reply['label']}。"
    return {"fen": board.to_fen(), "summary": summary,
            "recommended": recommended, "alternative": alternative}
