"""Flask application factory for the local Xiangqi coach."""

from __future__ import annotations

import os
from pathlib import Path
from flask import Flask, jsonify

from .db import close_db
from .engine import EngineError
from .game import GameError


PACKAGE_DIR = Path(__file__).resolve().parent


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.environ.get("CHESS_COACH_DATABASE", str(Path(app.instance_path) / "chess_coach.db")),
        ENGINE_PATH=os.environ.get("CHESS_COACH_ENGINE", str(PACKAGE_DIR / "engines" / "ELEEYE.EXE")),
        ENGINE_TIMEOUT=float(os.environ.get("CHESS_COACH_ENGINE_TIMEOUT", "8")),
        COACH_DEPTH=int(os.environ.get("CHESS_COACH_COACH_DEPTH", "4")),
        GUIDE_DEPTH=int(os.environ.get("CHESS_COACH_GUIDE_DEPTH", "6")),
        JSON_AS_ASCII=False,
    )
    if test_config:
        app.config.update(test_config)
    app.teardown_appcontext(close_db)

    from .routes import pages, api

    app.register_blueprint(pages)
    app.register_blueprint(api, url_prefix="/api/v1")

    @app.errorhandler(GameError)
    def game_error(error: GameError):
        return jsonify({"error": str(error)}), 400

    @app.errorhandler(EngineError)
    def engine_error(error: EngineError):
        return jsonify({"error": str(error)}), 503

    return app


app = create_app()

__all__ = ["app", "create_app"]
