"""P6 (simplification) and P7 (convergence), exactly as defined in RUN-PLAN.md. Chat only; no receipts."""
import gzip, json, re, statistics, datetime as dt
from collections import defaultdict
SRC = r"C:\Users\joshd\Data\ai-village-mapped\chat_messages.jsonl.gz"
rows = []
with gzip.open(SRC, "rt", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        rows.append((r["speaker"], r["timestamp"], r.get("content") or ""))
def ts(s):
    s = s if "." in s else s + ".000000"
    return dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f")
# P6
by_agent = defaultdict(lambda: defaultdict(list))
for a, t, c in rows:
    by_agent[a][t[:10]].append(len(c.split()))
p6 = []
for a, days in by_agent.items():
    d = sorted(days)
    if len(d) < 60:
        continue
    first = [w for day in d[:30] for w in days[day]]; last = [w for day in d[-30:] for w in days[day]]
    m1, m2 = statistics.median(first), statistics.median(last)
    p6.append({"agent": a, "active_days": len(d), "median_first30": m1, "median_last30": m2, "fell": m2 < m1})
fell = sum(x["fell"] for x in p6)
P6 = {"agents": len(p6), "fell": fell, "hit": fell > len(p6) / 2, "per_agent": p6}
# P7
times = [ts(t) for _, t, _ in rows]; t0, t1 = min(times), max(times); span = (t1 - t0) / 4
names = sorted({a for a, _, _ in rows}); bit = {a: 1 << i for i, a in enumerate(names)}
tok = re.compile(r"[a-z0-9']+")
spans = [dict() for _ in range(4)]; agents_in = [set() for _ in range(4)]
for (a, t, c), tt in zip(rows, times):
    q = min(3, int((tt - t0) / span)); agents_in[q].add(a)
    w = tok.findall(c.lower()); d = spans[q]; b = bit[a]
    for i in range(len(w) - 2):
        k = w[i] + " " + w[i + 1] + " " + w[i + 2]
        d[k] = d.get(k, 0) | b
P7 = {"timeline": [str(t0), str(t1)], "spans": []}
for q in range(4):
    d = spans[q]; shared = sum(1 for v in d.values() if bin(v).count("1") >= 3)
    P7["spans"].append({"span": q + 1, "agents": len(agents_in[q]), "distinct_trigrams": len(d), "shared_by_3plus": shared,
                        "share": round(shared / len(d), 5) if d else None})
P7["hit"] = P7["spans"][3]["share"] > P7["spans"][0]["share"]
json.dump({"P6": P6, "P7": P7, "computed_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
          open(r"C:\Users\joshd\Data\results\p6_p7.json", "w", encoding="utf-8"), indent=1)
print("P6/P7 computed and saved (sealed until G1 is scored).")
