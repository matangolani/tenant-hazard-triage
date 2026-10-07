#!/usr/bin/env python3
"""
Tenant Hazard Triage — synthetic training data generator.

Teacher: GLM-5.3-Flash via OpenRouter (an open-weight model, so the
"distil an open model into a small local one" story stays clean).

Design (see RESULTS.md for the reasoning):
  * Targets are sampled in code, not left to the model — we control coverage and balance.
  * 60% of calls ask for CONTRAST PAIRS: two near-identical messages that differ in
    one decisive detail and land on different severities. This targets the
    emergency/significant boundary where zero-shot models fail.
  * Every call randomises persona, channel, length and messiness (anti mode-collapse).
  * The teacher sees ONLY spec rules — never gold or official test items.
  * Every message is re-labelled blind by the teacher using the same prompt the
    student will use; kept only if severity agrees with the target ("round trip").
  * Exact checks: schema, policy (other_unclear can't be significant), length,
    near-duplicates, and similarity to every test item (contamination guard).

Standard library only. Needs an OpenRouter key in the environment:
    export OPENROUTER_API_KEY="sk-or-..."
    python3 src/generate_synth.py --calls 20          # smoke test (~30 messages, ~1p)
    python3 src/generate_synth.py --calls 900         # full run (~1,300 kept, ~$1-3); stops at --max-usd (default $4)

Every API call is logged to data/synth/calls.jsonl (tokens, thinking tokens, finish reason,
provider, seconds, cost) so speed and spend can be diagnosed from data.

Output (data/synth/): train.jsonl, val.jsonl, rejected.jsonl, raw.jsonl, stats.json
Resumable: re-running continues from raw.jsonl.
"""
import argparse, json, os, random, re, sys, threading, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec

API_URL = os.environ.get("OPENROUTER_BASE", "https://openrouter.ai/api/v1").rstrip("/") + "/chat/completions"
TEACHER = "z-ai/glm-5.3-flash"
PRICE_IN, PRICE_OUT = 0.0352e-6, 0.50e-6       # USD per token (OpenRouter listing, Oct 2026)
GEN_MAX_TOKENS, VERIFY_MAX_TOKENS = 4000, 1500  # GLM-5.3-Flash always thinks first; thinking counts toward these
OUT = "data/synth"

# ------------------------------------------------------------- diversity knobs
PERSONAS = ["a young parent", "a pensioner living alone", "a working adult sharing a flat", "a carer reporting for a relative",
            "a neighbour reporting on someone's behalf", "a student", "someone whose first language isn't English",
            "a frustrated long-term tenant", "a polite, formal tenant", "someone who downplays problems",
            "a night-shift worker", "a disabled tenant", "a parent of teenagers", "a tenant who has reported this before"]
CHANNELS = ["a text message", "an online repairs form", "an email", "a WhatsApp message",
            "a call-centre agent's note written in the third person ('Tenant reports...')", "a voicemail transcript"]
LENGTHS = [("very short", "under 15 words"), ("short", "15-35 words"), ("medium", "35-70 words"), ("long", "70-130 words")]
QUIRKS = ["no punctuation and lowercase", "a couple of typos", "mentions an earlier repair that never happened",
          "mentions an unrelated second minor issue", "says 'see photo'", "is angry about the landlord",
          "is apologetic about bothering them", "uses vague words like 'thing' and 'stuff'", "is clear and well written",
          "rambles before getting to the point"]
CONTRAST_AXES = {
    "damp_mould":     ["a particularly vulnerable person present vs not", "symptoms reported vs none", "widespread in a bedroom vs a small isolated patch"],
    "excess_cold":    ["a particularly vulnerable person present vs not", "symptoms reported vs none", "whole home without heat vs one room"],
    "excess_heat":    ["a particularly vulnerable person present vs not", "serious heat symptoms vs none", "caused by a defect vs hot weather only"],
    "falls":          ["a fall very likely (already near-misses, vulnerable person) vs merely possible", "a defect causing it vs an everyday trip"],
    "structural":     ["imminent danger (sudden or worsening cracks, sagging, displaced elements) vs stable", "potential for serious harm vs superficial"],
    "fire_explosion": ["an active fire/gas/alarm failure vs an issue with no fire risk"],
    "electrical":     ["exposed live parts or shocks vs a deteriorated but not dangerous installation", "within reach of a young child vs not", "dangerous fault vs simple dead socket"],
    "hygiene_pests":  ["loss of the only toilet or sewage escaping vs a slow drain", "serious infestation in the kitchen vs occasional pests", "young children present vs not"],
    "other_unclear":  ["a door that cannot be secured at all overnight vs one that is stiff but locks"],
}
# severity pairs that sit on a boundary
PAIRS = {c: [("emergency", "significant"), ("significant", "routine")] for c in spec.AWAAB_SIGNIFICANT_CATEGORIES}
PAIRS["fire_explosion"] = [("emergency", "routine"), ("emergency", "significant")]
PAIRS["other_unclear"] = [("emergency", "routine")]

GEN_SCHEMA = {"type": "object", "properties": {"messages": {"type": "array", "items": {"type": "object", "properties": {
    "text": {"type": "string"}, "category": {"type": "string", "enum": list(spec.CATEGORIES)},
    "severity": {"type": "string", "enum": spec.SEVERITIES}, "location": {"type": "string"},
    "vulnerable_occupants": {"type": "array", "items": {"type": "string", "enum": spec.VULN}},
    "duration": {"type": "string"}, "decisive_detail": {"type": "string"}},
    "required": ["text", "category", "severity", "location", "vulnerable_occupants", "duration", "decisive_detail"]}}},
    "required": ["messages"]}


def rules_for(cat):
    rs = [r for r in spec.RULES if r["applies_to"] in ("all", cat)]
    return "\n".join(f"- {r['text']}" for r in rs)


def make_job(rng, k):
    style = dict(persona=rng.choice(PERSONAS), channel=rng.choice(CHANNELS), length=rng.choice(LENGTHS), quirk=rng.choice(QUIRKS))
    r = rng.random()
    if r < 0.60:                                   # contrast pair
        cat = rng.choice(list(PAIRS))
        a, b = rng.choice(PAIRS[cat]); axis = rng.choice(CONTRAST_AXES[cat])
        targets = [(cat, a), (cat, b)]
        kind = "contrast"
    elif r < 0.90:                                 # single, Awaab category
        cat = rng.choice(spec.AWAAB_SIGNIFICANT_CATEGORIES)
        sev = rng.choices(["emergency", "significant", "routine"], [0.35, 0.35, 0.30])[0]
        targets, axis, kind = [(cat, sev)], None, "single"
    elif r < 0.97:                                 # not a hazard at all
        targets, axis, kind = [("other_unclear", "routine")], None, "admin"
    else:                                          # too vague to judge
        targets, axis, kind = [("other_unclear", "unclear")], None, "vague"
    return dict(job_id=f"job-{k:05d}", kind=kind, targets=targets, axis=axis, style=style)


def build_gen_prompt(job):
    s = job["style"]
    cat = job["targets"][0][0]
    head = (f"Write realistic repair reports that social-housing tenants in England send to their landlord. "
            f"Style: written by {s['persona']}, as {s['channel']}, {s['length'][0]} ({s['length'][1]}), and it {s['quirk']}. "
            "British English. No names, addresses or phone numbers. Never use the words 'emergency', 'significant', 'routine', "
            "'hazard', 'Awaab' or 'category'. The tenant describes the situation in their own words; they are not classifying it.")
    if job["kind"] == "contrast":
        (c, a), (_, b) = job["targets"]
        task = (f"Write TWO messages about the same kind of {c.replace('_', ' ')} problem in the same home, nearly identical, "
                f"differing ONLY in one decisive detail ({job['axis']}). Under the rules below, message 1 must be '{a}' and "
                f"message 2 must be '{b}'. The difference must be clear from the text alone.")
    elif job["kind"] == "admin":
        task = "Write ONE message that is not about any hazard (e.g. an admin request, keys, rent, cosmetic wear, a doorbell, noise from neighbours). Label it other_unclear / routine."
    elif job["kind"] == "vague":
        task = "Write ONE message that hints something is wrong but gives no information to judge what or how serious. Label it other_unclear / unclear."
    else:
        c, sv = job["targets"][0]
        task = f"Write ONE message about a {c.replace('_', ' ')} problem that, under the rules below, is '{sv}'."
    return (f"{head}\n\nTASK: {task}\n\nRULES THE LABEL MUST FOLLOW:\n{rules_for(cat)}\n\n"
            "For each message return text plus its label: category, severity, location (room or 'unspecified'), "
            "vulnerable_occupants (only people the text mentions), duration (or 'unspecified'), and decisive_detail "
            "(the phrase in the text that decides the severity).")


class Client:
    """OpenRouter client with per-call logging, output caps, reasoning control and a hard spend cap."""
    def __init__(self, key, reasoning="none", max_usd=2.0, log_path=None):
        self.key, self.reasoning, self.max_usd, self.log_path = key, reasoning, max_usd, log_path
        self.lock = threading.Lock(); self.stop = threading.Event()
        self.tokens_in = self.tokens_out = self.reasoning_tokens = self.n_calls = 0
        self.cost_reported = 0.0; self.cost_estimated = 0.0
        self.stop_reason = None; self.no_reasoning_param = False; self.first_error = None; self.n_failed = 0

    @property
    def cost(self):          # OpenRouter's own figure when it sends one, otherwise our estimate
        return max(self.cost_reported, self.cost_estimated)

    def call(self, messages, schema, temperature, name, max_tokens, reasoning=None):
        reasoning = reasoning or self.reasoning
        body = {"model": TEACHER, "messages": messages, "temperature": temperature, "max_tokens": max_tokens,
                "usage": {"include": True},
                "response_format": {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}}}
        if reasoning != "default" and not self.no_reasoning_param:
            body["reasoning"] = {"effort": reasoning}
        for attempt in range(4):
            if self.stop.is_set():
                return None
            t0 = time.time(); rec = {"name": name, "attempt": attempt}
            try:
                req = urllib.request.Request(API_URL, data=json.dumps(body).encode(), headers={
                    "Authorization": f"Bearer {self.key}", "Content-Type": "application/json",
                    "X-Title": "Tenant Hazard Triage synthetic data"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    resp = json.loads(r.read().decode())
                u = resp.get("usage") or {}
                ti, to = u.get("prompt_tokens", 0) or 0, u.get("completion_tokens", 0) or 0
                rt = ((u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0)
                ch = resp["choices"][0]
                rec.update(provider=resp.get("provider"), tokens_in=ti, tokens_out=to, reasoning_tokens=rt,
                           finish=ch.get("finish_reason"), cost=u.get("cost"), secs=round(time.time() - t0, 1))
                with self.lock:
                    self.n_calls += 1; self.tokens_in += ti; self.tokens_out += to; self.reasoning_tokens += rt
                    self.cost_estimated += ti * PRICE_IN + to * PRICE_OUT
                    if isinstance(u.get("cost"), (int, float)):
                        self.cost_reported += u["cost"]
                    if self.cost >= self.max_usd:
                        self.stop_reason = self.stop_reason or "budget"; self.stop.set()
                if ch.get("finish_reason") == "length":
                    raise ValueError("hit max_tokens")
                content = ch["message"]["content"]
                return json.loads(re.search(r"\{.*\}", content, re.S).group(0))
            except urllib.error.HTTPError as e:
                msg = e.read().decode(errors="replace")[:300]
                rec.update(error=f"HTTP {e.code}: {msg}", secs=round(time.time() - t0, 1))
                if e.code == 400 and "reasoning" in msg.lower() and "reasoning" in body:
                    with self.lock:
                        if not self.no_reasoning_param:
                            print("  note: the API rejected the reasoning setting; continuing without it", flush=True)
                        self.no_reasoning_param = True   # model won't take it; retry without
                    body.pop("reasoning", None)
                if e.code in (401, 402, 403):
                    self._log(rec)
                    sys.exit(f"\nOpenRouter refused the request (HTTP {e.code}): {msg}\n"
                             "Check OPENROUTER_API_KEY is set and the account has credit.")
                time.sleep(2 ** attempt)
            except Exception as e:
                rec.update(error=f"{type(e).__name__}: {str(e)[:200]}", secs=round(time.time() - t0, 1))
                time.sleep(2 ** attempt)
            finally:
                self._log(rec)
                if "error" in rec:
                    with self.lock:
                        self.first_error = self.first_error or rec["error"]
        with self.lock:
            self.n_failed += 1
            if self.n_failed >= 10 and self.n_calls == 0:     # nothing has worked: stop, don't burn time
                if not self.stop.is_set():
                    print(f"\n10 calls failed and none succeeded. First error:\n  {self.first_error}\n", flush=True)
                self.stop_reason = self.stop_reason or "failing"; self.stop.set()
        return None

    def _log(self, rec):
        if self.log_path and not rec.get("_logged"):
            rec["_logged"] = True
            with self.lock:
                with open(self.log_path, "a") as f:
                    f.write(json.dumps({k: v for k, v in rec.items() if k != "_logged"}) + "\n")


# ------------------------------------------------------------- quality checks
def shingles(t, n=5):
    t = re.sub(r"[^a-z0-9 ]", "", t.lower()); t = re.sub(r"\s+", " ", t)
    return {t[i:i + n] for i in range(max(1, len(t) - n + 1))}


def jacc(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


OVERLAP = [{"fire_explosion", "electrical"}, {"damp_mould", "excess_cold"}, {"damp_mould", "structural"},
           {"structural", "falls"}, {"hygiene_pests", "damp_mould"}, {"electrical", "structural"}]


def cat_ok(a, b):
    return a == b or any({a, b} <= s for s in OVERLAP)


def check_message(job, idx, m, test_sh, other_job_sh):
    """Return (row, reason). reason is None if the message is kept.
    other_job_sh: shingles of messages kept from OTHER jobs (contrast pairs are near-identical by design,
    so a message is never compared with its own pair partner)."""
    tc, ts = job["targets"][idx] if idx < len(job["targets"]) else (None, None)
    text = (m.get("text") or "").strip(); v = m.get("verifier") or {}
    words = len(text.split()); sh = shingles(text)
    reason = None
    if not text or words < 2 or words > 180: reason = "length"
    elif m.get("category") != tc or m.get("severity") != ts: reason = "generator_off_target"
    elif tc == "other_unclear" and ts == "significant": reason = "policy"
    elif re.search(r"\b(emergency|significant|routine|hazard|awaab)\b", text, re.I): reason = "leaked_label_word"
    elif max((jacc(sh, t) for t in test_sh), default=0) >= 0.5: reason = "too_close_to_test_item"
    elif any(jacc(sh, o) >= 0.6 for o in other_job_sh): reason = "near_duplicate"
    elif v.get("severity") != ts: reason = "verifier_disagrees_severity"
    elif not cat_ok(v.get("category"), tc): reason = "verifier_disagrees_category"
    row = {"job_id": job["job_id"], "kind": job["kind"], "text": text,
           # category/severity come from the sampled target (checked against the blind verifier above);
           # the extraction fields come from the blind verifier, which reads the text exactly as the student will
           "label": {"category": tc, "severity": ts,
                     "location": v.get("location") or m.get("location") or "unspecified",
                     "vulnerable_occupants": sorted(set(x for x in (v.get("vulnerable_occupants")
                                                    if v.get("vulnerable_occupants") is not None
                                                    else (m.get("vulnerable_occupants") or [])) if x in spec.VULN)),
                     "duration": v.get("duration") or m.get("duration") or "unspecified"},
           "verifier": {"category": v.get("category"), "severity": v.get("severity")},
           "decisive_detail": m.get("decisive_detail"), "style": job.get("style")}
    return row, reason, sh


def filter_jobs(raws, test_sh):
    kept, rejected, kept_sh = [], [], []
    for job in raws:
        group, group_sh = [], []
        for idx, m in enumerate(job["messages"]):
            row, reason, sh = check_message(job, idx, m, test_sh, kept_sh)
            if reason:
                row["reason"] = reason; rejected.append(row)
            else:
                group.append(row); group_sh.append(sh)
        if job["kind"] == "contrast" and len(group) == 1:
            group[0]["kind"] = "contrast_half"     # partner failed; the survivor is still a verified example
        if group:
            kept.append(group); kept_sh.extend(group_sh)
    return kept, rejected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calls", type=int, default=20)
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--max-usd", type=float, default=4.0, help="stop cleanly once this much has been spent (default $4)")
    # This teacher can't switch thinking off (HTTP 400 "Reasoning is mandatory"), so the lowest useful setting is the default.
    ap.add_argument("--reasoning", default="low", choices=["minimal", "low", "medium", "default"],
                    help="thinking effort when WRITING messages (default low)")
    ap.add_argument("--verify-reasoning", default="low", choices=["minimal", "low", "medium", "default"],
                    help="thinking effort when RE-LABELLING messages blind (default low)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--val-frac", type=float, default=0.1)
    a = ap.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("Set your key first:  export OPENROUTER_API_KEY=\"sk-or-...\"")
    os.makedirs(OUT, exist_ok=True)
    raw_path = os.path.join(OUT, "raw.jsonl")

    # test items we must never resemble (contamination guard)
    test_texts = []
    for f in ["data/gold.jsonl", "data/gold_v2.jsonl", "data/official.jsonl"]:
        if os.path.exists(f):
            test_texts += [json.loads(l)["text"] for l in open(f) if l.strip()]
    test_sh = [shingles(t) for t in test_texts]
    if not test_sh:
        sys.exit("No test sets found in data/ — run from the project folder.")

    rng = random.Random(a.seed)
    jobs = [make_job(rng, k) for k in range(a.calls)]
    done = set()
    if os.path.exists(raw_path):
        prev = [json.loads(l) for l in open(raw_path) if l.strip()]
        prev = [j for j in prev if j.get("messages") and all(m.get("verifier") for m in j["messages"])]
        # ^ jobs where writing or checking failed are redone, not counted
        with open(raw_path, "w") as f:
            for j in prev: f.write(json.dumps(j) + "\n")
        done = {j["job_id"] for j in prev}
    todo = [j for j in jobs if j["job_id"] not in done]
    print(f"teacher {TEACHER}  spec v{spec.SPEC_VERSION}  calls {a.calls}  already done {len(done)}  to run {len(todo)}")

    cli = Client(key, reasoning=a.reasoning, max_usd=a.max_usd, log_path=os.path.join(OUT, "calls.jsonl"))
    print(f"reasoning: write={a.reasoning} verify={a.verify_reasoning}  workers={a.workers}  spend cap ${a.max_usd:.2f}")
    student_prompt = spec.render_prompt()
    wlock = threading.Lock()

    def run(job):
        if cli.stop.is_set():
            return 0
        g = cli.call([{"role": "user", "content": build_gen_prompt(job)}], GEN_SCHEMA, 0.9, "tenant_messages", GEN_MAX_TOKENS)
        out = {"job_id": job["job_id"], "kind": job["kind"], "targets": job["targets"], "axis": job["axis"],
               "style": job["style"], "messages": []}
        if not (g and isinstance(g.get("messages"), list) and g["messages"]):
            return 0        # generation failed: don't save, so a re-run retries this job
        for m in g["messages"][:len(job["targets"])]:
            v = cli.call([{"role": "system", "content": student_prompt},
                          {"role": "user", "content": 'Tenant message:\n"""\n' + m.get("text", "") + '\n"""'}],
                         spec.SCHEMA, 0.0, "triage", VERIFY_MAX_TOKENS, reasoning=a.verify_reasoning)
            if not v:
                return 0    # checker call failed: don't save; a re-run redoes the whole job
            m["verifier"] = v
            out["messages"].append(m)
        if cli.stop.is_set():
            return 0        # budget hit mid-job: don't save a half-finished job; it is redone on resume
        with wlock:
            with open(raw_path, "a") as f:
                f.write(json.dumps(out) + "\n")
        return len(out["messages"])

    t0 = time.time(); n = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(run, j) for j in todo]
        for k, fu in enumerate(as_completed(futs), 1):
            n += fu.result() or 0
            if k % 10 == 0 or k == len(todo):
                avg = cli.tokens_out / max(1, cli.n_calls)
                print(f"  {k}/{len(todo)} jobs  {n} messages  {time.time() - t0:.0f}s  ${cli.cost:.3f}  "
                      f"avg out/call {avg:.0f} tok (thinking {cli.reasoning_tokens:,})", flush=True)
    if cli.stop_reason == "failing":
        sys.exit("Stopped: the API isn't accepting requests (error above). Nothing was saved for these jobs; "
                 "fix the cause and re-run the same command.")
    if cli.stop_reason == "budget":
        print(f"\nSpend cap reached (${cli.cost:.2f} >= ${a.max_usd:.2f}). Progress is saved; "
              "re-run with a higher --max-usd to continue.")

    # --------------------------------------------------------- filter + split
    raws = [json.loads(l) for l in open(raw_path) if l.strip()]
    kept, rejected = filter_jobs(raws, test_sh)

    rng2 = random.Random(a.seed + 1); rng2.shuffle(kept)       # split by job, so pairs never straddle train/val
    n_val = max(1, int(len(kept) * a.val_frac))
    val = [r for g in kept[:n_val] for r in g]; train = [r for g in kept[n_val:] for r in g]

    def target_output(r):   # exactly what the student must learn to emit
        L = dict(r["label"])
        L["confidence"] = "low" if L["severity"] == "unclear" else ("high" if r["verifier"]["category"] == L["category"] else "medium")
        L["needs_human_review"] = L["severity"] in ("emergency", "unclear") or L["confidence"] == "low"
        return L

    for name, rows in [("train", train), ("val", val)]:
        with open(os.path.join(OUT, f"{name}.jsonl"), "w") as f:
            for r in rows:
                f.write(json.dumps({"id": f"{r['job_id']}", "text": r["text"], "output": target_output(r),
                                    "kind": r["kind"]}) + "\n")
    with open(os.path.join(OUT, "rejected.jsonl"), "w") as f:
        for r in rejected: f.write(json.dumps(r) + "\n")

    from collections import Counter
    allk = train + val
    stats = {"teacher": TEACHER, "spec_version": spec.SPEC_VERSION, "calls": len(raws),
             "generated": sum(len(j["messages"]) for j in raws), "kept": len(allk), "train": len(train), "val": len(val),
             "rejected_by_reason": dict(Counter(r["reason"] for r in rejected)),
             "severity": dict(Counter(r["label"]["severity"] for r in allk)),
             "category": dict(Counter(r["label"]["category"] for r in allk)),
             "kind": dict(Counter(r["kind"] for r in allk)),
             "api_calls_this_run": cli.n_calls, "tokens_in": cli.tokens_in, "tokens_out": cli.tokens_out,
             "reasoning_tokens": cli.reasoning_tokens,
             "avg_tokens_out_per_call": round(cli.tokens_out / max(1, cli.n_calls), 1),
             "cost_usd_reported_by_openrouter": round(cli.cost_reported, 4),
             "est_cost_usd_this_run": round(cli.cost_estimated, 4),
             "reasoning": a.reasoning, "verify_reasoning": a.verify_reasoning, "seconds": round(time.time() - t0, 1)}
    json.dump(stats, open(os.path.join(OUT, "stats.json"), "w"), indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstopped — progress saved in data/synth/raw.jsonl; re-run to continue.")
