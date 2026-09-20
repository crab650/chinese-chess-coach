"""Smoke-test the bundled ElephantEye UCCI engine without changing project data."""

from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from time import monotonic
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1] / "references" / "xqwizard_source"
ENGINE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "ELEEYE.EXE"


def main() -> int:
    if not ENGINE.is_file():
        print(f"Missing engine: {ENGINE}", file=sys.stderr)
        return 1

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.Popen(
        [str(ENGINE)],
        cwd=ENGINE.parent,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="ascii",
        errors="replace",
        bufsize=1,
        creationflags=flags,
    )
    lines: Queue[str | None] = Queue()

    def read_output() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.put(line.rstrip("\r\n"))
        lines.put(None)

    Thread(target=read_output, daemon=True).start()

    def send(command: str) -> None:
        assert proc.stdin is not None
        print(f"> {command}")
        proc.stdin.write(command + "\n")
        proc.stdin.flush()

    def wait_for(prefix: str, seconds: float) -> bool:
        deadline = monotonic() + seconds
        while monotonic() < deadline:
            try:
                line = lines.get(timeout=min(0.5, max(0.01, deadline - monotonic())))
            except Empty:
                if proc.poll() is not None:
                    break
                continue
            if line is None:
                break
            print(f"< {line}")
            if line.startswith(prefix):
                return True
        return False

    try:
        send("ucci")
        if not wait_for("ucciok", 10):
            print("No ucciok response", file=sys.stderr)
            return 2
        send("setoption usebook false")
        send("position startpos")
        send("go depth 3")
        if not wait_for("bestmove ", 20):
            print("No bestmove response", file=sys.stderr)
            return 3
        send("quit")
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Engine did not exit after quit", file=sys.stderr)
            return 4
        print(f"Exit code: {proc.returncode}")
        return 0 if proc.returncode == 0 else 5
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
