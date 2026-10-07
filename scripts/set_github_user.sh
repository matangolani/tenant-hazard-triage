#!/usr/bin/env bash
# Put your GitHub username into the README and the write-up page:  bash scripts/set_github_user.sh <username>
set -euo pipefail
cd "$(dirname "$0")/.."
U="${1:?usage: bash scripts/set_github_user.sh <github-username>}"
python3 - "$U" <<'PY'
import re, sys
u = sys.argv[1]
for p in ("README.md", "docs/index.html", "PORTFOLIO_HANDOFF.md"):
    s = open(p).read()
    s = s.replace("REPLACE-WITH-GITHUB-USERNAME", u).replace("<username>", u)
    s = re.sub(r"github\.com/[A-Za-z0-9-]+/tenant-hazard-triage", f"github.com/{u}/tenant-hazard-triage", s)
    open(p, "w").write(s)
print(f"set GitHub user to {u}")
PY
