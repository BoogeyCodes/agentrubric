from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from agentrubric.service import create_app

DIMS = [
    "instruction_following", "correctness", "testing", "completeness", "efficiency",
    "code_quality", "safety", "honesty", "tool_use", "communication",
]


def _payload(task: str, runs: list[tuple[str, int]]) -> dict:
    return {
        "task": task,
        "runs": [{"agent": a, "scores": {d: v for d in DIMS}, "rationale": f"{a} notes"} for a, v in runs],
    }


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app(":memory:")) as c:
        yield c


def test_healthz(client: TestClient):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_api_create_scores_and_ranks(client: TestClient):
    r = client.post("/api/evaluations", json=_payload("fix login", [("alpha", 5), ("bravo", 3)]))
    assert r.status_code == 201
    body = r.json()
    assert body["winner"] == "alpha"
    assert body["id"] == 1
    assert body["runs"][0]["rank"] == 1


def test_api_create_rejects_bad_payload(client: TestClient):
    r = client.post("/api/evaluations", json={"task": "x", "runs": [{"agent": "a", "scores": {}}]})
    assert r.status_code == 422


def test_evaluation_html_and_exports(client: TestClient):
    eid = client.post("/api/evaluations", json=_payload("task", [("alpha", 5), ("bravo", 2)])).json()["id"]

    html = client.get(f"/evaluations/{eid}")
    assert html.status_code == 200
    assert "alpha" in html.text
    assert "Score matrix" in html.text

    assert client.get(f"/evaluations/{eid}.md").status_code == 200
    assert "# Evaluation" in client.get(f"/evaluations/{eid}.md").text

    j = client.get(f"/evaluations/{eid}.json")
    assert j.status_code == 200
    assert json.loads(j.text)["winner"] == "alpha"

    csv = client.get(f"/evaluations/{eid}.csv")
    assert csv.status_code == 200
    assert "dimension" in csv.text


def test_missing_evaluation_is_404(client: TestClient):
    assert client.get("/evaluations/999").status_code == 404
    assert client.get("/evaluations/999.json").status_code == 404


def test_submit_form_redirects_to_detail(client: TestClient):
    text = json.dumps(_payload("via form", [("alpha", 4)]))
    r = client.post("/submit", data={"payload": text}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/evaluations/")


def test_submit_form_bad_json_shows_error(client: TestClient):
    r = client.post("/submit", data={"payload": "{not json"}, follow_redirects=False)
    assert r.status_code == 400
    assert "invalid JSON" in r.text


def test_leaderboard_endpoints(client: TestClient):
    client.post("/api/evaluations", json=_payload("t1", [("alpha", 5), ("bravo", 3)]))
    client.post("/api/evaluations", json=_payload("t2", [("alpha", 4), ("bravo", 2)]))

    api = client.get("/api/leaderboard")
    assert api.status_code == 200
    rows = api.json()
    assert rows[0]["agent"] == "alpha"
    assert rows[0]["wins"] == 2
    assert rows[0]["win_rate"] == 1.0

    page = client.get("/leaderboard")
    assert page.status_code == 200
    assert "alpha" in page.text


def test_delete_via_form(client: TestClient):
    eid = client.post("/api/evaluations", json=_payload("t", [("alpha", 5)])).json()["id"]
    r = client.post(f"/evaluations/{eid}/delete", follow_redirects=False)
    assert r.status_code == 303
    assert client.get(f"/evaluations/{eid}").status_code == 404


def test_index_page_renders(client: TestClient):
    assert client.get("/").status_code == 200
    client.post("/api/evaluations", json=_payload("shown", [("alpha", 5)]))
    assert "shown" in client.get("/").text
