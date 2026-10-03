"""Gate G2: the sealed tool's claim extraction on the 200 hand-labelled messages (pass 1 = primary labels)."""
import gzip, json, sys, datetime
sys.path.insert(0, r"C:\Users\joshd\Workbench\swarm-receipts")
from receipts_core import extract_claims
from receipts_io import _raw_rows, _field, load_field_map, source_path
D = r"C:\Users\joshd\Data\ai-village-mapped"
def nocase(s): return "".join(c.lower() if "A" <= c <= "Z" else c for c in s)
names = set()
with gzip.open(D + r"\computer_use_sessions.jsonl.gz", "rt", encoding="utf-8") as f:
    for line in f:
        a = json.loads(line).get("agent")
        if isinstance(a, str) and a.strip(): names.add(nocase(a.strip()))
lookup = lambda n: nocase(str(n)) in names
sample = json.load(open(r"C:\Users\joshd\Data\g2_sample.json", encoding="utf-8"))
labels = json.load(open(r"C:\Users\joshd\Data\g2_labels.pass1.json", encoding="utf-8"))
lab = {x["id"]: x["claim"] for x in labels["labels"]}
ids = [x["id"] for x in sample]; want = set(ids)
fm = load_field_map()["chat_messages"]; path = source_path(D, "chat_messages")
pred = {}
for ln, row in _raw_rows(path):
    if row.get("id") in want:
        m = {k: _field(row, v) for k, v in fm.items()}; m.update(source=path.name, row_id=f"{path.name}:{ln}")
        cl = extract_claims(m, agent_lookup=lookup)
        pred[row["id"]] = {"tool": 1 if cl else 0, "n_claims": len(cl), "phrases": [c.matched_phrase[:80] for c in cl], "row_id": m["row_id"]}
missing = [i for i in ids if i not in pred]
tp = sum(1 for i in ids if i in pred and pred[i]["tool"] and lab[i]); fp = sum(1 for i in ids if i in pred and pred[i]["tool"] and not lab[i])
fn = sum(1 for i in ids if i in pred and not pred[i]["tool"] and lab[i]); tn = sum(1 for i in ids if i in pred and not pred[i]["tool"] and not lab[i])
res = {"run_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "labels": "g2_labels.pass1.json",
       "tool_commit": "a75ff0d", "found": len(pred), "missing_ids": missing, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
       "precision": round(tp / (tp + fp), 4) if tp + fp else None, "recall": round(tp / (tp + fn), 4) if tp + fn else None,
       "items": [{"i": k, "id": i, "label": lab[i], **pred.get(i, {})} for k, i in enumerate(ids)]}
json.dump(res, open(r"C:\Users\joshd\Data\g2_results.pass1.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in res.items() if k != "items"}))
