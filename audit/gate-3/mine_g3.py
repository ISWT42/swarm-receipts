"""G3 pool: random real (action, output) turns per operation, never seen by the designer or used in an earlier gate.

Gate 3's copy of Data/g1v2/mine_fresh.py (gate 2). Changes versus gate 2, and only these: the seed (20261004), the
output folder (Data/g3), and the exclusion list: every real turn id that appears anywhere in gate 1's and gate 2's
pools, label inputs, planted rows or truth files, collected programmatically from Data/g1 and Data/g1v2.
Per operation, a reservoir sample (seed 20261004) of up to 15 turns whose output matches a broad trouble pattern
and up to 15 turns whose output does not; the independent labellers decide the real outcome. Prints counts only.
"""
import gzip
import hashlib
import json
import random
import re
from pathlib import Path

SEED = 20261004
OUT = Path(r"C:\Users\joshd\Data\g3")
G1 = Path(r"C:\Users\joshd\Data\g1")
G2 = Path(r"C:\Users\joshd\Data\g1v2")
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def strings_in(x):
    """Every string in a parsed JSON value, dict keys included."""
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from strings_in(k)
            yield from strings_in(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings_in(v)


# Exclusion list, method 1 (by field): the two gate-1 files that gate 2 already excluded, gate 2's whole pool
# (240 turns, which includes the 100 turns that became planted sources) and the source turns in gate 2's truth file.
by_field = set()
for f in ("real_outcomes.json", "real_receipts.json"):
    for lst in json.load(open(G1 / f, encoding="utf-8"))["examples"].values():
        by_field.update(e["id"] for e in lst)
by_field.update(e["turn_id"] for e in json.load(open(G2 / "pool.json", encoding="utf-8")))
by_field.update(c["source_turn"] for c in json.load(open(G2 / "truth.json", encoding="utf-8"))["cases"]
                if "source_turn" in c)
# Exclusion list, method 2 (by scan): any uuid-shaped text anywhere in any top-level json file of gates 1 and 2
# (pools, label inputs and outputs, planted rows, truth files, result files). Ids that are not turns match nothing.
anywhere, scanned = set(), []
for folder in (G1, G2):
    for p in sorted(folder.glob("*.json")):
        scanned.append(folder.name + "/" + p.name)
        for s in strings_in(json.load(open(p, encoding="utf-8"))):
            anywhere.update(u.lower() for u in UUID.findall(s))
seen = by_field | anywhere
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
hit = set()  # excluded ids that really are turns in the record


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
            hit.add(r["id"])
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
assert not {ex["turn_id"] for ex in pool} & seen  # no earlier turn can be in the pool
print(json.dumps({"pool": len(pool), "by_stratum": {k: len(v) for k, v in sorted(keep.items())},
                  "matches_per_stratum": dict(sorted(seen_n.items())),
                  "excluded_earlier_turns": len(hit), "excluded_by_field": len(hit & by_field),
                  "excluded_by_scan": len(hit & anywhere),
                  "excluded_ids_sha256": hashlib.sha256("\n".join(sorted(hit)).encode("utf-8")).hexdigest(),
                  "scanned_json_files": scanned}))
