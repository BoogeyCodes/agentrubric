"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys

from agentrubric import __version__
from agentrubric.models import EvaluationError, load_evaluation
from agentrubric.report import to_json, to_markdown
from agentrubric.rubric import DEFAULT_RUBRIC
from agentrubric.scoring import score_evaluation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentrubric", description="Score and rank AI coding-agent runs against a quality rubric."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    score = sub.add_parser("score", help="score an evaluation file and print a report")
    score.add_argument("file", help="an evaluation JSON file (task + rated runs)")
    score.add_argument("--json", action="store_true", help="output JSON instead of Markdown")

    sub.add_parser("rubric", help="print the default rubric")

    serve = sub.add_parser("serve", help="run the web dashboard + REST API (needs the [web] extra)")
    serve.add_argument("--db", default="agentrubric.db", help="SQLite file to store evaluations in")
    serve.add_argument("--host", default="127.0.0.1", help="interface to bind (default: 127.0.0.1)")
    serve.add_argument("--port", type=int, default=8000, help="port to listen on (default: 8000)")

    args = parser.parse_args(argv)

    if args.command == "rubric":
        print(f"Default rubric ({len(DEFAULT_RUBRIC.dimensions)} dimensions):\n")
        for d in DEFAULT_RUBRIC.dimensions:
            print(f"  {d.key:<22} weight {d.weight:>4g}  {d.description}")
        return 0

    if args.command == "serve":
        try:
            import uvicorn

            from agentrubric.service import create_app
        except ImportError:
            print(
                "agentrubric: the web server needs the optional extra. Install it with:\n"
                "    pip install 'agentrubric[web]'",
                file=sys.stderr,
            )
            return 2
        uvicorn.run(create_app(args.db), host=args.host, port=args.port)
        return 0

    if args.command == "score":
        try:
            evaluation = load_evaluation(args.file)
        except (EvaluationError, FileNotFoundError) as exc:
            print(f"agentrubric: {exc}", file=sys.stderr)
            return 2
        scored = score_evaluation(evaluation)
        print(to_json(scored) if args.json else to_markdown(scored, evaluation.rubric))
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
