# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.2.0]

Grows agentrubric from a scoring library into a full evaluation **platform**: a persistent store,
a web dashboard, a REST API, and a cross-evaluation agent leaderboard. The scoring core stays
dependency-free; the web layer is an optional extra (`pip install agentrubric[web]`).

### Added
- `EvaluationStore` — a dependency-free SQLite store for scored evaluations, with `add`, `get`,
  `list`, `delete`, `count` and a `leaderboard` that aggregates every agent across all evaluations
  (evaluations, wins, win-rate, average, best/worst). Usable on its own or behind the web service.
- `agentrubric.service.create_app` — a FastAPI app: a dashboard (leaderboard + recent evaluations +
  a submit form), per-evaluation report pages, Markdown/JSON/CSV export routes, and a JSON REST API
  (`POST/GET /api/evaluations`, `GET /api/leaderboard`, `GET /api/rubric`, `GET /healthz`).
- `agentrubric serve` CLI subcommand to run the dashboard + API (needs the `[web]` extra).
- `rubric_to_dict` / `rubric_from_dict` so a rubric is persisted alongside each evaluation and the
  stored report renders even if the default rubric later changes.
- A `Dockerfile` that serves the dashboard, persisting evaluations to a mounted volume.

### Changed
- Version bumped to 0.2.0; `[web]` optional-dependency group added.

## [0.1.x]

### Added
- `report.to_csv` — export the score matrix (a dimension per row, an agent per column,
  then overall and rank) for pulling batches of evaluations into a spreadsheet.
- `ScoredEvaluation.margin` — the gap between the top run's overall and the
  runner-up's, so a reviewer can see at a glance whether a ranking was decisive.
- `ScoredEvaluation.is_close` — flags evaluations where the top two runs are
  within 0.3 of each other and the written rationale deserves a closer read.

## [0.1.0]

### Added
- Ten-dimension weighted rubric with a scoring engine and best-first ranking.
- Standard competition ranking with shared ranks and tie flags.
- Markdown and JSON reports.
- `agentrubric` CLI with `score` and `rubric` subcommands.
