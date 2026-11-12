"""A FastAPI web service and REST API around the agentrubric scoring engine.

This is the optional web layer (``pip install agentrubric[web]``). The scoring core stays
dependency-free; only this module needs FastAPI, Uvicorn and Jinja2.

    from agentrubric.service import create_app
    app = create_app("agentrubric.db")      # pass to uvicorn, or use `agentrubric serve`

Routes:
    GET  /                       dashboard: leaderboard + recent evaluations + submit form
    POST /submit                 (form) submit an evaluation JSON, redirect to its page
    GET  /evaluations/{id}       HTML report for one evaluation
    GET  /evaluations/{id}.md    Markdown export
    GET  /evaluations/{id}.json  JSON export
    GET  /evaluations/{id}.csv   CSV score matrix
    POST /evaluations/{id}/delete delete it (HTMX), redirect home
    GET  /leaderboard            HTML leaderboard across all evaluations
    POST /api/evaluations        REST: submit an evaluation, get the scored JSON back (201)
    GET  /api/evaluations        REST: list stored evaluation summaries
    GET  /api/leaderboard        REST: the leaderboard as JSON
    GET  /api/rubric             REST: the default rubric
    GET  /healthz                liveness probe
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from agentrubric import __version__
from agentrubric.models import EvaluationError, from_dict
from agentrubric.report import to_csv, to_json, to_markdown
from agentrubric.rubric import DEFAULT_RUBRIC
from agentrubric.store import EvaluationStore

_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _parse_evaluation_text(text: str) -> Any:
    import json

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise EvaluationError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise EvaluationError("payload must be a JSON object")
    return from_dict(data)


def create_app(db_path: str | Path = "agentrubric.db") -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.store = EvaluationStore(db_path)
        try:
            yield
        finally:
            app.state.store.close()

    app = FastAPI(
        title="agentrubric",
        version=__version__,
        description="Score, rank and report on AI coding-agent runs, and track agents on a leaderboard.",
        lifespan=lifespan,
    )

    def store() -> EvaluationStore:
        return app.state.store

    def _dashboard_context(request: Request, **extra: Any) -> dict:
        return {
            "request": request,
            "leaderboard": store().leaderboard(),
            "evaluations": store().list(limit=25),
            "total": store().count(),
            "version": __version__,
            **extra,
        }

    # -- HTML pages ------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return _TEMPLATES.TemplateResponse(request=request, name="index.html", context=_dashboard_context(request))

    @app.post("/submit")
    def submit(request: Request, payload: str = Form(...)) -> Response:
        try:
            evaluation = _parse_evaluation_text(payload)
        except EvaluationError as exc:
            return _TEMPLATES.TemplateResponse(
                request=request,
                name="index.html",
                context=_dashboard_context(request, error=str(exc), payload=payload),
                status_code=400,
            )
        stored = store().add(evaluation)
        return RedirectResponse(f"/evaluations/{stored.id}", status_code=303)

    @app.get("/leaderboard", response_class=HTMLResponse)
    def leaderboard_page(request: Request) -> HTMLResponse:
        return _TEMPLATES.TemplateResponse(
            request=request,
            name="leaderboard.html",
            context={
                "request": request,
                "leaderboard": store().leaderboard(),
                "total": store().count(),
                "version": __version__,
            },
        )

    # Suffix/action routes are declared before the bare `{eval_id}` route so they are not
    # shadowed by it (otherwise "/evaluations/1.json" matches {eval_id}="1.json" and 422s).
    @app.get("/evaluations/{eval_id}.md", response_class=PlainTextResponse)
    def evaluation_md(eval_id: int) -> PlainTextResponse:
        stored = _require(store(), eval_id)
        return PlainTextResponse(to_markdown(stored.scored, stored.rubric), media_type="text/markdown")

    @app.get("/evaluations/{eval_id}.json")
    def evaluation_json(eval_id: int) -> Response:
        stored = _require(store(), eval_id)
        return Response(to_json(stored.scored), media_type="application/json")

    @app.get("/evaluations/{eval_id}.csv")
    def evaluation_csv(eval_id: int) -> PlainTextResponse:
        stored = _require(store(), eval_id)
        return PlainTextResponse(to_csv(stored.scored, stored.rubric), media_type="text/csv")

    @app.post("/evaluations/{eval_id}/delete")
    def delete_evaluation(eval_id: int) -> Response:
        store().delete(eval_id)
        return RedirectResponse("/", status_code=303)

    @app.get("/evaluations/{eval_id}", response_class=HTMLResponse)
    def evaluation_page(request: Request, eval_id: int) -> HTMLResponse:
        stored = store().get(eval_id)
        if stored is None:
            raise HTTPException(status_code=404, detail="evaluation not found")
        return _TEMPLATES.TemplateResponse(
            request=request,
            name="evaluation.html",
            context={
                "request": request,
                "stored": stored,
                "scored": stored.scored,
                "rubric": stored.rubric,
                "version": __version__,
            },
        )

    # -- JSON API --------------------------------------------------------
    @app.post("/api/evaluations")
    def api_create(payload: dict) -> JSONResponse:
        try:
            evaluation = from_dict(payload)
        except EvaluationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        stored = store().add(evaluation)
        body = {
            "id": stored.id,
            "created_at": stored.created_at,
            "task": stored.task,
            "winner": stored.scored.winner.agent,
            "margin": stored.scored.margin,
            "is_close": stored.scored.is_close,
            "runs": [
                {"agent": r.agent, "overall": r.overall, "rank": r.rank, "tied": r.tied}
                for r in stored.scored.runs
            ],
        }
        return JSONResponse(body, status_code=201)

    @app.get("/api/evaluations")
    def api_list(limit: int = 100, offset: int = 0) -> list[dict]:
        return [
            {
                "id": s.id,
                "task": s.task,
                "created_at": s.created_at,
                "winner": s.winner,
                "margin": s.margin,
                "run_count": s.run_count,
            }
            for s in store().list(limit=limit, offset=offset)
        ]

    @app.get("/api/leaderboard")
    def api_leaderboard(min_evaluations: int = 1) -> list[dict]:
        return [
            {
                "agent": r.agent,
                "evaluations": r.evaluations,
                "wins": r.wins,
                "win_rate": r.win_rate,
                "average": r.average,
                "best": r.best,
                "worst": r.worst,
            }
            for r in store().leaderboard(min_evaluations=min_evaluations)
        ]

    @app.get("/api/rubric")
    def api_rubric() -> dict:
        return {
            "scale": {"min": 1, "max": 5},
            "dimensions": [
                {"key": d.key, "name": d.name, "description": d.description, "weight": d.weight}
                for d in DEFAULT_RUBRIC.dimensions
            ],
        }

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok", "version": __version__, "evaluations": store().count()}

    return app


def _require(store: EvaluationStore, eval_id: int):
    stored = store.get(eval_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="evaluation not found")
    return stored
