import tempfile
import unittest
import sqlite3
from pathlib import Path
from unittest.mock import patch

from chess_coach import create_app
from chess_coach.db import init_db
from chess_coach.db import get_db
from chess_coach.engine import Analysis
from chess_coach.rules import Board, START_FEN


class DeliberateMistakeEngine:
    def __init__(self):
        self.calls = 0

    def analyze(self, fen, depth):
        self.calls += 1
        board = Board.from_fen(fen)
        if self.calls == 1:
            return Analysis("c3c4", 0, ("c3c4",), depth, 1)
        return Analysis(board.legal_moves()[0], 200, (), depth, 1)


class GameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "DATABASE": str(Path(self.temp.name) / "test.db")})
        self.context = self.app.app_context()
        self.context.push()
        init_db()
        self.client = self.app.test_client()

    def tearDown(self):
        self.context.pop()
        self.temp.cleanup()

    def test_home_and_new_game(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn(b'coach_mode', home.data)
        created = self.client.post("/api/v1/games", json={"human_side": "w", "level": "beginner"})
        self.assertEqual(created.status_code, 201)
        self.assertEqual(len(created.json["legal_moves"]), 44)
        play = self.client.get(f"/play/{created.json['id']}")
        self.assertEqual(play.status_code, 200)
        self.assertIn(b'variationPanel', play.data)
        self.assertIn(b'opponentLesson', play.data)

    def test_real_engine_can_answer_a_move(self):
        created = self.client.post("/api/v1/games", json={"human_side": "w", "level": "beginner"}).json
        move = self.client.post(f"/api/v1/games/{created['id']}/moves", json={"move": "c3c4"})
        self.assertEqual(move.status_code, 200)
        self.assertIsNone(move.json["pending"])
        self.assertEqual(len(move.json["history"]), 2)
        self.assertEqual(move.json["history"][0]["move"], "c3c4")
        self.assertEqual(move.json["history"][1]["actor"], "computer")

    def test_black_side_starts_after_engine_move(self):
        created = self.client.post("/api/v1/games", json={"human_side": "b", "level": "beginner"})
        self.assertEqual(created.status_code, 201)
        self.assertEqual(len(created.json["history"]), 1)
        self.assertEqual(created.json["history"][0]["actor"], "computer")
        self.assertTrue(created.json["legal_moves"])
        self.assertEqual(Board.from_fen(created.json["fen"]).side, "b")

    def test_guided_opponent_question_reveals_and_saves_answer(self):
        created = self.client.post("/api/v1/games", json={"human_side": "w", "level": "beginner", "coach_mode": "guided"}).json
        game_id = created["id"]
        self.assertIsNone(created["opponent_lesson"])
        moved = self.client.post(f"/api/v1/games/{game_id}/moves", json={"move": "c3c4"})
        self.assertEqual(moved.status_code, 200, moved.json)
        lesson = moved.json["opponent_lesson"]
        self.assertIsNotNone(lesson)
        self.assertFalse(lesson["answered"])
        self.assertEqual(lesson["ply"], 2)
        self.assertNotIn("answer", lesson)
        self.assertEqual(len(lesson["options"]), 4)
        self.assertEqual(self.client.post(f"/api/v1/games/{game_id}/opponent-lesson",
                                          json={"ply": 1, "choice": "unsure"}).status_code, 400)
        answered = self.client.post(f"/api/v1/games/{game_id}/opponent-lesson",
                                    json={"ply": lesson["ply"], "choice": "unsure"})
        self.assertEqual(answered.status_code, 200, answered.json)
        revealed = answered.json["opponent_lesson"]
        self.assertTrue(revealed["answered"])
        self.assertEqual(revealed["choice"], "unsure")
        self.assertTrue(revealed["answer"])
        self.assertTrue(revealed["explanation"])
        self.assertEqual(answered.json["fen"], moved.json["fen"])
        self.assertEqual(answered.json["history"], moved.json["history"])
        self.assertEqual(self.client.get(f"/api/v1/games/{game_id}").json["opponent_lesson"], revealed)

    def test_black_guided_game_gets_question_after_opening_move(self):
        created = self.client.post("/api/v1/games", json={"human_side": "b", "level": "beginner", "coach_mode": "guided"})
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json["opponent_lesson"]["ply"], 1)
        self.assertFalse(created.json["opponent_lesson"]["answered"])

    def test_guided_line_is_legal_and_does_not_change_the_game(self):
        created = self.client.post("/api/v1/games", json={"human_side": "w", "level": "beginner", "coach_mode": "guided"}).json
        game_id = created["id"]
        response = self.client.get(f"/api/v1/games/{game_id}/guide")
        self.assertEqual(response.status_code, 200, response.json)
        guide = response.json
        self.assertEqual(guide["fen"], created["fen"])
        self.assertEqual(guide["line"][0]["move"], guide["best_move"])
        self.assertGreaterEqual(len(guide["line"]), 2)
        self.assertTrue(guide["reason"])
        self.assertIn(guide["line"][1]["label"], guide["reason"])
        board = Board.from_fen(created["fen"])
        for step in guide["line"]:
            self.assertIn(step["move"], board.legal_moves())
            board = board.play(step["move"])
            self.assertEqual(board.to_fen(), step["fen"])
        candidate = "a3a4" if guide["best_move"] != "a3a4" else "c3c4"
        compared = self.client.post(f"/api/v1/games/{game_id}/compare",
                                    json={"move": candidate, "fen": created["fen"]})
        self.assertEqual(compared.status_code, 200, compared.json)
        self.assertEqual(compared.json["alternative"]["best_move"], candidate)
        self.assertEqual(compared.json["recommended"]["best_move"], guide["best_move"])
        self.assertTrue(compared.json["summary"])
        for branch in ("recommended", "alternative"):
            board = Board.from_fen(created["fen"])
            for step in compared.json[branch]["line"]:
                self.assertIn(step["move"], board.legal_moves())
                board = board.play(step["move"])
                self.assertEqual(step["fen"], board.to_fen())
        self.assertEqual(self.client.post(f"/api/v1/games/{game_id}/compare",
                                          json={"move": "a0a9", "fen": created["fen"]}).status_code, 400)
        self.assertEqual(self.client.post(f"/api/v1/games/{game_id}/compare",
                                          json={"move": candidate, "fen": "old"}).status_code, 400)
        unchanged = self.client.get(f"/api/v1/games/{game_id}").json
        self.assertEqual(unchanged["fen"], created["fen"])
        self.assertEqual(unchanged["history"], [])
        switched = self.client.post(f"/api/v1/games/{game_id}/mode", json={"coach_mode": "independent"})
        self.assertEqual(switched.json["coach_mode"], "independent")
        self.assertEqual(self.client.get(f"/api/v1/games/{game_id}").json["coach_mode"], "independent")
        self.assertEqual(self.client.get(f"/api/v1/games/{game_id}/guide").status_code, 400)

    def test_existing_database_is_migrated(self):
        path = Path(self.temp.name) / "legacy.db"
        with sqlite3.connect(path) as connection:
            connection.execute("CREATE TABLE games (id INTEGER PRIMARY KEY, created_at TEXT, updated_at TEXT, human_side TEXT, level TEXT, status TEXT, fen TEXT, history_json TEXT, pending_json TEXT)")
            connection.execute("INSERT INTO games VALUES (1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'w', 'beginner', 'playing', ?, '[]', NULL)", (START_FEN,))
        connection.close()
        old_app = create_app({"TESTING": True, "DATABASE": str(path)})
        with old_app.app_context():
            init_db()
            self.assertEqual(get_db().execute("SELECT coach_mode FROM games WHERE id = 1").fetchone()[0], "independent")
            self.assertIsNotNone(get_db().execute("SELECT name FROM sqlite_master WHERE name = 'opponent_lessons'").fetchone())

    def test_pending_hint_retry_accept_and_practice(self):
        created = self.client.post("/api/v1/games", json={"human_side": "w", "level": "beginner"}).json
        game_id = created["id"]
        fake = DeliberateMistakeEngine()
        with patch("chess_coach.game._engine", return_value=fake):
            pending = self.client.post(f"/api/v1/games/{game_id}/moves", json={"move": "a3a4"})
            self.assertEqual(pending.status_code, 200)
            self.assertIsNotNone(pending.json["pending"])
            self.assertEqual(pending.json["fen"], created["fen"])
            self.assertEqual(pending.json["legal_moves"], [])
            self.assertIn(b'pendingBoardActions', self.client.get(f"/play/{game_id}").data)
            mistake_id = pending.json["pending"]["mistake_id"]
            retry = self.client.post(f"/api/v1/games/{game_id}/retry", json={})
            self.assertIsNone(retry.json["pending"])
            fake.calls = 0
            pending = self.client.post(f"/api/v1/games/{game_id}/moves", json={"move": "a3a4"})
            accepted = self.client.post(f"/api/v1/games/{game_id}/accept", json={})
            self.assertEqual(accepted.status_code, 200, accepted.json)
            self.assertEqual(len(accepted.json["history"]), 2)
            self.assertEqual(self.client.get(f"/review/{game_id}").status_code, 200)
            self.assertEqual(self.client.get("/practice").status_code, 200)
            self.assertEqual(self.client.get(f"/practice/{mistake_id}").status_code, 200)
            answer = self.client.post(f"/api/v1/mistakes/{mistake_id}/answer", json={"move": "c3c4"})
            self.assertTrue(answer.json["correct"])
            self.assertEqual(self.client.get("/progress").status_code, 200)
            self.assertEqual(self.client.get("/api/v1/mistakes/" + str(mistake_id)).json["attempts"], 1)

        # Reopening with the same SQLite file must retain the game and practice result.
        second = create_app({"TESTING": True, "DATABASE": self.app.config["DATABASE"]})
        with second.test_client() as client:
            saved = client.get(f"/api/v1/games/{game_id}")
            self.assertEqual(saved.status_code, 200)
            self.assertEqual(len(saved.json["history"]), 2)
            self.assertEqual(client.get("/progress").status_code, 200)
            self.assertEqual(client.get(f"/api/v1/mistakes/{mistake_id}").json["successes"], 1)

    def test_illegal_move_does_not_change_game(self):
        created = self.client.post("/api/v1/games", json={"human_side": "w", "level": "beginner"}).json
        result = self.client.post(f"/api/v1/games/{created['id']}/moves", json={"move": "a0a9"})
        self.assertEqual(result.status_code, 400)
        current = self.client.get(f"/api/v1/games/{created['id']}").json
        self.assertEqual(current["fen"], created["fen"])
        self.assertEqual(current["history"], [])

    def test_check_is_explained_in_game_state(self):
        created = self.client.post("/api/v1/games", json={"human_side": "w", "level": "beginner"}).json
        checked_fen = "4k4/9/9/9/9/4r4/9/9/9/4K4 w - - 0 1"
        db = get_db()
        with db:
            db.execute("UPDATE games SET fen = ? WHERE id = ?", (checked_fen, created["id"]))
        state = self.client.get(f"/api/v1/games/{created['id']}").json
        self.assertTrue(state["in_check"])
        self.assertEqual(state["checked_king"], "e0")
        self.assertNotIn("e0e1", state["legal_moves"])


if __name__ == "__main__":
    unittest.main()
