"""HTML pages and the browser's versioned JSON endpoints."""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from . import game
from .db import get_db
from .game import GameError
from .rules import Board, describe_move


pages = Blueprint("pages", __name__)
api = Blueprint("api", __name__)


def _body() -> dict:
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise GameError("請提供有效的 JSON 資料")
    return value


@pages.get("/")
def home():
    active = get_db().execute("SELECT id FROM games WHERE status = 'playing' ORDER BY id DESC LIMIT 1").fetchone()
    return render_template("home.html", active_game_id=active["id"] if active else None, progress=game.progress())


@pages.get("/play/<int:game_id>")
def play(game_id: int):
    game.state(game_id)
    return render_template("play.html", game_id=game_id)


@pages.get("/review")
def review():
    return render_template("review.html", games=game.list_games())


@pages.get("/review/<int:game_id>")
def review_game(game_id: int):
    snapshot = game.state(game_id)
    rows = get_db().execute("SELECT ply, played_move, best_move, reason FROM mistakes WHERE game_id = ?", (game_id,)).fetchall()
    mistakes = []
    for row in rows:
        board = Board.from_fen(snapshot["history"][row["ply"] - 1]["fen_before"]) if row["ply"] <= len(snapshot["history"]) else None
        if board and snapshot["history"][row["ply"] - 1]["move"] == row["played_move"]:
            mistakes.append({"ply": row["ply"], "reason": row["reason"], "best": describe_move(board, row["best_move"])})
    return render_template("review_game.html", game=snapshot, mistakes=mistakes)


@pages.get("/practice")
def practice():
    return render_template("practice.html", mistakes=game.list_mistakes())


@pages.get("/practice/<int:mistake_id>")
def practice_detail(mistake_id: int):
    row = get_db().execute("SELECT id FROM mistakes WHERE id = ?", (mistake_id,)).fetchone()
    if row is None:
        raise GameError("找不到這道錯題")
    return render_template("practice_detail.html", mistake_id=mistake_id)


@pages.get("/progress")
def progress():
    return render_template("progress.html", progress=game.progress())


@pages.get("/health")
def health():
    return jsonify({"status": "ok"})


@api.post("/games")
def create_game():
    body = _body()
    return jsonify(game.new_game(body.get("human_side", "w"), body.get("level", "beginner"), body.get("coach_mode", "independent"))), 201


@api.get("/games/<int:game_id>")
def get_game(game_id: int):
    return jsonify(game.state(game_id))


@api.post("/games/<int:game_id>/mode")
def set_mode(game_id: int):
    body = _body()
    return jsonify(game.set_coach_mode(game_id, body.get("coach_mode", "")))


@api.get("/games/<int:game_id>/guide")
def guide(game_id: int):
    return jsonify(game.guide_position(game_id))


@api.post("/games/<int:game_id>/opponent-lesson")
def answer_opponent_lesson(game_id: int):
    body = _body()
    return jsonify(game.answer_opponent_lesson(game_id, body.get("ply"), body.get("choice", "")))


@api.post("/games/<int:game_id>/compare")
def compare(game_id: int):
    body = _body()
    return jsonify(game.compare_position(game_id, body.get("move", ""), body.get("fen", "")))


@api.post("/games/<int:game_id>/moves")
def move(game_id: int):
    body = _body()
    return jsonify(game.move_human(game_id, body.get("move", "")))


@api.post("/games/<int:game_id>/retry")
def retry(game_id: int):
    return jsonify(game.retry_move(game_id))


@api.post("/games/<int:game_id>/accept")
def accept(game_id: int):
    return jsonify(game.accept_move(game_id))


@api.get("/mistakes/<int:mistake_id>")
def get_mistake(mistake_id: int):
    row = get_db().execute("SELECT * FROM mistakes WHERE id = ?", (mistake_id,)).fetchone()
    if row is None:
        raise GameError("找不到這道錯題")
    board = Board.from_fen(row["fen_before"])
    return jsonify({"id": row["id"], "fen": row["fen_before"], "legal_moves": board.legal_moves(),
                    "theme": row["theme"], "attempts": row["attempts"], "successes": row["successes"]})


@api.post("/mistakes/<int:mistake_id>/answer")
def answer_mistake(mistake_id: int):
    body = _body()
    return jsonify(game.practice_answer(mistake_id, body.get("move", "")))
