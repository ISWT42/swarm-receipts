"""Resume the memory-claim universe after a job limit stopped make_agent_sample.py universe (4 Oct 2026, about 06:35 UTC).
Same extractor and index as the sealed plan says. The last memory row in the file may be partly written, so all of its claims
are dropped and that row is extracted again; rows before it are complete and kept. Prints counts only."""
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\joshd\Workbench\swarm-receipts-v3")
from receipts_core import extract_claims  # noqa: E402
from receipts_io import iter_source, load_field_map  # noqa: E402
from swarm_receipts import PrebuiltIndex  # noqa: E402

HERE = Path(__file__).resolve().parent
MAPPED = Path(r"C:\Users\joshd\Data\ai-village-mapped")
INDEX = Path(r"C:\Users\joshd\Data\village-index-v3\turn-index.sqlite")
U = HERE / "universe-memory.tsv"

lines = U.read_text(encoding="utf-8").splitlines()
last = int(lines[-1].split("\t")[1])
kept = [l for l in lines if int(l.split("\t")[1]) < last]
print("kept", len(kept), "claims from rows before", last, "| dropped", len(lines) - len(kept), "from the last row", flush=True)
idx = PrebuiltIndex(MAPPED, INDEX, load_field_map())
n = 0
with open(U, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(kept) + "\n")
    for row in iter_source(MAPPED, "agent_memories", load_field_map()):
        line = int(row["row_id"].rsplit(":", 1)[1])
        if line < last:
            continue
        for claim in extract_claims(row, agent_lookup=idx.is_agent):
            f.write(f"{claim.claim_id}\t{line}\t{claim.agent}\t{claim.time if claim.time is not None else ''}\n")
            n += 1
idx.close()
print("memory claims added", n, "| total", len(kept) + n, flush=True)
