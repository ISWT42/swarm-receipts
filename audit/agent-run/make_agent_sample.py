"""The first agent run's sample, as AGENT-RUN-PLAN-2026-10-04.md fixes it (sealed 05:14:40 UTC, 4 Oct 2026).
  python make_agent_sample.py universe              every claim v3's extract_claims finds, chat and memories
  python make_agent_sample.py draw HEIGHT HASH      seed = first 16 hex digits of the confirming block's hash
  python make_agent_sample.py prepare               after the run: sampled claims only, with 'linked' and 'row_line'
Writes ids, line numbers, agent names and times only; record text stays in the run folder, never printed."""
import csv
import gzip
import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\joshd\Workbench\swarm-receipts-v3")
from receipts_core import extract_claims  # noqa: E402
from receipts_io import iter_source, load_field_map, parse_timestamp  # noqa: E402
from swarm_receipts import PrebuiltIndex  # noqa: E402

csv.field_size_limit(10 ** 9)
HERE = Path(__file__).resolve().parent
MAPPED = Path(r"C:\Users\joshd\Data\ai-village-mapped")
INDEX = Path(r"C:\Users\joshd\Data\village-index-v3\turn-index.sqlite")
RUN = Path(r"C:\Users\joshd\Data\agent-run")
SOURCES = {"chat": "chat_messages.jsonl.gz", "memory": "agent_memories.jsonl.gz"}
SIZES = {"chat": 100, "memory": 30}


def universe():
    idx = PrebuiltIndex(MAPPED, INDEX, load_field_map())
    for kind, fname in SOURCES.items():
        n = 0
        with open(HERE / f"universe-{kind}.tsv", "w", encoding="utf-8", newline="") as f:
            for row in iter_source(MAPPED, fname.split(".")[0], load_field_map()):
                for claim in extract_claims(row, agent_lookup=idx.is_agent):
                    line = int(claim.row_id.rsplit(":", 1)[1])
                    f.write(f"{claim.claim_id}\t{line}\t{claim.agent}\t{claim.time if claim.time is not None else ''}\n")
                    n += 1
        print(kind, "claims:", n, flush=True)
    idx.close()


def read_universe(kind):
    rows = {}
    for line in (HERE / f"universe-{kind}.tsv").read_text(encoding="utf-8").splitlines():
        cid, ln, agent, t = line.split("\t")
        rows[cid] = {"line": int(ln), "agent": agent, "time": t}
    return rows


def draw(height, block_hash):
    seed = int(block_hash.lstrip("0")[:16], 16)  # correction 4 Oct: skip the proof-of-work zeros (CORRECTION-SEED-2026-10-04.md)
    rng = random.Random(seed)
    picks = {}
    for kind in ("chat", "memory"):  # chat first, then memory, from one generator, as the plan says
        picks[kind] = rng.sample(sorted(read_universe(kind)), SIZES[kind])
    (RUN / "data").mkdir(parents=True, exist_ok=True)
    maps = {}
    for kind, fname in SOURCES.items():
        u = read_universe(kind)
        want = sorted({u[c]["line"] for c in picks[kind]})
        wanted, got = set(want), {}
        with gzip.open(MAPPED / fname, "rt", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if i in wanted:
                    got[i] = line if line.endswith("\n") else line + "\n"
                    if len(got) == len(wanted):
                        break
        with gzip.open(RUN / "data" / fname, "wt", encoding="utf-8") as out:
            for ln in want:
                out.write(got[ln])
        maps[kind] = {str(sub): orig for sub, orig in enumerate(want, 1)}
    sample = {"block_height": height, "block_hash": block_hash, "seed": seed,
              "seed_rule": "first 16 hex digits after the leading zeros (correction 4 Oct)", "sizes": SIZES,
              "chat": picks["chat"], "memory": picks["memory"], "line_maps": maps}
    (HERE / "SAMPLE.json").write_text(json.dumps(sample, indent=1), encoding="utf-8")
    for p in [HERE / "SAMPLE.json", HERE / "universe-chat.tsv", HERE / "universe-memory.tsv",
              RUN / "data" / SOURCES["chat"], RUN / "data" / SOURCES["memory"]]:
        print(hashlib.sha256(p.read_bytes()).hexdigest(), p)
    print("seed", seed, "| rows in the run folder:", {k: len(v) for k, v in maps.items()})


def linked(idx, agent, claim_time, hours=24.0):
    # the 3 Oct runner's own query (run_parallel_v2.py)
    identity = idx._identifier(agent)
    stamp = parse_timestamp(claim_time)
    if identity is None or stamp is None:
        return 0
    row = idx.connection.execute(
        "SELECT 1 FROM turns INDEXED BY turns_agent_time WHERE agent=? AND stamp>=? AND stamp<? LIMIT 1",
        (identity, stamp - hours * 3600, stamp)).fetchone()
    return 1 if row else 0


def prepare():
    s = json.loads((HERE / "SAMPLE.json").read_text(encoding="utf-8"))
    idx = PrebuiltIndex(MAPPED, INDEX, load_field_map())
    fields = ("claim_id", "agent", "time", "source", "claim_text", "matched_phrase",
              "answer", "deciding_line", "row_ids", "reason", "linked", "row_line")
    rows = list(csv.DictReader(open(RUN / "out" / "claims.csv", encoding="utf-8", newline="")))
    for kind, fname, sub in (("chat", SOURCES["chat"], "chat"), ("memory", SOURCES["memory"], "mem")):
        lmap, wanted, kept = s["line_maps"][kind], set(s[kind]), []
        for r in rows:
            if not r["claim_id"].startswith(fname):
                continue
            head, _, tail = r["claim_id"].partition("#")
            orig_line = lmap[head.rsplit(":", 1)[1]]
            orig_id = f"{fname}:{orig_line}" + (f"#{tail}" if tail else "")
            if orig_id in wanted:
                kept.append({**r, "claim_id": orig_id, "source": f"{fname}:{orig_line}",
                             "linked": linked(idx, r["agent"], r["time"]), "row_line": orig_line})
        missing = wanted - {r["claim_id"] for r in kept}
        d = RUN / "analysis" / sub / "shards"
        d.mkdir(parents=True, exist_ok=True)
        with open(d / f"check-{fname.split('.')[0]}-0.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            w.writeheader()
            w.writerows(kept)
        print(kind, "sampled:", len(wanted), "found in the run:", len(kept), "missing:", sorted(missing))
    idx.close()


if __name__ == "__main__":
    {"universe": lambda: universe(), "draw": lambda: draw(int(sys.argv[2]), sys.argv[3]),
     "prepare": lambda: prepare()}[sys.argv[1]]()
