#!/usr/bin/env python3
"""Reproduce the offline index-memory check, using separate Linux processes.

Run: python3 benchmark_scale.py --out results/scale_check.json
Each worker writes gzip rows incrementally, builds the index, then streams
every candidate. Its input files and SQLite database are removed afterward.
Only the standard library is used; no dataset or network access is needed.
"""

import argparse
import datetime as dt
import gzip
import json
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

from receipts_io import TurnIndex


ROOT = Path(__file__).resolve().parent
AGENT = "BenchmarkAgent"
MEMORY_CEILING_MIB = 128


def inside_repository(path):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError("Benchmark paths must stay inside the repository")
    return resolved


def worker(turn_count):
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="benchmark-scale-", dir=ROOT) as temporary:
        temporary_path = Path(temporary)
        data = temporary_path / "data"
        index_dir = temporary_path / "index"
        data.mkdir()
        index_dir.mkdir()
        first_stamp = 1_788_177_600.0
        action = {"operation": "save", "target": "alpha-brief.md"}
        output = {"status_code": 201, "message": "Saved alpha-brief.md successfully.",
                  "bytes_written": 1024}
        turns_path = data / "computer_use_turns.jsonl.gz"
        generation_started = time.perf_counter()
        with gzip.open(turns_path, "wt", encoding="utf-8", compresslevel=1) as handle:
            for number in range(turn_count):
                row = {"agent": AGENT, "timestamp": first_stamp + number / 20,
                       "session_id": "benchmark-session", "agent_action": action,
                       "tool_output": output, "agent_messages": ["I saved the note."]}
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")
        with gzip.open(data / "computer_use_sessions.jsonl.gz", "wt", encoding="utf-8") as handle:
            handle.write(json.dumps({"agent": AGENT, "session_id": "benchmark-session",
                                     "session_goal": "Save the alpha brief note"}) + "\n")
        generation_seconds = time.perf_counter() - generation_started
        index_started = time.perf_counter()
        with TurnIndex(data, work_dir=index_dir) as index:
            index_seconds = time.perf_counter() - index_started
            indexed_turns = index.counts["indexed_turns"]
            index_bytes = index.path.stat().st_size
            query_started = time.perf_counter()
            candidate_count = 0
            claim_time = first_stamp + turn_count / 20 + 1
            # All rows fall within 24 hours at the default million-row size.
            # Longer requested runs widen the window to include their first row.
            window_hours = max(24, (claim_time - first_stamp) / 3600)
            for _ in index.candidates(AGENT, claim_time, (), window_hours):
                candidate_count += 1
            query_seconds = time.perf_counter() - query_started
            counts = dict(index.counts)
        compressed_bytes = turns_path.stat().st_size
        peak_rss_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        sample_bytes = len(json.dumps(row, separators=(",", ":")).encode("utf-8"))
        action_output_bytes = len(json.dumps({"agent_action": action, "tool_output": output},
                                            separators=(",", ":")).encode("utf-8"))
    removed = not temporary_path.exists()
    return {
        "requested_turns": turn_count,
        "indexed_turns": indexed_turns,
        "streamed_candidate_turns": candidate_count,
        "peak_rss_mib": round(peak_rss_mib, 3),
        "generation_seconds": round(generation_seconds, 3),
        "index_seconds": round(index_seconds, 3),
        "candidate_stream_seconds": round(query_seconds, 3),
        "total_seconds": round(time.perf_counter() - started, 3),
        "compressed_turn_bytes": compressed_bytes,
        "sqlite_index_bytes": index_bytes,
        "representative_record_bytes": sample_bytes,
        "representative_action_output_bytes": action_output_bytes,
        "counts": counts,
        "checks": {
            "indexed_count_matches": indexed_turns == turn_count,
            "streamed_candidate_count_matches": candidate_count == turn_count,
            "peak_rss_below_128_mib": peak_rss_mib < MEMORY_CEILING_MIB,
            "temporary_data_and_index_removed": removed,
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="results/scale_check.json")
    parser.add_argument("--sizes", nargs="+", type=int, default=[100_000, 1_000_000])
    parser.add_argument("--worker", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not sys.platform.startswith("linux"):
        parser.error("This check uses Linux ru_maxrss units (KiB)")
    if args.worker is not None:
        if args.worker <= 0:
            parser.error("Turn counts must be positive")
        print(json.dumps(worker(args.worker), sort_keys=True))
        return 0
    if any(size <= 0 for size in args.sizes):
        parser.error("Turn counts must be positive")
    out = inside_repository(args.out)
    measurements = []
    for size in args.sizes:
        print(f"Measuring {size:,} streamed turns in a separate process...", flush=True)
        completed = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--worker", str(size)],
            cwd=ROOT, text=True, capture_output=True, check=True,
        )
        measurement = json.loads(completed.stdout)
        measurements.append(measurement)
        print(f"  indexed={measurement['indexed_turns']:,}; "
              f"peak RSS={measurement['peak_rss_mib']:.3f} MiB; "
              f"total={measurement['total_seconds']:.3f}s", flush=True)
    passed = all(all(row["checks"].values()) for row in measurements)
    report = {
        "measured_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "measurement": "Separate child process ru_maxrss; Linux KiB converted to MiB",
        "memory_ceiling_mib": MEMORY_CEILING_MIB,
        "passed": passed,
        "runs": measurements,
        "limits": [
            "Synthetic, ordered rows with representative structured action and output; not real AI Village data.",
            "Measures index building and one streamed query, not classification of one million claims.",
            "Peak RSS does not include kernel filesystem caches; the index uses disk space.",
        ],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Wrote " + str(out.relative_to(ROOT)), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
