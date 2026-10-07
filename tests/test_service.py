"""API, deadline and service tests. Run: python3 -m pytest -q
Uses the keyword-rules backend, so no model or Ollama is needed (this is what CI runs)."""
import os, sys
from datetime import datetime, timezone, date
os.environ["TRIAGE_BACKEND"] = "rules"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from fastapi.testclient import TestClient
import api, deadlines

client = TestClient(api.app)


def test_working_days_skip_weekends_and_bank_holidays():
    # Tue 22 Dec 2026 + 10 working days crosses Christmas, Boxing Day (sub. 28 Dec) and New Year's Day
    assert deadlines.add_working_days(date(2026, 12, 22), 10) == date(2027, 1, 8)
    assert deadlines.add_working_days(date(2026, 10, 9), 1) == date(2026, 10, 12)     # Fri -> Mon


def test_working_day_counting_uses_uk_calendar_day():
    late_evening_utc = datetime(2026, 10, 5, 23, 30, tzinfo=timezone.utc)   # already Tue 6 Oct in London
    assert deadlines.add_working_days(late_evening_utc, 10) == date(2026, 10, 20)


def test_emergency_deadline_is_24_hours():
    d = deadlines.deadlines("emergency", datetime(2026, 10, 6, 9, 0, tzinfo=timezone.utc))
    assert d["make_safe_by"].startswith("2026-10-07T09:00")


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["backend"] == "rules"


def test_triage_returns_schema_and_deadline():
    r = client.post("/triage", json={"text": "I can smell gas in the kitchen", "received_at": "2026-10-06T09:00:00+01:00"})
    assert r.status_code == 200
    b = r.json()
    assert b["severity"] in {"emergency", "significant", "routine", "unclear"}
    assert set(b) >= {"category", "location", "vulnerable_occupants", "confidence", "needs_human_review", "deadline", "meta"}
    if b["severity"] == "emergency":
        assert b["needs_human_review"] is True and "make_safe_by" in b["deadline"]


def test_blank_and_oversized_text_rejected():
    assert client.post("/triage", json={"text": "   "}).status_code == 422
    assert client.post("/triage", json={"text": "x" * 4001}).status_code == 422


def test_examples_and_demo_page_served():
    assert len(client.get("/examples").json()) >= 3
    r = client.get("/")
    assert r.status_code == 200 and "Tenant Hazard Triage" in r.text


def test_backend_down_gives_503(monkeypatch):
    import triage_service as svc
    def boom(text): raise svc.BackendUnavailable("Can't reach Ollama")
    monkeypatch.setattr(svc, "_rules", boom)
    r = client.post("/triage", json={"text": "mould in the bedroom"})
    assert r.status_code == 503 and "Ollama" in r.json()["detail"]


def test_ensemble_rule_escalates_but_never_downgrades():
    from ensemble import combine
    base = {"severity": "significant", "needs_human_review": False, "category": "electrical"}
    up = combine(base, {"severity": "emergency"})
    assert up["severity"] == "emergency" and up["needs_human_review"] and up["escalated_by_second_opinion"]
    assert up["category"] == "electrical"                       # other fields come from the primary model
    keep = combine({"severity": "emergency", "needs_human_review": True}, {"severity": "routine"})
    assert keep["severity"] == "emergency" and not keep["escalated_by_second_opinion"]


def _fake_ollama(answers):
    def f(text, model=None):
        a = answers[model]
        if isinstance(a, Exception):
            raise a
        return dict(a, parse_error=False)
    return f


def test_service_ensemble_and_second_model_down(monkeypatch):
    import triage_service as svc
    monkeypatch.setattr(svc, "BACKEND", "ollama"); monkeypatch.setattr(svc, "MODEL", "ft"); monkeypatch.setattr(svc, "SECOND", "q35")
    primary = {"category": "electrical", "severity": "significant", "location": "kitchen", "vulnerable_occupants": [],
               "duration": "unspecified", "confidence": "high", "needs_human_review": False}
    monkeypatch.setattr(svc, "_ollama", _fake_ollama({"ft": primary, "q35": dict(primary, severity="emergency")}))
    r = svc.triage("socket sparking")
    assert r["severity"] == "emergency" and r["needs_human_review"] and r["meta"]["escalated_by_second_opinion"]
    assert "make_safe_by" in r["deadline"]
    monkeypatch.setattr(svc, "_ollama", _fake_ollama({"ft": primary, "q35": svc.BackendUnavailable("q35 missing")}))
    r = svc.triage("socket sparking")
    assert r["severity"] == "significant" and r["needs_human_review"] is True       # fails safe, not silent
