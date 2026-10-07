"""
Tenant Hazard Triage — fine-tuning and evaluation helpers.

Used by notebooks/hazard_triage_finetune.ipynb on Kaggle. Everything that doesn't need a GPU
(prompt building, loss masking, parsing, prediction records) lives here so it can be
unit-tested locally (tests/check_ft_lib.py).

Design rules:
  * The student sees EXACTLY the prompt used for the zero-shot bake-off
    (same system prompt from spec.py, same user wrapper), so base vs fine-tuned
    differ only in the weights.
  * Loss is computed on the answer only (prompt tokens are masked with -100).
  * The answer is the JSON object in spec.SCHEMA key order, then the chat
    template's end-of-turn marker, so the model learns to stop.
  * Predictions are normalised with the SAME code as the Ollama runner and
    written in the same record format, so src/evaluate.py and src/compare.py
    score them without changes.
"""
import json, time

import spec
from zeroshot_runner import SYSTEM_PROMPT, PROMPT_HASH, normalise, parse, FAILSAFE

KEYS = list(spec.SCHEMA["properties"].keys())


def user_turn(text):
    return 'Tenant message:\n"""\n' + text + '\n"""'


def prompt_messages(text):
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_turn(text)}]


def target_json(output):
    """The answer the student must produce, in schema key order."""
    missing = [k for k in KEYS if k not in output]
    if missing:
        raise ValueError(f"training target is missing {missing}")
    return json.dumps({k: output[k] for k in KEYS}, ensure_ascii=False)


def text_tokenizer(tok):
    """Multimodal models come with a processor; calling one with text first treats it as images. Use its tokenizer."""
    return getattr(tok, "tokenizer", tok)


def chat_text(tok, messages, add_generation_prompt):
    """Render with the model's chat template, thinking switched off where the template supports it."""
    tok = text_tokenizer(tok)
    kw = dict(tokenize=False, add_generation_prompt=add_generation_prompt)
    try:
        return tok.apply_chat_template(messages, enable_thinking=False, **kw)
    except TypeError:
        return tok.apply_chat_template(messages, **kw)


def end_marker(tok):
    """Whatever the template puts after an assistant answer (e.g. '<|im_end|>\\n' or '<end_of_turn>\\n')."""
    probe = '{"probe": 12345}'
    full = chat_text(tok, prompt_messages("x") + [{"role": "assistant", "content": probe}], False)
    i = full.rfind(probe)
    if i < 0:
        raise RuntimeError("chat template dropped the assistant answer; can't find the end-of-turn marker")
    return full[i + len(probe):]


def encode(tok, text, output, max_len, marker):
    """Token ids for prompt + answer, with the prompt masked out of the loss."""
    tok = text_tokenizer(tok)
    p_ids = tok(chat_text(tok, prompt_messages(text), True), add_special_tokens=False)["input_ids"]
    t_ids = tok(target_json(output) + marker, add_special_tokens=False)["input_ids"]
    if len(p_ids) + len(t_ids) > max_len:
        return None                                   # dropped rather than silently truncating the answer
    return {"input_ids": p_ids + t_ids,
            "attention_mask": [1] * (len(p_ids) + len(t_ids)),
            "labels": [-100] * len(p_ids) + t_ids}


class Collator:
    """Right-pads a batch; padding never contributes to the loss."""
    def __init__(self, pad_id):
        self.pad_id = pad_id

    def __call__(self, feats):
        import torch
        n = max(len(f["input_ids"]) for f in feats)
        out = {"input_ids": [], "attention_mask": [], "labels": []}
        for f in feats:
            gap = n - len(f["input_ids"])
            out["input_ids"].append(f["input_ids"] + [self.pad_id] * gap)
            out["attention_mask"].append(f["attention_mask"] + [0] * gap)
            out["labels"].append(f["labels"] + [-100] * gap)
        return {k: torch.tensor(v) for k, v in out.items()}


def to_record(row_id, raw_text, model_name, latency_ms):
    """One prediction line, same shape as the Ollama runner writes."""
    obj = parse(raw_text)
    if obj is None:
        pred = dict(FAILSAFE, parse_error=True, schema_violation=True)
    else:
        pred = normalise(obj)
        pred["parse_error"] = False
    pred.update(id=row_id, latency_ms=round(latency_ms, 1), attempts=1, model=model_name,
                spec_version=spec.SPEC_VERSION, prompt_hash=PROMPT_HASH, raw=raw_text[:600])
    return pred


def predict(rows, generate_fn, model_name, batch_size=8, log=print):
    """rows: [{"id","text",...}]; generate_fn(list[str texts]) -> list[str raw answers]."""
    out = []
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        t0 = time.perf_counter()
        answers = generate_fn([r["text"] for r in batch])
        per = (time.perf_counter() - t0) * 1000 / max(1, len(batch))
        out += [to_record(r["id"], a, model_name, per) for r, a in zip(batch, answers)]
        log(f"  {min(i + batch_size, len(rows))}/{len(rows)}")
    return out


def hf_generate_fn(model, tok, max_new_tokens=200):
    """Batched greedy decoding with a Hugging Face / Unsloth model."""
    import torch
    tok = text_tokenizer(tok)
    tok.padding_side = "left"
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id

    def gen(texts):
        prompts = [chat_text(tok, prompt_messages(t), True) for t in texts]
        enc = tok(prompts, return_tensors="pt", padding=True, add_special_tokens=False).to(model.device)
        with torch.no_grad():
            seq = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False, pad_token_id=pad)
        return tok.batch_decode(seq[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)
    return gen


def synth_val_as_gold(val_rows):
    """Convert generator val rows into the gold format evaluate.py reads (ids made unique)."""
    out = []
    for k, r in enumerate(val_rows):
        o = r["output"]
        out.append({"id": f"synthval-{k:04d}", "text": r["text"],
                    "gold": {f: o[f] for f in ("category", "severity", "location", "vulnerable_occupants", "duration")}})
    return out


def write_jsonl(path, rows):
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]
