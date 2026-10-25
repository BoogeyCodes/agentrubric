from __future__ import annotations

import pytest

from agentrubric.models import Evaluation, EvaluationError, RunRating
from agentrubric.rubric import DEFAULT_RUBRIC, Dimension, Rubric
from agentrubric.scoring import score_evaluation, weighted_overall

ALL_FIVES = {k: 5 for k in DEFAULT_RUBRIC.keys}
ALL_ONES = {k: 1 for k in DEFAULT_RUBRIC.keys}


def run(agent: str, value: int, **overrides) -> RunRating:
    scores = {k: value for k in DEFAULT_RUBRIC.keys}
    scores.update(overrides)
    return RunRating(agent=agent, scores=scores)


def test_weighted_overall_of_uniform_scores_equals_the_score():
    assert weighted_overall(RunRating("a", ALL_FIVES), DEFAULT_RUBRIC) == 5.0
    assert weighted_overall(RunRating("a", ALL_ONES), DEFAULT_RUBRIC) == 1.0


def test_weights_actually_matter():
    rubric = Rubric((Dimension("a", "A", "", weight=3), Dimension("b", "B", "", weight=1)))
    # a=4, b=0-ish: weighted toward a. (4*3 + 2*1)/4 = 3.5
    assert weighted_overall(RunRating("x", {"a": 4, "b": 2}), rubric) == 3.5


def test_ranks_runs_best_first():
    evaluation = Evaluation("t", [run("low", 2), run("high", 5), run("mid", 3)])
    scored = score_evaluation(evaluation)
    assert [r.agent for r in scored.runs] == ["high", "mid", "low"]
    assert [r.rank for r in scored.runs] == [1, 2, 3]
    assert scored.winner.agent == "high"
    assert not scored.winner.tied


def test_ties_share_a_rank_and_are_flagged():
    evaluation = Evaluation("t", [run("a", 4), run("b", 4), run("c", 2)])
    scored = score_evaluation(evaluation)
    assert scored.runs[0].rank == 1 and scored.runs[1].rank == 1
    assert scored.runs[0].tied and scored.runs[1].tied
    assert scored.runs[2].rank == 3 and not scored.runs[2].tied


def test_validation_catches_bad_input():
    with pytest.raises(EvaluationError):
        score_evaluation(Evaluation("t", []))  # no runs
    with pytest.raises(EvaluationError):
        score_evaluation(Evaluation("t", [run("a", 5), run("a", 4)]))  # duplicate agents

    missing = RunRating("a", {k: 5 for k in DEFAULT_RUBRIC.keys if k != "safety"})
    with pytest.raises(EvaluationError):
        score_evaluation(Evaluation("t", [missing]))

    out_of_range = run("a", 5, correctness=9)
    with pytest.raises(EvaluationError):
        score_evaluation(Evaluation("t", [out_of_range]))
