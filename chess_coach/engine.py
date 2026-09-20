"""Short-lived UCCI engine sessions for bounded position analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from time import monotonic
import re
import subprocess


class EngineError(RuntimeError):
    pass


@dataclass(frozen=True)
class Analysis:
    best_move: str
    score: int | None
    pv: tuple[str, ...]
    depth: int
    elapsed_ms: int


class UcciEngine:
    def __init__(self, executable: str | Path, timeout: float = 8.0):
        self.executable = Path(executable).resolve()
        self.timeout = timeout

    def analyze(self, fen: str, depth: int = 5) -> Analysis:
        if not self.executable.is_file():
            raise EngineError(f"找不到象棋引擎：{self.executable}")
        if not 1 <= depth <= 12:
            raise ValueError("搜尋深度超出範圍")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            proc = subprocess.Popen(
                [str(self.executable)],
                cwd=self.executable.parent,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="ascii",
                errors="replace",
                bufsize=1,
                creationflags=flags,
            )
        except OSError as exc:
            raise EngineError(f"象棋引擎無法啟動：{exc}") from exc

        queue: Queue[str | None] = Queue()

        def read_output() -> None:
            assert proc.stdout is not None
            for line in proc.stdout:
                queue.put(line.strip())
            queue.put(None)

        reader = Thread(target=read_output, daemon=True)
        reader.start()
        deadline = monotonic() + self.timeout

        def send(command: str) -> None:
            if proc.poll() is not None:
                raise EngineError("象棋引擎提前結束")
            assert proc.stdin is not None
            try:
                proc.stdin.write(command + "\n")
                proc.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise EngineError("無法傳送指令給象棋引擎") from exc

        def next_line() -> str:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise EngineError("象棋引擎分析逾時")
            try:
                line = queue.get(timeout=remaining)
            except Empty as exc:
                raise EngineError("象棋引擎分析逾時") from exc
            if line is None:
                raise EngineError("象棋引擎未回傳結果就結束")
            return line

        started = monotonic()
        try:
            send("ucci")
            while next_line() != "ucciok":
                pass
            send("setoption usebook false")
            send("position fen " + fen)
            send(f"go depth {depth}")
            score: int | None = None
            pv: tuple[str, ...] = ()
            reached_depth = 0
            while True:
                line = next_line()
                if line.startswith("info "):
                    depth_match = re.search(r"\bdepth\s+(\d+)", line)
                    score_match = re.search(r"\bscore\s+(-?\d+)", line)
                    pv_match = re.search(r"\bpv\s+((?:[a-i][0-9]){2}(?:\s+(?:[a-i][0-9]){2})*)", line)
                    if depth_match and score_match and int(depth_match.group(1)) >= reached_depth:
                        reached_depth = int(depth_match.group(1))
                        score = int(score_match.group(1))
                        pv = tuple(pv_match.group(1).split()) if pv_match else ()
                elif line.startswith("bestmove "):
                    tokens = line.split()
                    if len(tokens) < 2 or not re.fullmatch(r"[a-i][0-9][a-i][0-9]", tokens[1]):
                        raise EngineError("象棋引擎回傳無效走法")
                    return Analysis(tokens[1], score, pv, reached_depth, round((monotonic() - started) * 1000))
                elif line.startswith("nobestmove"):
                    raise EngineError("此局面沒有引擎可走的棋步")
        finally:
            if proc.poll() is None:
                try:
                    send("quit")
                    proc.wait(timeout=1)
                except (EngineError, subprocess.TimeoutExpired):
                    proc.kill()
            proc.wait(timeout=2)
            reader.join(timeout=1)
            if proc.stdin is not None:
                proc.stdin.close()
            if proc.stdout is not None:
                proc.stdout.close()
