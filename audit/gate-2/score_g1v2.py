"""Score gate G1-prime as G1V2-DESIGN.md says (same scoring as G1), from the v2 command line's claims.csv."""
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

G = Path(r"C:\Users\joshd\Data\g1v2")
REAL_TURNS = 2510487
csv.field_size_limit(10 ** 9)
truth = json.load(open(G / "truth.json", encoding="utf-8"))
cases = truth["cases"]
first = {}
for r in csv.DictReader(open(G / "out" / "claims.csv", encoding="utf-8", newline="")):
    line = int(r["source"].rsplit(":", 1)[1])
    if "#" not in r["claim_id"] and line not in first:
        first[line] = r


def origin(row_ids):
    return ["planted" if int(x.rsplit(":", 1)[1]) > REAL_TURNS else "real" for x in filter(None, row_ids.split(";"))]


res = []
for c in cases:
    r = first.get(c["line"])
    ans = r["answer"] if r else "no claim extracted"
    res.append({"case": c["case"], "group": c["group"], "expected": c["expected"], "family": c["family"],
                "agent": c["agent"], "claim": c["claim"], "source_turn": c.get("source_turn"),
                "answer": ans, "correct": ans == c["expected"], "deciding_rows": origin(r["row_ids"]) if r else [],
                "deciding_line": r["deciding_line"] if r else "", "reason": r["reason"] if r else ""})
groups = defaultdict(Counter)
for x in res:
    groups[x["group"]]["n"] += 1
    groups[x["group"]]["correct"] += x["correct"]
    groups[x["group"]]["answer:" + x["answer"]] += 1
need = {g: math.ceil(0.9 * groups[g]["n"]) for g in groups}
contra_shown = sum(1 for x in res if x["group"] == "contradicted" and x["answer"] == "shown")
passed = all(groups[g]["correct"] >= need[g] for g in ("contradicted", "shown", "none")) and contra_shown == 0
fam = defaultdict(Counter)
for x in res:
    fam[(x["family"], x["group"])]["n"] += 1
    fam[(x["family"], x["group"])]["correct"] += x["correct"]
summary = {"pass": passed, "groups": {g: dict(groups[g]) for g in ("contradicted", "shown", "none")},
           "needed": need, "contradicted_called_shown": contra_shown,
           "extracted": sum(1 for x in res if x["answer"] != "no claim extracted"),
           "by_family_group": {f"{a}/{b}": f"{v['correct']}/{v['n']}" for (a, b), v in sorted(fam.items())},
           "deciding_row_origin": dict(Counter(o for x in res for o in x["deciding_rows"]))}
json.dump({"summary": summary, "cases": res}, open(G / "G1V2-RESULT.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(summary, indent=1))
print("\nWRONG ANSWERS:")
for x in res:
    if not x["correct"]:
        print(f"{x['case']} {x['group']:12s} {x['family']:7s} -> {x['answer']:18s} rows={x['deciding_rows']} | {x['claim'][:80]} | {x['deciding_line'][:90]}")
