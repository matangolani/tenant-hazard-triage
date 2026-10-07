#!/usr/bin/env python3
"""
Tenant Hazard Triage — zero-shot runner (Ollama).

Sends every gold message to a local model served by Ollama, with NO examples and
NO fine-tuning, and writes predictions in the exact shape `evaluate.py` scores.

Standard library only — no pip installs needed.

Usage:
    python3 src/zeroshot_runner.py --model qwen3.5:4b --gold data/gold_v2.jsonl
    python3 src/zeroshot_runner.py --model gemma4:e4b --gold data/official.jsonl --limit 5   # smoke test

Output: outputs/preds_<set>_<model>.jsonl  (e.g. outputs/preds_official_gemma4_e4b.jsonl)
The prompt is generated from src/spec.py; each prediction records spec_version and prompt_hash.

Safe to interrupt (Ctrl+C) and re-run: finished items are kept and skipped.
"""
import argparse, json, os, re, sys, time, urllib.request, urllib.error

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
if not OLLAMA_URL.startswith("http"):
    OLLAMA_URL = "http://" + OLLAMA_URL

import hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec  # single source of truth: categories, rules, schema, deadlines, prompt

CATEGORIES, SEVERITIES, VULN, CONFIDENCE = list(spec.CATEGORIES), spec.SEVERITIES, spec.VULN, spec.CONFIDENCE
DEADLINES, SCHEMA = spec.DEADLINES, spec.SCHEMA
SYSTEM_PROMPT = spec.render_prompt()          # generated, no worked examples
PROMPT_HASH = hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()[:12]


def slug(model):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model)


def post(path, payload, timeout):
    req = urllib.request.Request(OLLAMA_URL + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def friendly_fail(msg):
    print("\nERROR: " + msg, file=sys.stderr)
    sys.exit(1)


class Client:
    def __init__(self, model, timeout):
        self.model, self.timeout = model, timeout
        self.send_think = True  # disable "thinking" where supported; dropped if unsupported

    def chat(self, text, temperature=0.0):
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": 'Tenant message:\n"""\n' + text + '\n"""'},
            ],
            "format": SCHEMA,
            "stream": False,
            "keep_alive": "15m",
            "options": {"temperature": temperature, "seed": 42, "num_ctx": 6144},
        }
        if self.send_think:
            payload["think"] = False
        try:
            return post("/api/chat", payload, self.timeout)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            if e.code == 404 or "not found" in body.lower():
                friendly_fail(f"Model '{self.model}' isn't downloaded. Run:  ollama pull {self.model}")
            if self.send_think and "think" in body.lower():
                self.send_think = False  # model has no thinking switch; retry without it
                return self.chat(text, temperature)
            raise RuntimeError(f"Ollama HTTP {e.code}: {body[:200]}")
        except urllib.error.URLError:
            friendly_fail("Can't reach Ollama at " + OLLAMA_URL + ".\n"
                          "Open the Ollama app (llama icon in the menu bar), or run `ollama serve` "
                          "in another terminal window, then try again.")


def parse(content):
    """Return (dict or None). Tolerates stray text around the JSON."""
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        m = re.search(r"\{.*\}", content or "", re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


def normalise(obj):
    """Validate against the schema; coerce bad values to the fail-safe and mark them."""
    violation = False
    out = {}
    cat = obj.get("category")
    if cat not in CATEGORIES:
        cat, violation = "other_unclear", True
    sev = obj.get("severity")
    if sev not in SEVERITIES:
        sev, violation = "unclear", True
    conf = obj.get("confidence")
    if conf not in CONFIDENCE:
        conf, violation = "low", True
    vuln = obj.get("vulnerable_occupants") or []
    if not isinstance(vuln, list):
        vuln, violation = [], True
    vuln = [v for v in vuln if v in VULN]
    model_flag = obj.get("needs_human_review")
    if not isinstance(model_flag, bool):
        model_flag, violation = True, True

    out["category"] = cat
    out["severity"] = sev
    out["deadline"] = DEADLINES[sev]
    out["location"] = str(obj.get("location") or "unspecified")
    out["vulnerable_occupants"] = sorted(set(vuln))
    out["duration"] = str(obj.get("duration") or "unspecified")
    out["confidence"] = conf
    # System policy from the taxonomy, enforced in code rather than trusted to the model:
    out["needs_human_review_model"] = model_flag
    out["needs_human_review"] = bool(model_flag or sev in ("emergency", "unclear") or conf == "low")
    out["schema_violation"] = violation
    return out


FAILSAFE = {"category": "other_unclear", "severity": "unclear", "deadline": DEADLINES["unclear"],
            "location": "unspecified", "vulnerable_occupants": [], "duration": "unspecified",
            "confidence": "low", "needs_human_review_model": True, "needs_human_review": True}


def load_done(path):
    done = set()
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                try:
                    done.add(json.loads(line)["id"])
                except (json.JSONDecodeError, KeyError):
                    pass
    return done


def main():
    ap = argparse.ArgumentParser(description="Zero-shot triage through a local Ollama model.")
    ap.add_argument("--model", required=True, help="Ollama model tag, e.g. qwen3.5:4b")
    ap.add_argument("--gold", default="data/gold_v2.jsonl")
    ap.add_argument("--out", default=None, help="default: outputs/preds_<model>.jsonl")
    ap.add_argument("--limit", type=int, default=None, help="only the first N messages (smoke test)")
    ap.add_argument("--timeout", type=int, default=180, help="seconds per request")
    ap.add_argument("--fresh", action="store_true", help="discard previous results for this model")
    args = ap.parse_args()

    set_name = os.path.splitext(os.path.basename(args.gold))[0]
    out_path = args.out or os.path.join("outputs", f"preds_{set_name}_{slug(args.model)}.jsonl")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    if args.fresh and os.path.exists(out_path):
        os.remove(out_path)

    with open(args.gold) as f:
        rows = [json.loads(l) for l in f if l.strip()]
    if args.limit:
        rows = rows[:args.limit]
    done = load_done(out_path)
    todo = [r for r in rows if r["id"] not in done]
    print(f"spec v{spec.SPEC_VERSION}  prompt {PROMPT_HASH}")
    print(f"model: {args.model}   set: {set_name}   messages: {len(rows)}   already done: {len(rows) - len(todo)}   to run: {len(todo)}")
    if not todo:
        print(f"Nothing to do. Predictions are in {out_path}")
        return

    client = Client(args.model, args.timeout)
    print("loading model (the first call is slow — it's reading the weights into memory)…", flush=True)
    t0 = time.perf_counter()
    client.chat("Warm-up message: the kitchen tap is dripping.")
    print(f"model loaded in {time.perf_counter() - t0:.1f}s\n", flush=True)

    n_fail = 0
    t_start = time.perf_counter()
    with open(out_path, "a") as fout:
        for k, row in enumerate(todo, 1):
            t = time.perf_counter()
            obj, attempts = None, 0
            while obj is None and attempts < 2:
                attempts += 1
                resp = client.chat(row["text"], temperature=0.0 if attempts == 1 else 0.3)
                obj = parse(resp.get("message", {}).get("content", ""))
            latency = (time.perf_counter() - t) * 1000

            if obj is None:
                pred = dict(FAILSAFE, parse_error=True, schema_violation=True)
                n_fail += 1
            else:
                pred = normalise(obj)
                pred["parse_error"] = False
            pred["id"] = row["id"]
            pred["latency_ms"] = round(latency, 1)
            pred["attempts"] = attempts
            pred["model"] = args.model
            pred["spec_version"] = spec.SPEC_VERSION
            pred["prompt_hash"] = PROMPT_HASH
            fout.write(json.dumps(pred) + "\n")
            fout.flush()

            elapsed = time.perf_counter() - t_start
            eta = elapsed / k * (len(todo) - k)
            tag = "PARSE FAIL" if pred["parse_error"] else f"{pred['category']}/{pred['severity']}"
            print(f"[{k:>3}/{len(todo)}] {row['id']}  {tag:<32} {latency/1000:5.1f}s   eta {eta/60:4.1f} min",
                  flush=True)

    print(f"\ndone. {len(todo)} predictions written to {out_path}  (parse failures: {n_fail})")
    print(f"score it with:\n  python3 src/evaluate.py --gold {args.gold} --pred {out_path} "
          f"--name \"Zero-shot {args.model}\" --json outputs/metrics_{set_name}_{slug(args.model)}.json")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstopped. Progress is saved — re-run the same command to continue.")
