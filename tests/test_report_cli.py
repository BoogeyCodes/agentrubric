from __future__ import annotations

import json
from pathlib import Path

from agentrubric.cli import main
from agentrubric.models import load_evaluation
from agentrubric.report import to_json, to_markdown
from agentrubric.scoring import score_evaluation

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "auth-fix.json"


def test_markdown_report_has_matrix_ranking_and_rationale():
    evaluation = load_evaluation(EXAMPLE)
    scored = score_evaluation(evaluation)
    md = to_markdown(scored, evaluation.rubric)

    assert "# Evaluation: Fix the failing login test" in md
    assert "**Winner:** `agent-alpha`" in md
    assert "| Correctness |" in md
    assert "**Overall (1-5)**" in md
    assert "## Rationale" in md
    assert "agent-alpha" in md and "agent-bravo" in md and "agent-charlie" in md


def test_json_report_round_trips():
    evaluation = load_evaluation(EXAMPLE)
    scored = score_evaluation(evaluation)
    data = json.loads(to_json(scored))
    assert data["winner"] == "agent-alpha"
    assert len(data["runs"]) == 3
    assert data["runs"][0]["rank"] == 1


def test_cli_score_markdown(capsys):
    assert main(["score", str(EXAMPLE)]) == 0
    assert "Winner" in capsys.readouterr().out


def test_cli_score_json(capsys):
    assert main(["score", str(EXAMPLE), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["winner"] == "agent-alpha"


def test_cli_rubric(capsys):
    assert main(["rubric"]) == 0
    assert "correctness" in capsys.readouterr().out


def test_cli_bad_file_is_error(capsys):
    assert main(["score", "nope.json"]) == 2
    assert "agentrubric:" in capsys.readouterr().err
