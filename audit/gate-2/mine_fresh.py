"""G1-prime pool: random real (action, output) turns per operation, never seen by the designer.

Excludes every turn id that appears in Data/g1/real_outcomes.json or real_receipts.json (the designer read those).
Per operation, a reservoir sample (seed 20261005) of up to 15 turns whose output matches a broad trouble pattern
and up to 15 turns whose output does not; the independent labellers decide the real outcome. Prints counts only.
"""
import gzip
import json
import random
import re
from pathlib import Path

SEED = 20261005
OUT = Path(r"C:\Users\joshd\Data\g1v2")
seen = set()
for f in ("real_outcomes.json", "real_receipts.json"):
    for lst in json.load(open(Path(r"C:\Users\joshd\Data\g1") / f, encoding="utf-8"))["examples"].values():
        seen.update(e["id"] for e in lst)
OPS = {
    "push": r"\bgit push\b",
    "merge": r"\bgh pr merge\b",
    "deploy": r"\b(?:surge\b|netlify deploy|wrangler (?:pages )?deploy|vercel\b|firebase deploy|fly deploy|gh-pages\b|npm run deploy)",
    "post": r"(?:curl|gh api)\b[^\n]*(?:-X\s*POST|--method POST|--request POST)[^\n]*(?:comment|post|discussion|message|issue|repl)|gh (?:issue|pr) comment\b",
    "send": r"gmail_cli\.py send|send_email|smtplib|sendmail|\bmsmtp\b",
    "fix": r"\b(?:pytest|npm test|node --test|python3? -m unittest|npm run test|jest\b|mocha\b|vitest\b)",
    "upload": r"\bgh release upload\b|\brclone (?:copy|sync)\b|\bgsutil cp\b|\baws s3 cp\b|curl\b[^\n]*-F\s+['\"]?file=|\bscp\b",
    "create": r"\bgh (?:issue|repo|release|pr) create\b",
    "publish": r"\bnpm publish\b|\btwine upload\b|\bgh release create\b",
}
TROUBLE = re.compile(r"error|fail|denied|refused|rejected|invalid|traceback|exception|not found|unauthori[sz]ed|forbidden|"
                     r"\b[45]\d\d\b|aborted|cannot|could not|unable|conflict|timed out|timeout", re.I)
R = {k: re.compile(v) for k, v in OPS.items()}
rng = random.Random(SEED)
keep, seen_n = {}, {}


def add(key, ex):
    seen_n[key] = seen_n.get(key, 0) + 1
    lst = keep.setdefault(key, [])
    if len(lst) < 15:
        lst.append(ex)
    else:
        j = rng.randrange(seen_n[key])
        if j < 15:
            lst[j] = ex


with gzip.open(r"C:\Users\joshd\Data\ai-village-mapped\computer_use_turns.jsonl.gz", "rt", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        if r["id"] in seen:
            continue
        a, o = r.get("agent_action") or "", r.get("tool_output") or ""
        if not o.strip() or len(a) > 1000 or len(o) > 1500:
            continue
        for k, rx in R.items():
            if rx.search(a):
                add(k + ("/trouble" if TROUBLE.search(o) else "/other"),
                    {"turn_id": r["id"], "op": k, "action": a, "output": o})
                break
pool = [dict(ex, stratum=key) for key in sorted(keep) for ex in keep[key]]
rng.shuffle(pool)
for i, ex in enumerate(pool):
    ex["k"] = i + 1
(OUT / "pool.json").write_text(json.dumps(pool, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print(json.dumps({"pool": len(pool), "by_stratum": {k: len(v) for k, v in sorted(keep.items())},
                  "matches_per_stratum": dict(sorted(seen_n.items()))}))
