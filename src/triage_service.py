"""
Tenant Hazard Triage — the triage service behind the API and demo.

One function, triage(text), returns the structured triage plus indicative deadlines.
Backends:
  ollama — a local model served by Ollama (default). Same system prompt, JSON schema
           (constrained decoding) and normalisation as the evaluation runner, so the demo
           behaves exactly like the scored model.
  rules  — the keyword baseline. Needs no model; used by tests and CI.
Configure with environment variables:
  TRIAGE_BACKEND = ollama | rules        (default ollama)
  TRIAGE_MODEL   = Ollama model tag      (default tenant-hazard-triage, the fine-tuned model)
  TRIAGE_SECOND_MODEL = second-opinion model (default qwen3.5:4b; set to "" to turn the ensemble off)
  OLLAMA_HOST   = http://localhost:11434

With a second model set, both models triage every message (in parallel) and src/ensemble.py's rule
applies: if the second model says emergency, the result is escalated and flagged for review. If the
second model can't be reached, the result is flagged for review rather than silently trusted.
"""
import os, time, urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import spec
from zeroshot_runner import SYSTEM_PROMPT, PROMPT_HASH, SCHEMA, post, parse, normalise, FAILSAFE
from deadlines import deadlines
import baseline_rules
from ensemble import combine

BACKEND = os.environ.get("TRIAGE_BACKEND", "ollama")
MODEL = os.environ.get("TRIAGE_MODEL", "tenant-hazard-triage")
SECOND = os.environ.get("TRIAGE_SECOND_MODEL", "qwen3.5:4b") if BACKEND == "ollama" else ""
TIMEOUT = int(os.environ.get("TRIAGE_TIMEOUT", "120"))


class BackendUnavailable(RuntimeError):
    pass


def _ollama(text, model=None):
    model = model or MODEL
    payload = {"model": model, "stream": False, "keep_alive": "30m", "format": SCHEMA,
               "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": 'Tenant message:\n"""\n' + text + '\n"""'}],
               "options": {"temperature": 0, "seed": 42, "num_ctx": 6144},
               "think": False}          # same as the evaluation runner; thinking made the demo take minutes
    try:
        resp = post("/api/chat", payload, TIMEOUT)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:200]
        if e.code == 400 and "think" in body.lower():      # model has no thinking switch
            payload.pop("think"); resp = post("/api/chat", payload, TIMEOUT)
            obj = parse(resp.get("message", {}).get("content", ""))
            return dict(FAILSAFE, parse_error=True) if obj is None else dict(normalise(obj), parse_error=False)
        if e.code == 404:
            raise BackendUnavailable(f"Model '{model}' isn't in Ollama. See scripts/deploy_ollama.sh, or set TRIAGE_MODEL / TRIAGE_SECOND_MODEL.")
        raise BackendUnavailable(f"Ollama returned HTTP {e.code}: {body}")
    except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
        raise BackendUnavailable(f"Can't reach Ollama at {os.environ.get('OLLAMA_HOST', 'http://localhost:11434')}: {e}")
    obj = parse(resp.get("message", {}).get("content", ""))
    if obj is None:
        return dict(FAILSAFE, parse_error=True)
    out = normalise(obj); out["parse_error"] = False
    return out


def _rules(text):
    out = baseline_rules.predict(text); out["parse_error"] = False
    out["needs_human_review_model"] = out["needs_human_review"]
    return out


def _ensemble(text):
    with ThreadPoolExecutor(2) as pool:
        first, second = pool.submit(_ollama, text, MODEL), pool.submit(_ollama, text, SECOND)
        r = first.result()                      # the primary model must work
        try:
            s = second.result()
        except BackendUnavailable as e:
            r = dict(r, needs_human_review=True, escalated_by_second_opinion=False,
                     second_opinion={"severity": None, "model": SECOND, "error": str(e)})
            return r
    s["model"] = SECOND
    return combine(r, s)


def model_label():
    if BACKEND != "ollama":
        return "keyword rules"
    return f"{MODEL}, second opinion from {SECOND}" if SECOND else MODEL


def triage(text, received_at=None):
    received_at = received_at or datetime.now(timezone.utc)
    t0 = time.perf_counter()
    if BACKEND == "rules":
        r = _rules(text)
    else:
        r = _ensemble(text) if SECOND else _ollama(text)
    return {
        "category": r["category"], "severity": r["severity"],
        "location": r.get("location", "unspecified"), "vulnerable_occupants": r.get("vulnerable_occupants", []),
        "duration": r.get("duration", "unspecified"), "confidence": r["confidence"],
        "needs_human_review": r["needs_human_review"],
        "deadline": deadlines(r["severity"], received_at),
        "received_at": received_at.isoformat(timespec="minutes"),
        "meta": {"backend": BACKEND, "model": model_label(),
                 "escalated_by_second_opinion": r.get("escalated_by_second_opinion", False),
                 "second_opinion": r.get("second_opinion"),
                 "spec_version": spec.SPEC_VERSION, "prompt_hash": PROMPT_HASH,
                 "latency_ms": round((time.perf_counter() - t0) * 1000), "parse_error": r.get("parse_error", False)},
    }
