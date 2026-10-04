"""Make analyse_sample.py from the sealed analyse_real.py (audit/run-plan, 3 Oct) by exact replacements only, each asserted
to happen once, so the difference between the two is exactly what AGENT-RUN-PLAN-2026-10-04.md allows:
the inputs (the sample's shards), the output paths, and P5's census estimate from a sample."""
from pathlib import Path

SRC = Path(r"C:\Users\joshd\Workbench\swarm-receipts-public\audit\run-plan\analyse_real.py")
OUT = Path(__file__).resolve().parent / "analyse_sample.py"
s = SRC.read_text(encoding="utf-8")
EDITS = [
    ('"""P1-P5, P8, P9 from the real run, exactly as RUN-PLAN.md defines them. Writes results/real_results.json."""',
     '"""P1-P5, P8, P9 from the first agent run\'s sample (4 Oct 2026), made from the sealed analyse_real.py by\n'
     'make_analyse_sample.py: only the inputs, the output paths and P5\'s census estimate differ."""'),
    ('RUN = r"C:\\Users\\joshd\\Data\\run-real"', 'RUN = r"C:\\Users\\joshd\\Data\\agent-run\\analysis"'),
    ('json.dump(out, open(r"C:\\Users\\joshd\\Data\\results\\real_results.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)',
     'json.dump(out, open(r"C:\\Users\\joshd\\Data\\agent-run\\sample_results.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)'),
    ('json.dump(p5_rows, open(r"C:\\Users\\joshd\\Data\\results\\p5_rows.json", "w", encoding="utf-8"), indent=1)',
     'json.dump(p5_rows, open(r"C:\\Users\\joshd\\Data\\agent-run\\p5_rows.json", "w", encoding="utf-8"), indent=1)'),
    ('out["P5"] = {"contradicted_chat_claims": len(contra), "qualifying_sealed_all_text": p5_all, "qualifying_visible_only": p5_vis,\n'
     '             "hit": p5_all >= 10}',
     '# The sample version (the plan\'s only change to P5): the census count is estimated from the sample.\n'
     'UNIVERSE = sum(1 for _ in open(r"C:\\Users\\joshd\\Private\\claims\\2026-10-04-agent-run\\universe-chat.tsv", encoding="utf-8"))\n'
     'ci5 = wilson(p5_all, len(chat))\n'
     'out["P5"] = {"contradicted_chat_claims": len(contra), "qualifying_sealed_all_text": p5_all, "qualifying_visible_only": p5_vis,\n'
     '             "sampled_chat_claims": len(chat), "chat_claim_universe": UNIVERSE,\n'
     '             "estimated_census_count": round(p5_all / len(chat) * UNIVERSE, 1) if chat else None,\n'
     '             "estimated_census_ci95": [round(x * UNIVERSE, 1) for x in ci5] if ci5 else None,\n'
     '             "hit": bool(chat) and p5_all / len(chat) * UNIVERSE >= 10}'),
]
for old, new in EDITS:
    assert s.count(old) == 1, "expected exactly one: " + old[:70]
    s = s.replace(old, new)
OUT.write_text(s, encoding="utf-8")
print("wrote", OUT, "with", len(EDITS), "replacements")
