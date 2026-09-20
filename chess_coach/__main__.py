"""Start the local-only coach and open its browser page."""

from __future__ import annotations

from pathlib import Path
from threading import Timer
import os
import webbrowser

from . import app
from .db import init_db


def main() -> None:
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    with app.app_context():
        init_db()
    address = "http://127.0.0.1:5111/"
    print(f"Chess Coach running at {address}")
    if os.environ.get("CHESS_COACH_OPEN_BROWSER", "1") == "1":
        Timer(1.0, lambda: webbrowser.open(address)).start()
    app.run(host="127.0.0.1", port=5111, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
