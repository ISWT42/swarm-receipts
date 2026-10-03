"""Score gate G1 exactly as G1-DESIGN.md item 11 says, from the unmodified CLI's claims.csv."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

G1 = Path(r"C:\Users\joshd\Data\g1")
REAL_TURNS = 2510487
truth = json.load(open(G1 / "truth.json", encoding="utf-8"))
cases = truth["cases"]
rows = list(csv.DictReader(open(G1 / "out" / "claims.csv", encoding="utf-8", newline="")))
first = {}
for r in rows:
    src = r["source"]
    line = int(src.rsplit(":", 1)[1])
    if "#" not in r["claim_id"] and line not in first:
        first[line] = r


def origin(row_ids):
    out = []
    for rid in filter(None, row_ids.split(";")):
        n = int(rid.rsplit(":", 1)[1])
        out.append("planted" if n > REAL_TURNS else "real")
    return out


res = []
for c in cases:
    r = first.get(c["line"])
    ans = r["answer"] if r else "no claim extracted"
    res.append({**{k: c[k] for k in ("case", "group", "expected", "op", "frame", "agent", "claim")},
                "template": c.get("template"), "minutes_before": c.get("minutes_before"),
                "answer": ans, "correct": ans == c["expected"],
                "deciding_rows": origin(r["row_ids"]) if r else [], "deciding_line": r["deciding_line"] if r else "",
                "reason": r["reason"] if r else ""})
by_group = defaultdict(Counter)
for x in res:
    by_group[x["group"]]["n"] += 1
    by_group[x["group"]]["correct"] += x["correct"]
    by_group[x["group"]]["answer:" + x["answer"]] += 1
contra_called_shown = sum(1 for x in res if x["group"] == "contradicted" and x["answer"] == "shown")
passed = all(by_group[g]["correct"] >= 45 for g in ("contradicted", "shown", "none")) and contra_called_shown == 0
by_op = defaultdict(Counter)
by_frame = defaultdict(Counter)
for x in res:
    by_op[(x["op"], x["group"])]["n"] += 1
    by_op[(x["op"], x["group"])]["correct"] += x["correct"]
    by_frame[(x["op"], x["frame"])]["n"] += 1
    by_frame[(x["op"], x["frame"])]["correct"] += x["correct"]
summary = {
    "pass": passed,
    "groups": {g: dict(by_group[g]) for g in ("contradicted", "shown", "none")},
    "contradicted_called_shown": contra_called_shown,
    "extracted": sum(1 for x in res if x["answer"] != "no claim extracted"),
    "by_op_group": {f"{k[0]}/{k[1]}": f"{v['correct']}/{v['n']}" for k, v in sorted(by_op.items())},
    "by_op_frame": {f"{k[0]}/frame{k[1]}": f"{v['correct']}/{v['n']}" for k, v in sorted(by_frame.items())},
    "deciding_row_origin": dict(Counter(o for x in res for o in x["deciding_rows"])),
}
json.dump({"summary": summary, "cases": res}, open(G1 / "G1-RESULT.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(summary, indent=1))
print("\nWRONG ANSWERS:")
for x in res:
    if not x["correct"]:
        print(f"{x['case']} {x['group']:12s} {x['op']:6s} f{x['frame']} -> {x['answer']:18s} rows={x['deciding_rows']} | {x['claim'][:70]} | {x['deciding_line'][:90]}")
