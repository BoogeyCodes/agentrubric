"""Persist scored evaluations and aggregate agents across them into a leaderboard.

The store is dependency-free (it uses the standard-library ``sqlite3`` module) so it stays part of
agentrubric's core. The web service builds on it, but you can use it on its own to keep a running
record of evaluations and compare how agents do over many tasks.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from agentrubric.models import Evaluation
from agentrubric.rubric import DEFAULT_RUBRIC, Rubric, rubric_from_dict, rubric_to_dict
from agentrubric.scoring import RankedRun, ScoredEvaluation, score_evaluation

_SCHEMA = """
CREATE TABLE IF NOT EXISTS evaluations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    task       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    winner     TEXT NOT NULL,
    margin     REAL NOT NULL DEFAULT 0,
    rubric     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_id INTEGER NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE,
    agent         TEXT NOT NULL,
    overall       REAL NOT NULL,
    rank          INTEGER NOT NULL,
    tied          INTEGER NOT NULL,
    scores        TEXT NOT NULL,
    rationale     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_evaluation ON runs(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_runs_agent ON runs(agent);
"""


@dataclass(frozen=True)
class StoredEvaluation:
    """A scored evaluation read back from the store, with its id and timestamp."""

    id: int
    created_at: str
    rubric: Rubric
    scored: ScoredEvaluation

    @property
    def task(self) -> str:
        return self.scored.task


@dataclass(frozen=True)
class EvaluationSummary:
    """A one-line summary of a stored evaluation, for list views."""

    id: int
    task: str
    created_at: str
    winner: str
    margin: float
    run_count: int


@dataclass(frozen=True)
class LeaderboardRow:
    """One agent's record aggregated across every stored evaluation."""

    agent: str
    evaluations: int
    wins: int
    average: float
    best: float
    worst: float

    @property
    def win_rate(self) -> float:
        """Share of evaluations this agent won outright or tied for first (0-1)."""
        return round(self.wins / self.evaluations, 3) if self.evaluations else 0.0


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class EvaluationStore:
    """A SQLite-backed record of scored evaluations.

    Use it as a context manager, or call :meth:`close` when done. Pass ``":memory:"`` for an
    ephemeral in-process store (handy in tests).
    """

    def __init__(self, path: str | Path = "agentrubric.db") -> None:
        # check_same_thread=False + a lock so the web server (which runs sync handlers in a
        # threadpool) can share one connection safely.
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # -- lifecycle -------------------------------------------------------
    def __enter__(self) -> EvaluationStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    # -- writes ----------------------------------------------------------
    def add(self, evaluation: Evaluation) -> StoredEvaluation:
        """Score an evaluation and store it. Returns the stored, scored record."""
        scored = score_evaluation(evaluation)
        return self.add_scored(scored, evaluation.rubric)

    def add_scored(self, scored: ScoredEvaluation, rubric: Rubric = DEFAULT_RUBRIC) -> StoredEvaluation:
        created_at = _now()
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO evaluations (task, created_at, winner, margin, rubric) VALUES (?, ?, ?, ?, ?)",
                (scored.task, created_at, scored.winner.agent, scored.margin, json.dumps(rubric_to_dict(rubric))),
            )
            eval_id = int(cur.lastrowid)
            self._conn.executemany(
                "INSERT INTO runs (evaluation_id, agent, overall, rank, tied, scores, rationale) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (eval_id, r.agent, r.overall, r.rank, int(r.tied), json.dumps(r.scores), r.rationale)
                    for r in scored.runs
                ],
            )
            self._conn.commit()
        return StoredEvaluation(id=eval_id, created_at=created_at, rubric=rubric, scored=scored)

    def delete(self, eval_id: int) -> bool:
        """Delete an evaluation (and its runs). Returns True if a row was removed."""
        with self._lock:
            cur = self._conn.execute("DELETE FROM evaluations WHERE id = ?", (eval_id,))
            self._conn.commit()
            return cur.rowcount > 0

    # -- reads -----------------------------------------------------------
    def get(self, eval_id: int) -> StoredEvaluation | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM evaluations WHERE id = ?", (eval_id,)).fetchone()
            if row is None:
                return None
            run_rows = self._conn.execute(
                "SELECT * FROM runs WHERE evaluation_id = ? ORDER BY rank, agent", (eval_id,)
            ).fetchall()
        runs = [
            RankedRun(
                agent=rr["agent"],
                overall=rr["overall"],
                rank=rr["rank"],
                tied=bool(rr["tied"]),
                scores=json.loads(rr["scores"]),
                rationale=rr["rationale"],
            )
            for rr in run_rows
        ]
        scored = ScoredEvaluation(task=row["task"], runs=runs)
        return StoredEvaluation(
            id=row["id"],
            created_at=row["created_at"],
            rubric=rubric_from_dict(json.loads(row["rubric"])),
            scored=scored,
        )

    def list(self, limit: int = 100, offset: int = 0) -> list[EvaluationSummary]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT e.id, e.task, e.created_at, e.winner, e.margin,
                       (SELECT COUNT(*) FROM runs r WHERE r.evaluation_id = e.id) AS run_count
                FROM evaluations e
                ORDER BY e.id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [
            EvaluationSummary(
                id=r["id"],
                task=r["task"],
                created_at=r["created_at"],
                winner=r["winner"],
                margin=r["margin"],
                run_count=r["run_count"],
            )
            for r in rows
        ]

    def count(self) -> int:
        with self._lock:
            return int(self._conn.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0])

    def leaderboard(self, min_evaluations: int = 1) -> list[LeaderboardRow]:
        """Aggregate every agent across all stored evaluations, best average first.

        ``wins`` counts evaluations where the agent placed first (including ties for first).
        """
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT agent,
                       COUNT(*)                         AS evaluations,
                       SUM(CASE WHEN rank = 1 THEN 1 ELSE 0 END) AS wins,
                       AVG(overall)                     AS average,
                       MAX(overall)                     AS best,
                       MIN(overall)                     AS worst
                FROM runs
                GROUP BY agent
                HAVING COUNT(*) >= ?
                ORDER BY average DESC, wins DESC, agent ASC
                """,
                (min_evaluations,),
            ).fetchall()
        return [
            LeaderboardRow(
                agent=r["agent"],
                evaluations=r["evaluations"],
                wins=r["wins"],
                average=round(r["average"], 2),
                best=round(r["best"], 1),
                worst=round(r["worst"], 1),
            )
            for r in rows
        ]
