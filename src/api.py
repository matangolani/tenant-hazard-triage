"""
Tenant Hazard Triage — HTTP API and demo page.

    uvicorn api:app --app-dir src --port 8000          # then open http://localhost:8000

Endpoints
  GET  /           demo page (web/index.html)
  GET  /health     backend, model and spec version
  GET  /examples   example tenant messages for the demo
  POST /triage     {"text": "...", "received_at": "2026-10-06T09:00:00+01:00" (optional)}
"""
import json, os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

import spec
import triage_service as svc

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")
app = FastAPI(title="Tenant Hazard Triage", version=spec.SPEC_VERSION,
              description="Decision support for triaging social-housing hazard reports under Awaab's Law. "
                          "Every emergency or uncertain case is flagged for a human; the tool never decides.")


class TriageRequest(BaseModel):
    text: str = Field(min_length=3, max_length=4000, description="The tenant's message, as received")
    received_at: Optional[datetime] = Field(None, description="When the report arrived (defaults to now)")

    @field_validator("text")
    @classmethod
    def not_blank(cls, v):
        if not v.strip():
            raise ValueError("text is empty")
        return v.strip()


class TriageResponse(BaseModel):
    category: str
    severity: str
    location: str
    vulnerable_occupants: list[str]
    duration: str
    confidence: str
    needs_human_review: bool
    deadline: dict
    received_at: str
    meta: dict


@app.get("/health")
def health():
    return {"status": "ok", "backend": svc.BACKEND, "model": svc.model_label(),
            "spec_version": spec.SPEC_VERSION}


@app.get("/examples")
def examples():
    return json.load(open(os.path.join(WEB, "examples.json")))


@app.post("/triage", response_model=TriageResponse)
def triage(req: TriageRequest):
    received = req.received_at or datetime.now(timezone.utc)
    if received.tzinfo is None:
        received = received.replace(tzinfo=timezone.utc)
    try:
        return svc.triage(req.text, received)
    except svc.BackendUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(os.path.join(WEB, "index.html"))
