"""Render a scored evaluation as Markdown or JSON."""

from __future__ import annotations

import json

from agentrubric.rubric import Rubric
from agentrubric.scoring import ScoredEvaluation


def to_markdown(scored: ScoredEvaluation, rubric: Rubric) -> str:
    lines: list[str] = []
    if scored.task:
        lines.append(f"# Evaluation: {scored.task}")
        lines.append("")

    ordinal = {1: "1st", 2: "2nd", 3: "3rd"}
    winner = scored.winner
    verdict = "tied for 1st" if winner.tied else "ranked 1st"
    lines.append(f"**Winner:** `{winner.agent}` ({verdict}, overall {winner.overall:.1f}/5)")
    lines.append("")

    # Score matrix: one column per run.
    header = "| Dimension | Weight | " + " | ".join(f"`{r.agent}`" for r in scored.runs) + " |"
    sep = "| --- | ---: | " + " | ".join(["---:"] * len(scored.runs)) + " |"
    lines.append(header)
    lines.append(sep)
    for dim in rubric.dimensions:
        cells = " | ".join(str(r.scores[dim.key]) for r in scored.runs)
        lines.append(f"| {dim.name} | {dim.weight:g} | {cells} |")
    overall_cells = " | ".join(f"**{r.overall:.1f}**" for r in scored.runs)
    lines.append(f"| **Overall (1-5)** | | {overall_cells} |")
    rank_cells = " | ".join(f"{ordinal.get(r.rank, str(r.rank))}{'=' if r.tied else ''}" for r in scored.runs)
    lines.append(f"| **Rank** | | {rank_cells} |")
    lines.append("")

    lines.append("## Rationale")
    lines.append("")
    for run in scored.runs:
        rank_label = ordinal.get(run.rank, f"{run.rank}th")
        lines.append(f"### {rank_label}{' (tie)' if run.tied else ''} — `{run.agent}` ({run.overall:.1f}/5)")
        lines.append("")
        lines.append(run.rationale.strip() or "_No rationale provided._")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def to_json(scored: ScoredEvaluation) -> str:
    payload = {
        "task": scored.task,
        "winner": scored.winner.agent,
        "runs": [
            {
                "agent": r.agent,
                "overall": r.overall,
                "rank": r.rank,
                "tied": r.tied,
                "scores": r.scores,
                "rationale": r.rationale,
            }
            for r in scored.runs
        ],
    }
    return json.dumps(payload, indent=2)
