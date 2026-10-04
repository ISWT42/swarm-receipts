"""FINAL-RESULTS.json for the public repo: counts and rates only, from the sealed analysis output (sample_results.json),
with the same key names as INTERIM-CHAT-RESULTS.json and prediction scoring (threshold, hit) removed."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
src = json.load(open(HERE / "final-2026-10-04" / "sample_results.json", encoding="utf-8"))
def strip(v):
    if isinstance(v, dict): return {k: strip(x) for k, x in v.items() if k not in ("hit", "threshold")}
    if isinstance(v, list): return [strip(x) for x in v]
    return v
keys = [("chat_claims", "chat_claims"), ("chat_answers", "chat_answers"), ("chat_linked", "chat_linked"),
        ("chat_linked_answers", "chat_linked_answers"), ("memory_sample_claims", "memory_sample_claims"),
        ("memory_answers", "memory_answers"), ("memory_linked", "memory_linked"), ("memory_linked_answers", "memory_linked_answers"),
        ("contradicted_among_linked_chat_claims", "P1"), ("not_shown_among_all_chat_claims", "P2"),
        ("contradicted_by_agent_start_date_third", "P3"), ("contradicted_memory_vs_chat", "P4"),
        ("per_agent_chat", "per_agent_chat"), ("shown_by_claim_style", "P8"),
        ("hedging_among_unsupported_chat_claims", "P9"), ("estimated_contradictions_with_a_failure_line_in_census", "P5")]
out = {"note": ("Final results of the first agent run, 4 Oct 2026: chat and memory claims complete (the run finished at 22:33:40 UTC). "
                "Counts and rates only; prediction scoring is kept private (decided before these results existed). "
                "The private file this is derived from is fingerprinted in FINAL-SHA256.txt as sample_results.json."),
       "results": {pub: strip(src[priv]) for pub, priv in keys}}
(HERE / "final-2026-10-04" / "FINAL-RESULTS.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(out["results"]["memory_answers"]), json.dumps(out["results"]["contradicted_memory_vs_chat"]))
