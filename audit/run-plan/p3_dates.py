"""P3 release dates, by the RUN-PLAN rule: the date in the model string where present, else the village join date."""
import json, re
a = json.load(open(r"C:\Users\joshd\Data\ai-village-mapped\agents_index.json", encoding="utf-8"))
rows = []
for k, v in a.items():
    ms = str(v.get("model_string") or ""); name = v["name"]
    if ms.startswith("tinker://"):
        continue
    m = re.search(r"(20\d\d)-?(\d\d)-?(\d\d)", ms)
    if m:
        date, how = f"{m.group(1)}-{m.group(2)}-{m.group(3)}", "model string"
    elif re.search(r"grok-4-(\d\d)(\d\d)$", ms):
        g = re.search(r"grok-4-(\d\d)(\d\d)$", ms); date, how = f"2025-{g.group(1)}-{g.group(2)}", "model string (MMDD, 2025)"
    else:
        date, how = (v.get("created_at") or "")[:10], "village join date (stand-in)"
    rows.append({"agent": name, "model_string": ms, "date": date, "source": how})
rows.sort(key=lambda r: (r["date"], r["agent"]))
for i, r in enumerate(rows):
    r["rank"] = i + 1; r["third"] = "oldest" if i < 15 else ("newest" if i >= len(rows) - 15 else "middle")
json.dump(rows, open(r"C:\Users\joshd\Data\results\p3_dates.json", "w", encoding="utf-8"), indent=1)
for r in rows: print(r["rank"], r["third"], r["date"], r["source"][:12], r["agent"])
