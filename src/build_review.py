#!/usr/bin/env python3
"""Builds review_gold_v2.html: a self-contained page for approving the v1 -> v2 gold changes."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import spec, gold_v2_proposals as P

gold = [json.loads(l) for l in open("data/gold.jsonl")]
rules = {r["id"]: {"text": r["text"], "source": r["source"], "kind": r["kind"]} for r in spec.RULES}

items = []
for g in gold:
    i = g["id"]; cur = g["gold"]
    it = {"id": i, "text": g["text"], "cur": cur, "fields": []}
    if i in P.SEV:
        s, r, note = P.SEV[i]
        it["fields"].append({"field": "severity", "tier": "rule", "to": s, "rules": r, "note": note})
    if i in P.FORCED:
        s, alt, r, note = P.FORCED[i]
        it["fields"].append({"field": "severity", "tier": "forced", "to": s, "alt": alt, "rules": r, "note": note})
    if i in P.SUGGEST:
        s, r, note = P.SUGGEST[i]
        it["fields"].append({"field": "severity", "tier": "suggest", "to": s, "rules": r, "note": note})
    if i in P.CAT:
        c, r, note = P.CAT[i]
        it["fields"].append({"field": "category", "tier": "rule", "to": c, "rules": r, "note": note})
    it["also"] = P.ALSO.get(i, [])
    it["vuln_add"] = P.VULN_ADD.get(i, [])
    tiers = {f["tier"] for f in it["fields"]}
    it["group"] = ("suggest" if "suggest" in tiers else "forced" if "forced" in tiers
                   else "rule" if tiers else "additions" if (it["also"] or it["vuln_add"]) else "none")
    items.append(it)

data = {"items": items, "rules": rules, "spec_version": spec.SPEC_VERSION}
html = open("src/review_template.html").read().replace("/*__DATA__*/null", json.dumps(data))
open("review_gold_v2.html", "w").write(html)
from collections import Counter
print("groups:", dict(Counter(it["group"] for it in items)))
