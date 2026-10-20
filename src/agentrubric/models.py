"""Input model: an evaluation of several agent runs for one task."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentrubric.rubric import DEFAULT_RUBRIC, SCALE_MAX, SCALE_MIN, Rubric


class EvaluationError(ValueError):
    """Raised when an evaluation payload is malformed or inconsistent with the rubric."""


@dataclass
class RunRating:
    """One agent's run and the rating given to it on each rubric dimension."""

    agent: str
    scores: dict[str, int]
    rationale: str = ""

    def validate(self, rubric: Rubric) -> None:
        missing = [k for k in rubric.keys if k not in self.scores]
        if missing:
            raise EvaluationError(f"run {self.agent!r} is missing scores for: {', '.join(missing)}")
        unknown = [k for k in self.scores if k not in rubric.keys]
        if unknown:
            raise EvaluationError(f"run {self.agent!r} has scores for unknown dimensions: {', '.join(unknown)}")
        for key, value in self.scores.items():
            if not isinstance(value, int) or isinstance(value, bool):
                raise EvaluationError(f"run {self.agent!r} score for {key!r} must be an integer")
            if not SCALE_MIN <= value <= SCALE_MAX:
                raise EvaluationError(f"run {self.agent!r} score for {key!r} is out of range {SCALE_MIN}-{SCALE_MAX}")


@dataclass
class Evaluation:
    """A task and the rated runs to be compared."""

    task: str
    runs: list[RunRating]
    rubric: Rubric = field(default=DEFAULT_RUBRIC)

    def validate(self) -> None:
        if not self.runs:
            raise EvaluationError("an evaluation needs at least one run")
        agents = [r.agent for r in self.runs]
        if len(agents) != len(set(agents)):
            raise EvaluationError("run agent names must be unique")
        for run in self.runs:
            run.validate(self.rubric)


def from_dict(data: dict[str, Any], rubric: Rubric = DEFAULT_RUBRIC) -> Evaluation:
    if "runs" not in data or not isinstance(data["runs"], list):
        raise EvaluationError("payload must have a 'runs' list")

    runs = []
    for i, raw in enumerate(data["runs"]):
        if not isinstance(raw, dict):
            raise EvaluationError(f"run #{i} must be an object")
        agent = raw.get("agent") or raw.get("name")
        if not agent:
            raise EvaluationError(f"run #{i} is missing an 'agent' name")
        scores = raw.get("scores")
        if not isinstance(scores, dict):
            raise EvaluationError(f"run {agent!r} is missing a 'scores' object")
        runs.append(RunRating(agent=str(agent), scores=dict(scores), rationale=str(raw.get("rationale", ""))))

    evaluation = Evaluation(task=str(data.get("task", "")), runs=runs, rubric=rubric)
    evaluation.validate()
    return evaluation


def load_evaluation(path: str | Path, rubric: Rubric = DEFAULT_RUBRIC) -> Evaluation:
    """Load and validate an evaluation from a JSON file."""
    text = Path(path).read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise EvaluationError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise EvaluationError("payload must be a JSON object")
    return from_dict(data, rubric)
