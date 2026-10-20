"""Turn rated runs into weighted overall scores and a ranking."""

from __future__ import annotations

from dataclasses import dataclass

from agentrubric.models import Evaluation, RunRating
from agentrubric.rubric import Rubric


@dataclass(frozen=True)
class RankedRun:
    agent: str
    overall: float
    rank: int
    tied: bool
    scores: dict[str, int]
    rationale: str


@dataclass(frozen=True)
class ScoredEvaluation:
    task: str
    runs: list[RankedRun]

    @property
    def winner(self) -> RankedRun:
        return self.runs[0]


def weighted_overall(run: RunRating, rubric: Rubric) -> float:
    """The weighted average of a run's dimension scores, on the 1-5 scale, rounded to one decimal."""
    total = sum(run.scores[d.key] * d.weight for d in rubric.dimensions)
    return round(total / rubric.total_weight, 1)


def score_evaluation(evaluation: Evaluation) -> ScoredEvaluation:
    """Score every run and rank them best-first. Equal overalls share a rank and are flagged as tied."""
    evaluation.validate()
    rubric = evaluation.rubric

    overalls = [(run, weighted_overall(run, rubric)) for run in evaluation.runs]
    # Sort best-first; a stable secondary sort by agent keeps the output deterministic for ties.
    overalls.sort(key=lambda pair: (-pair[1], pair[0].agent))

    counts = {}
    for _, overall in overalls:
        counts[overall] = counts.get(overall, 0) + 1

    ranked: list[RankedRun] = []
    for run, overall in overalls:
        # Standard competition ranking: equal scores share the position of the first of their group.
        rank = next(p for p, (_, o) in enumerate(overalls, start=1) if o == overall)
        ranked.append(
            RankedRun(
                agent=run.agent,
                overall=overall,
                rank=rank,
                tied=counts[overall] > 1,
                scores=dict(run.scores),
                rationale=run.rationale,
            )
        )

    return ScoredEvaluation(task=evaluation.task, runs=ranked)
