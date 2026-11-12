# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
