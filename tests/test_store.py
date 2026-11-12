from __future__ import annotations

from agentrubric.models import from_dict
from agentrubric.store import EvaluationStore

DIMS = [
    "instruction_following", "correctness", "testing", "completeness", "efficiency",
    "code_quality", "safety", "honesty", "tool_use", "communication",
]


def _run(agent: str, value: int, rationale: str = "") -> dict:
    return {"agent": agent, "scores": {d: value for d in DIMS}, "rationale": rationale}


def _eval(task: str, runs: list[dict]) -> object:
    return from_dict({"task": task, "runs": runs})


def test_add_get_roundtrip():
    with EvaluationStore(":memory:") as store:
        stored = store.add(_eval("fix the bug", [_run("alpha", 5, "clean"), _run("bravo", 3, "ok")]))
        assert stored.id == 1
        got = store.get(stored.id)
        assert got is not None
        assert got.task == "fix the bug"
        assert got.scored.winner.agent == "alpha"
        assert got.scored.runs[0].rationale == "clean"
        # rubric was persisted and rebuilt
        assert len(got.rubric.dimensions) == 10


def test_list_and_count():
    with EvaluationStore(":memory:") as store:
        store.add(_eval("t1", [_run("alpha", 5)]))
        store.add(_eval("t2", [_run("alpha", 4)]))
        assert store.count() == 2
        summaries = store.list()
        assert [s.id for s in summaries] == [2, 1]  # newest first
        assert summaries[0].task == "t2"
        assert summaries[0].run_count == 1


def test_delete():
    with EvaluationStore(":memory:") as store:
        stored = store.add(_eval("t", [_run("alpha", 5)]))
        assert store.delete(stored.id) is True
        assert store.get(stored.id) is None
        assert store.delete(stored.id) is False  # already gone


def test_leaderboard_aggregates_across_evaluations():
    with EvaluationStore(":memory:") as store:
        # alpha wins both; bravo always second; charlie appears once.
        store.add(_eval("t1", [_run("alpha", 5), _run("bravo", 3)]))
        store.add(_eval("t2", [_run("alpha", 4), _run("bravo", 2), _run("charlie", 1)]))

        board = store.leaderboard()
        by_agent = {r.agent: r for r in board}

        assert board[0].agent == "alpha"  # best average first
        assert by_agent["alpha"].evaluations == 2
        assert by_agent["alpha"].wins == 2
        assert by_agent["alpha"].win_rate == 1.0
        assert by_agent["alpha"].average == 4.5
        assert by_agent["alpha"].best == 5.0
        assert by_agent["alpha"].worst == 4.0

        assert by_agent["bravo"].wins == 0
        assert by_agent["bravo"].win_rate == 0.0
        assert by_agent["charlie"].evaluations == 1


def test_leaderboard_min_evaluations_filter():
    with EvaluationStore(":memory:") as store:
        store.add(_eval("t1", [_run("alpha", 5), _run("bravo", 3)]))
        store.add(_eval("t2", [_run("alpha", 4)]))
        agents = {r.agent for r in store.leaderboard(min_evaluations=2)}
        assert agents == {"alpha"}  # bravo only has one evaluation
