"""agentrubric: score, rank and report on AI coding-agent runs against a quality rubric.

Given several agents' runs of the same task and a rating on each quality dimension, agentrubric
computes a weighted overall score (1-5), ranks the runs, and produces a Markdown or JSON report —
the structured deliverable an agent-evaluation review calls for.
"""

from agentrubric.models import Evaluation, RunRating, load_evaluation
from agentrubric.rubric import DEFAULT_RUBRIC, Dimension, Rubric, rubric_from_dict, rubric_to_dict
from agentrubric.scoring import RankedRun, ScoredEvaluation, score_evaluation
from agentrubric.store import (
    EvaluationStore,
    EvaluationSummary,
    LeaderboardRow,
    StoredEvaluation,
)

__version__ = "0.2.0"
__all__ = [
    "Dimension",
    "Rubric",
    "DEFAULT_RUBRIC",
    "rubric_to_dict",
    "rubric_from_dict",
    "RunRating",
    "Evaluation",
    "load_evaluation",
    "RankedRun",
    "ScoredEvaluation",
    "score_evaluation",
    "EvaluationStore",
    "StoredEvaluation",
    "EvaluationSummary",
    "LeaderboardRow",
]
