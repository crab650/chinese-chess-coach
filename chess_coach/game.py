"""Game, coaching, and practice workflows independent of HTTP routes."""

from __future__ import annotations

import json

from flask import current_app

from .db import get_db
from .engine import Analysis, EngineError, UcciEngine
from .guide import build_alternative, build_guide, compare_guides
from .opponent_lesson import CHOICES, inspect_move
from .rules import Board, START_FEN, describe_move, move_to_squares, square_to_coord


LEVEL_DEPTH = {"beginner": 2, "normal": 3, "challenge": 4}
COACH_MODES = {"independent", "guided"}
MISTAKE_THRESHOLD = 110


class GameError(ValueError):
    pass


def _engine() -> UcciEngine:
    return UcciEngine(current_app.config["ENGINE_PATH"], current_app.config["ENGINE_TIMEOUT"])


def _read_game(game_id: int):
    row = get_db().execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    if row is None:
        raise GameError("找不到這盤棋")
    return row


def _history(row) -> list[dict]:
    return json.loads(row["history_json"])


def _pending(row) -> dict | None:
    return json.loads(row["pending_json"]) if row["pending_json"] else None


def _opponent_lesson(row, history: list[dict], pending: dict | None) -> dict | None:
    if row["coach_mode"] != "guided" or pending or not history or history[-1]["actor"] != "computer":
        return None
    last = history[-1]
    detail = inspect_move(last["fen_before"], last["move"], row["human_side"])
    ply = len(history)
    answer = get_db().execute(
        "SELECT choice, correct FROM opponent_lessons WHERE game_id = ? AND ply = ?",
        (row["id"], ply),
    ).fetchone()
    lesson = {"ply": ply, "move_label": last["label"],
              "question": "電腦剛走這一步，你覺得它最直接的目的或效果是什麼？",
              "options": CHOICES, "answered": answer is not None}
    if answer:
        lesson.update(detail)
        lesson.update({"choice": answer["choice"], "correct": bool(answer["correct"])})
    return lesson


def _status(board: Board, human_side: str) -> str:
    winner = board.result()
    if winner is None:
        return "playing"
    return "won" if winner == human_side else "lost"


def _record(history: list[dict], board: Board, move: str, actor: str) -> Board:
    history.append({"fen_before": board.to_fen(), "move": move, "actor": actor, "label": describe_move(board, move)})
    return board.play(move)


def _computer_reply(board: Board, level: str, history: list[dict]) -> Board:
    if board.result() is not None:
        return board
    analysis = _engine().analyze(board.to_fen(), LEVEL_DEPTH[level])
    if analysis.best_move not in board.legal_moves():
        raise EngineError("引擎回傳不合法的走法")
    return _record(history, board, analysis.best_move, "computer")


def _coach_feedback(board: Board, played: str, best: Analysis, after: Analysis, loss: int) -> dict:
    result = board.play(played)
    reply = after.best_move if after.best_move in result.legal_moves() else None
    theme = "局面判斷"
    reason = "這步之後對方有較強的回應，先檢查對方下一步想做什麼。"
    first = "先找出對方下一步最直接的威脅。"
    second = "看看對方下一步可以走到哪個位置。"
    highlights: list[str] = []
    if reply:
        r1, c1, r2, c2 = move_to_squares(reply)
        captured = result.piece(r2, c2)
        if captured != ".":
            theme = "失子"
            reason = "對方可以立即" + describe_move(result, reply) + "。"
            first = "先看看對方現在能吃掉你哪個棋子。"
            second = "留意被攻擊的棋子，以及對方的吃子路線。"
            highlights = [reply[:2], reply[2:]]
        elif result.play(reply).in_check(board.side):
            theme = "將軍威脅"
            reason = "對方接著可以" + describe_move(result, reply) + "，形成將軍。"
            first = "先檢查對方有沒有直接將軍。"
            second = "注意對方將軍的起點與落點。"
            highlights = [reply[:2], reply[2:]]
    if best.pv and len(best.pv) > 1:
        best_board = board.play(best.best_move)
        continuation = best.pv[1]
        followup = "；對方可能" + describe_move(best_board, continuation) if continuation in best_board.legal_moves() else ""
    else:
        followup = ""
    third = "可以試試" + describe_move(board, best.best_move) + followup + "。"
    return {
        "played_move": played,
        "best_move": best.best_move,
        "best_score": best.score,
        "score_loss": loss,
        "theme": theme,
        "reason": reason,
        "hints": [first, second, third],
        "highlights": highlights,
        "display_fen": result.to_fen(),
    }


def state(game_id: int) -> dict:
    row = _read_game(game_id)
    board = Board.from_fen(row["fen"])
    pending = _pending(row)
    history = _history(row)
    king = board.king_square(row["human_side"])
    checked = row["status"] == "playing" and board.side == row["human_side"] and board.in_check(row["human_side"])
    return {
        "id": row["id"],
        "human_side": row["human_side"],
        "level": row["level"],
        "coach_mode": row["coach_mode"],
        "status": row["status"],
        "fen": row["fen"],
        "display_fen": pending["display_fen"] if pending else row["fen"],
        "in_check": checked,
        "checked_king": square_to_coord(*king) if checked and king else None,
        "legal_moves": board.legal_moves() if row["status"] == "playing" and board.side == row["human_side"] and not pending else [],
        "history": history,
        "pending": pending,
        "opponent_lesson": _opponent_lesson(row, history, pending),
    }


def answer_opponent_lesson(game_id: int, ply: int, choice: str) -> dict:
    if choice not in CHOICES:
        raise GameError("請選擇一個答案")
    row = _read_game(game_id)
    history = _history(row)
    lesson = _opponent_lesson(row, history, _pending(row))
    if not lesson or lesson["ply"] != ply:
        raise GameError("這道題已不是目前的局面，請重新整理")
    detail = inspect_move(history[-1]["fen_before"], history[-1]["move"], row["human_side"])
    correct = choice == detail["category"]
    db = get_db()
    with db:
        db.execute("INSERT OR IGNORE INTO opponent_lessons (game_id, ply, choice, correct) VALUES (?, ?, ?, ?)",
                   (game_id, ply, choice, int(correct)))
    return state(game_id)


def new_game(human_side: str = "w", level: str = "beginner", coach_mode: str = "independent") -> dict:
    if human_side not in ("w", "b") or level not in LEVEL_DEPTH or coach_mode not in COACH_MODES:
        raise GameError("對局設定無效")
    board = Board.from_fen(START_FEN)
    history: list[dict] = []
    if human_side == "b":
        board = _computer_reply(board, level, history)
    db = get_db()
    with db:
        cursor = db.execute(
            "INSERT INTO games (human_side, level, coach_mode, status, fen, history_json) VALUES (?, ?, ?, ?, ?, ?)",
            (human_side, level, coach_mode, "playing", board.to_fen(), json.dumps(history, ensure_ascii=False)),
        )
    return state(cursor.lastrowid)


def set_coach_mode(game_id: int, mode: str) -> dict:
    if mode not in COACH_MODES:
        raise GameError("教學模式無效")
    _read_game(game_id)
    db = get_db()
    with db:
        db.execute("UPDATE games SET coach_mode = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (mode, game_id))
    return state(game_id)


def guide_position(game_id: int) -> dict:
    row = _read_game(game_id)
    if row["coach_mode"] != "guided":
        raise GameError("請先切換到大師帶走模式")
    if row["status"] != "playing" or _pending(row):
        raise GameError("目前不能分析下一步")
    board = Board.from_fen(row["fen"])
    if board.side != row["human_side"]:
        raise GameError("還沒輪到你走棋")
    analysis = _engine().analyze(board.to_fen(), current_app.config["GUIDE_DEPTH"])
    return build_guide(board, analysis, row["human_side"])


def compare_position(game_id: int, move: str, expected_fen: str) -> dict:
    row = _read_game(game_id)
    if row["coach_mode"] != "guided" or row["status"] != "playing" or _pending(row):
        raise GameError("目前不能比較走法")
    if row["fen"] != expected_fen:
        raise GameError("棋局已更新，請重新整理")
    board = Board.from_fen(row["fen"])
    if board.side != row["human_side"] or move not in board.legal_moves():
        raise GameError("請選一個合法的走法")
    engine = _engine()
    depth = current_app.config["GUIDE_DEPTH"]
    best_analysis = engine.analyze(board.to_fen(), depth)
    recommended = build_guide(board, best_analysis, row["human_side"])
    alternative_analysis = None
    if move != best_analysis.best_move and board.play(move).result() is None:
        alternative_board = board.play(move)
        alternative_analysis = engine.analyze(alternative_board.to_fen(), depth)
        if alternative_analysis.best_move not in alternative_board.legal_moves():
            raise EngineError("引擎回傳不合法的對方走法")
    alternative = recommended if move == best_analysis.best_move else build_alternative(board, move, alternative_analysis, row["human_side"])
    return compare_guides(board, recommended, alternative, best_analysis, alternative_analysis)


def move_human(game_id: int, move: str) -> dict:
    row = _read_game(game_id)
    if row["status"] != "playing" or _pending(row):
        raise GameError("目前不能走棋")
    board = Board.from_fen(row["fen"])
    if board.side != row["human_side"]:
        raise GameError("還沒輪到你走棋")
    if move not in board.legal_moves():
        raise GameError("這一步不符合象棋走法")
    after_board = board.play(move)

    if after_board.result() is None:
        try:
            engine = _engine()
            depth = current_app.config["COACH_DEPTH"]
            before = engine.analyze(board.to_fen(), depth)
            after = engine.analyze(after_board.to_fen(), depth)
            if before.score is not None and after.score is not None and before.best_move in board.legal_moves():
                loss = before.score + after.score
                if loss >= MISTAKE_THRESHOLD and move != before.best_move:
                    pending = _coach_feedback(board, move, before, after, loss)
                    db = get_db()
                    with db:
                        ply = len(_history(row)) + 1
                        existing = db.execute("SELECT id FROM mistakes WHERE game_id = ? AND ply = ? AND played_move = ?", (game_id, ply, move)).fetchone()
                        if existing:
                            pending["mistake_id"] = existing["id"]
                        else:
                            cursor = db.execute(
                                "INSERT INTO mistakes (game_id, ply, fen_before, played_move, best_move, best_score, score_loss, reason, theme) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (game_id, ply, board.to_fen(), move, before.best_move, before.score, loss, pending["reason"], pending["theme"]),
                            )
                            pending["mistake_id"] = cursor.lastrowid
                        cursor = db.execute("UPDATE games SET pending_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND fen = ? AND pending_json IS NULL",
                                            (json.dumps(pending, ensure_ascii=False), game_id, row["fen"]))
                        if cursor.rowcount != 1:
                            raise GameError("棋局已更新，請重新整理")
                    return state(game_id)
        except EngineError:
            # The move can still be played; the opponent analysis below reports
            # an error if the engine is unavailable altogether.
            pass

    history = _history(row)
    next_board = _record(history, board, move, "human")
    next_board = _computer_reply(next_board, row["level"], history)
    db = get_db()
    with db:
        cursor = db.execute(
            "UPDATE games SET fen = ?, status = ?, history_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND fen = ? AND pending_json IS NULL",
            (next_board.to_fen(), _status(next_board, row["human_side"]), json.dumps(history, ensure_ascii=False), game_id, row["fen"]),
        )
        if cursor.rowcount != 1:
            raise GameError("棋局已更新，請重新整理")
    return state(game_id)


def retry_move(game_id: int) -> dict:
    row = _read_game(game_id)
    if not _pending(row):
        raise GameError("目前沒有可重走的棋步")
    db = get_db()
    with db:
        db.execute("UPDATE games SET pending_json = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (game_id,))
    return state(game_id)


def accept_move(game_id: int) -> dict:
    row = _read_game(game_id)
    pending = _pending(row)
    if not pending:
        raise GameError("目前沒有待確認的棋步")
    board = Board.from_fen(row["fen"])
    history = _history(row)
    next_board = _record(history, board, pending["played_move"], "human")
    next_board = _computer_reply(next_board, row["level"], history)
    db = get_db()
    with db:
        cursor = db.execute(
            "UPDATE games SET fen = ?, status = ?, history_json = ?, pending_json = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND fen = ? AND pending_json IS NOT NULL",
            (next_board.to_fen(), _status(next_board, row["human_side"]), json.dumps(history, ensure_ascii=False), game_id, row["fen"]),
        )
        if cursor.rowcount != 1:
            raise GameError("棋局已更新，請重新整理")
    return state(game_id)


def list_games() -> list[dict]:
    rows = get_db().execute("SELECT id, created_at, updated_at, human_side, level, status, history_json FROM games ORDER BY id DESC LIMIT 50").fetchall()
    return [{"id": row["id"], "created_at": row["created_at"], "updated_at": row["updated_at"],
             "human_side": row["human_side"], "level": row["level"], "status": row["status"],
             "moves": len(json.loads(row["history_json"]))} for row in rows]


def list_mistakes() -> list[dict]:
    rows = get_db().execute("SELECT * FROM mistakes ORDER BY id DESC LIMIT 100").fetchall()
    return [dict(row) for row in rows]


def practice_answer(mistake_id: int, move: str) -> dict:
    db = get_db()
    row = db.execute("SELECT * FROM mistakes WHERE id = ?", (mistake_id,)).fetchone()
    if row is None:
        raise GameError("找不到這道錯題")
    board = Board.from_fen(row["fen_before"])
    if move not in board.legal_moves():
        raise GameError("這一步不符合象棋走法")
    correct = move == row["best_move"]
    if not correct and row["best_score"] is not None:
        try:
            result = _engine().analyze(board.play(move).to_fen(), current_app.config["COACH_DEPTH"])
            correct = result.score is not None and row["best_score"] + result.score <= 50
        except EngineError:
            pass
    with db:
        db.execute(
            "UPDATE mistakes SET attempts = attempts + 1, successes = successes + ?, last_practiced_at = CURRENT_TIMESTAMP WHERE id = ?",
            (1 if correct else 0, mistake_id),
        )
    return {"correct": correct, "best_move": row["best_move"], "best_description": describe_move(board, row["best_move"]),
            "reason": row["reason"], "played_description": describe_move(board, move)}


def progress() -> dict:
    db = get_db()
    games = db.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    mistakes = db.execute("SELECT COUNT(*), COALESCE(SUM(attempts), 0), COALESCE(SUM(successes), 0) FROM mistakes").fetchone()
    themes = db.execute("SELECT theme, COUNT(*) AS count FROM mistakes GROUP BY theme ORDER BY count DESC").fetchall()
    return {"games": games, "mistakes": mistakes[0], "attempts": mistakes[1], "successes": mistakes[2],
            "themes": [dict(row) for row in themes]}
