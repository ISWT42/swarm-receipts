"""Parallel runner for swarm-receipts v2 (same code as run_parallel.py; only the tool path differs): the tool's own functions, many processes, one prebuilt index.

Usage:
  run_parallel.py check  --data DIR --index FILE --out DIR --source chat_messages|agent_memories --workers N [--select FILE]
  run_parallel.py extract --data DIR --index FILE --out DIR --source agent_memories --workers N     (claim ids only)
Each worker takes rows whose line number % N == worker id. Output columns 1-10 are exactly the CLI's claims.csv
columns, computed with the CLI's expressions; 'linked' and 'row_line' are extra.
"""
import argparse
import csv
import json
import multiprocessing as mp
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, r"C:\Users\joshd\Workbench\swarm-receipts-v2")
from receipts_core import classify_claim, extract_claims  # noqa: E402
from receipts_io import TurnIndex, iter_source, load_field_map, parse_timestamp  # noqa: E402

CSV_FIELDS = ("claim_id", "agent", "time", "source", "claim_text", "matched_phrase",
              "answer", "deciding_line", "row_ids", "reason")
EXTRA = ("linked", "row_line")


def open_index(data, index_path):
    idx = TurnIndex.__new__(TurnIndex)
    idx.data_dir, idx.field_map, idx.limit = Path(data), load_field_map(), None
    idx.path = Path(index_path)
    idx.connection = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
    idx.connection.execute("PRAGMA temp_store=FILE")
    idx.connection.execute("PRAGMA cache_size=-4096")
    idx.counts, idx.diagnostics = {}, []
    idx._built, idx._closed = True, False
    return idx


def linked(idx, agent, claim_time, hours=24.0):
    identity = idx._identifier(agent)
    stamp = parse_timestamp(claim_time)
    if identity is None or stamp is None:
        return 0
    row = idx.connection.execute(
        "SELECT 1 FROM turns INDEXED BY turns_agent_time WHERE agent=? AND stamp>=? AND stamp<? LIMIT 1",
        (identity, stamp - hours * 3600, stamp)).fetchone()
    return 1 if row else 0


def line_of(row_id):
    return int(str(row_id).rsplit(":", 1)[1])


def worker(args, wid, select):
    idx = open_index(args.data, args.index)
    fm = load_field_map()
    out = Path(args.out) / "shards"
    out.mkdir(parents=True, exist_ok=True)
    log = open(out / f"{args.mode}-{args.source}-{wid:02d}.log", "w", encoding="utf-8")
    n = done = 0
    t0 = time.time()
    if args.mode == "extract":
        with open(out / f"extract-{args.source}-{wid:02d}.txt", "w", encoding="utf-8", newline="\n") as fh:
            for row in iter_source(args.data, args.source, fm):
                if line_of(row["row_id"]) % args.workers != wid:
                    continue
                for claim in extract_claims(row, agent_lookup=idx.is_agent):
                    fh.write(claim.claim_id + "\n")
                    n += 1
        log.write(f"extracted {n} in {time.time() - t0:.0f}s\n")
        return
    with open(out / f"check-{args.source}-{wid:02d}.csv", "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS + EXTRA, lineterminator="\n")
        writer.writeheader()
        for row in iter_source(args.data, args.source, fm):
            ln = line_of(row["row_id"])
            if ln % args.workers != wid:
                continue
            for claim in extract_claims(row, agent_lookup=idx.is_agent):
                if select is not None and claim.claim_id not in select:
                    continue
                candidates = idx.candidates(claim.agent, claim.time, claim.keywords, args.window_hours)
                decision = classify_claim(claim, candidates)
                writer.writerow({
                    "claim_id": claim.claim_id, "agent": claim.agent,
                    "time": claim.time if claim.time is not None else "",
                    "source": claim.row_id, "claim_text": claim.text[:300],
                    "matched_phrase": claim.matched_phrase, "answer": decision.answer,
                    "deciding_line": decision.deciding_line,
                    "row_ids": ";".join(decision.row_ids), "reason": decision.reason,
                    "linked": linked(idx, claim.agent, claim.time, args.window_hours), "row_line": ln,
                })
                done += 1
                if done % 100 == 0:
                    fh.flush()
                    log.write(f"{done} claims, {time.time() - t0:.0f}s\n")
                    log.flush()
    log.write(f"DONE {done} claims in {time.time() - t0:.0f}s\n")
    log.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("check", "extract"))
    ap.add_argument("--data", required=True)
    ap.add_argument("--index", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--source", required=True, choices=("chat_messages", "agent_memories"))
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--select")
    ap.add_argument("--window-hours", type=float, default=24.0)
    args = ap.parse_args()
    select = None
    if args.select:
        select = set(Path(args.select).read_text(encoding="utf-8").split())
    procs = [mp.Process(target=worker, args=(args, w, select)) for w in range(args.workers)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    bad = [p.exitcode for p in procs if p.exitcode != 0]
    print(json.dumps({"mode": args.mode, "source": args.source, "workers": args.workers, "failed_workers": bad}))


if __name__ == "__main__":
    main()
