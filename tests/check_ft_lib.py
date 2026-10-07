"""Unit tests for the GPU-free parts of src/ft_lib.py, using a fake chat tokenizer.
Run:  python3 tests/check_ft_lib.py"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import ft_lib, spec


class FakeQwenTok:
    """Char-level tokenizer with a Qwen-style template (<|im_start|>/<|im_end|>, empty think block)."""
    eos_token_id = 0; pad_token_id = 0; padding_side = "right"
    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False, enable_thinking=True):
        s = "".join(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n" for m in messages)
        if add_generation_prompt:
            s += "<|im_start|>assistant\n" + ("" if enable_thinking else "<think>\n\n</think>\n\n")
        return s
    def __call__(self, text, add_special_tokens=False, **kw):
        return {"input_ids": [ord(c) for c in text]}


class FakeGemmaTok(FakeQwenTok):
    """No enable_thinking kwarg (like templates that don't support it)."""
    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False):
        s = "".join(f"<start_of_turn>{m['role']}\n{m['content']}<end_of_turn>\n" for m in messages)
        return s + ("<start_of_turn>model\n" if add_generation_prompt else "")


OUT = {"category": "damp_mould", "severity": "emergency", "location": "bedroom", "vulnerable_occupants": ["infant"],
       "duration": "weeks", "confidence": "high", "needs_human_review": True}
fails = 0
def check(name, cond):
    global fails
    print(("PASS " if cond else "FAIL ") + name); fails += (not cond)

# 1 target order and content
tj = ft_lib.target_json(dict(reversed(list(OUT.items()))))
check("target JSON follows schema key order", list(json.loads(tj).keys()) == list(spec.SCHEMA["properties"].keys()))
try:
    ft_lib.target_json({"category": "x"}); check("missing keys rejected", False)
except ValueError:
    check("missing keys rejected", True)

for Tok in (FakeQwenTok, FakeGemmaTok):
    tok = Tok(); n = Tok.__name__
    mk = ft_lib.end_marker(tok)
    check(f"{n}: end marker found", mk in ("<|im_end|>\n", "<end_of_turn>\n"))
    enc = ft_lib.encode(tok, "mould in baby's room", OUT, 20000, mk)
    ids, lab = enc["input_ids"], enc["labels"]
    answer = "".join(chr(i) for i, l in zip(ids, lab) if l != -100)
    check(f"{n}: only the answer is trained on", answer == ft_lib.target_json(OUT) + mk)
    prompt = "".join(chr(i) for i, l in zip(ids, lab) if l == -100)
    check(f"{n}: trained prompt == inference prompt", prompt == ft_lib.chat_text(tok, ft_lib.prompt_messages("mould in baby's room"), True))
    check(f"{n}: system prompt is the bake-off prompt", ft_lib.SYSTEM_PROMPT in prompt and 'Tenant message:\n"""\nmould' in prompt)
    check(f"{n}: over-long example dropped, not truncated", ft_lib.encode(tok, "x", OUT, 50, mk) is None)

check("thinking switched off for Qwen-style template", "<think>\n\n</think>" in ft_lib.chat_text(FakeQwenTok(), ft_lib.prompt_messages("x"), True))

# 2 records match runner format and normalisation
rows = [{"id": "g1", "text": "a"}, {"id": "g2", "text": "b"}, {"id": "g3", "text": "c"}]
answers = {"a": ft_lib.target_json(OUT),
           "b": 'sure! {"category":"falls","severity":"significant","location":"stairs","vulnerable_occupants":[],"duration":"unspecified","confidence":"high","needs_human_review":false}',
           "c": "I cannot answer"}
recs = ft_lib.predict(rows, lambda ts: [answers[t] for t in ts], "ft-test", batch_size=2, log=lambda *a: None)
check("one record per row, ids kept", [r["id"] for r in recs] == ["g1", "g2", "g3"])
check("emergency forced to human review (runner policy)", recs[0]["needs_human_review"] is True and recs[0]["deadline"] == spec.DEADLINES["emergency"])
check("stray text around JSON tolerated", recs[1]["severity"] == "significant" and not recs[1]["parse_error"])
check("unparseable answer -> fail-safe", recs[2]["parse_error"] and recs[2]["severity"] == "unclear" and recs[2]["needs_human_review"])
check("record carries spec version + prompt hash", recs[0]["prompt_hash"] == ft_lib.PROMPT_HASH and recs[0]["spec_version"] == spec.SPEC_VERSION)

# 3 synthetic val -> gold format, unique ids
g = ft_lib.synth_val_as_gold([{"id": "job-1", "text": "t", "output": OUT}, {"id": "job-1", "text": "u", "output": OUT}])
check("synth val ids unique + gold fields present", len({r["id"] for r in g}) == 2 and g[0]["gold"]["severity"] == "emergency")

# 4 collator (needs torch)
try:
    import torch
    b = ft_lib.Collator(0)([{"input_ids": [5, 6, 7], "attention_mask": [1, 1, 1], "labels": [-100, 6, 7]},
                           {"input_ids": [5], "attention_mask": [1], "labels": [5]}])
    check("collator pads labels with -100", b["labels"].tolist() == [[-100, 6, 7], [5, -100, -100]] and b["attention_mask"].tolist()[1] == [1, 0, 0])
except ImportError:
    print("SKIP collator test (torch not installed here)")

print(f"\n{'ALL PASSED' if not fails else str(fails) + ' FAILED'}")
sys.exit(1 if fails else 0)
