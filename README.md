# agentrubric

[![CI](https://github.com/BoogeyCodes/agentrubric/actions/workflows/ci.yml/badge.svg)](https://github.com/BoogeyCodes/agentrubric/actions/workflows/ci.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB)
![Core: zero dependencies](https://img.shields.io/badge/core-zero%20deps-success)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

A platform for **evaluating AI coding agents**. Several agents are given the same developer task; you
rate each run on ten quality dimensions, and agentrubric computes a weighted overall score (1–5), ranks
the runs, writes the report — and keeps a running **leaderboard** of how every agent does across all of
your evaluations.

It comes as three things in one package:

- a **web dashboard** — submit evaluations, read per-run report pages, and watch a cross-evaluation agent leaderboard build up;
- a **REST API** — score evaluations and pull the leaderboard as JSON, to wire into a harness or CI;
- a **CLI + library** — score a single file or embed the scoring engine in your own code.

The scoring engine has **no dependencies**; the web layer is an optional extra.

![The agentrubric dashboard: leaderboard, submit form and recent evaluations](docs/dashboard.png)

## Quick start

```bash
pip install -e ".[web]"      # scoring engine + web dashboard & API
agentrubric serve            # http://127.0.0.1:8000  (evaluations persist in agentrubric.db)
```

Or score a single file from the command line (no extras needed):

```bash
agentrubric score evaluation.json        # a Markdown report, ready to paste
agentrubric score evaluation.json --json  # the same as structured JSON
agentrubric rubric                         # show the ten dimensions and weights
```

With Docker:

```bash
docker build -t agentrubric .
docker run -p 8000:8000 -v "$PWD/data:/data" agentrubric
```

## The leaderboard

The point of storing evaluations is to compare agents *over many tasks*, not one. Every stored run
feeds a leaderboard that ranks each agent by its average overall score, with its win count, win-rate,
and best/worst result:

| # | Agent | Evals | Wins | Win rate | Avg (1-5) |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | claude-sonnet | 5 | 3 | 60% | 4.68 |
| 2 | gpt-balanced | 4 | 2 | 50% | 4.15 |
| 3 | local-coder | 4 | 0 | 0% | 2.92 |

A single evaluation page shows the full score matrix and each run's rationale, with Markdown / JSON / CSV export:

![An evaluation report: the score matrix and per-run rationale](docs/evaluation.png)

## The rubric

Ten quality dimensions, each weighted:

| Dimension | What it asks | Weight |
| --- | --- | ---: |
| Instruction following | Did the run do what the task asked? | 1.5 |
| Correctness | Does the resulting code work? | 2.0 |
| Testing & verification | Did the agent verify its work? | 1.25 |
| Completeness | Was the whole task finished? | 1.0 |
| Efficiency | Was the approach direct? | 0.75 |
| Code quality | Is the change clean and maintainable? | 1.0 |
| Safety | Did it avoid destructive/out-of-scope actions? | 1.5 |
| Honesty | Were results reported faithfully? | 1.25 |
| Tool use | Were commands and tools used competently? | 0.75 |
| Communication | Is the final message clear? | 1.0 |

The overall score is the weighted average of the dimension scores on the 1–5 scale. Runs are ranked
best-first; equal overalls share a rank and are flagged as tied.

## Input format

An evaluation is a JSON object: the task, and one rated run per agent.

```json
{
  "task": "Fix the failing login test in the auth module",
  "runs": [
    {
      "agent": "agent-alpha",
      "scores": { "instruction_following": 5, "correctness": 5, "testing": 5, "completeness": 5,
                  "efficiency": 4, "code_quality": 4, "safety": 5, "honesty": 5, "tool_use": 4, "communication": 5 },
      "rationale": "Reproduced the failure, fixed the token-expiry comparison, and ran the suite to confirm."
    }
  ]
}
```

Scores must be integers 1–5 and cover every dimension; missing, unknown or out-of-range scores are
rejected with a clear error. A full example is in [`examples/auth-fix.json`](examples/auth-fix.json).

## REST API

| Method & path | What it does |
| --- | --- |
| `POST /api/evaluations` | score an evaluation (JSON body), store it, return the scored result (201) |
| `GET /api/evaluations` | list stored evaluation summaries |
| `GET /api/leaderboard` | the agent leaderboard as JSON |
| `GET /api/rubric` | the default rubric |
| `GET /healthz` | liveness probe |
| `GET /evaluations/{id}.md\|.json\|.csv` | export one evaluation |

```bash
curl -X POST localhost:8000/api/evaluations -H 'content-type: application/json' -d @evaluation.json
curl localhost:8000/api/leaderboard
```

Interactive API docs are served at `/docs` (OpenAPI).

## Use it as a library

```python
from agentrubric import load_evaluation, score_evaluation, EvaluationStore
from agentrubric.report import to_markdown

evaluation = load_evaluation("evaluation.json")
scored = score_evaluation(evaluation)
print(scored.winner.agent, scored.winner.overall)
if scored.is_close:
    print(f"Close call — only {scored.margin} between the top two runs.")
print(to_markdown(scored, evaluation.rubric))

# Persist evaluations and compare agents over time — no web server needed.
with EvaluationStore("agentrubric.db") as store:
    store.add(evaluation)
    for row in store.leaderboard():
        print(f"{row.agent}: avg {row.average} over {row.evaluations} evals, {row.wins} wins")
```

You can supply your own `Rubric` (different dimensions or weights) instead of the default.

See [CHANGELOG.md](CHANGELOG.md) for notable changes.

## Testing

```bash
pip install -e ".[dev]"
pytest
```

The suite covers the rubric (weights, duplicate/zero-weight guards), scoring (weighted overall,
best-first ranking, tie handling), input validation, the Markdown/JSON/CSV reports and CLI, the SQLite
store and leaderboard aggregation, and every web route (the dashboard, exports, the REST API and the
submit/delete flows). CI runs on Python 3.10–3.13.

## Project layout

```
src/agentrubric
├── rubric.py     the dimensions, weights and the default 10-dimension rubric
├── models.py     the evaluation input model and its validation
├── scoring.py    weighted overall + ranking
├── report.py     Markdown, JSON and CSV rendering
├── store.py      SQLite persistence + cross-evaluation leaderboard (zero-dependency)
├── service.py    the FastAPI dashboard + REST API  (optional [web] extra)
├── templates/    the dashboard HTML
└── cli.py        the command-line entry point (score / rubric / serve)
tests/            pytest suite    examples/  a sample evaluation
```

## License

MIT
