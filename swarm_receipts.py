#!/usr/bin/env python3
"""Check completion claims against streamed, offline computer-use receipts."""

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

from receipts_core import classify_claim, extract_claims
from receipts_io import TurnIndex, inspect_data, iter_source, load_field_map


ANSWERS = ("shown", "contradicted", "not shown")
CSV_FIELDS = ("claim_id", "agent", "time", "source", "claim_text", "matched_phrase",
              "answer", "deciding_line", "row_ids", "reason")


def _positive_limit(value):
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("limit must be a positive integer")
    return result


def _window(value):
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise argparse.ArgumentTypeError("window hours must be finite and greater than zero")
    return result


def _inline(value):
    return str(value).replace("\n", " ").replace("\r", " ").replace("|", "\\|")


def _examples(handle, examples):
    for answer in ANSWERS:
        handle.write("\n### " + answer + "\n\n")
        entries = examples[answer]
        if not entries:
            handle.write("No claims in this group.\n")
        for row in entries:
            handle.write("- " + _inline(row["agent"]) + ': “' + _inline(row["claim_text"]) +
                         '” (claim `' + _inline(row["source"]) + "`).\n")
            if row["deciding_line"]:
                handle.write("\n  > " + _inline(row["deciding_line"]) + "\n\n")
                handle.write("  Receipt: `" + _inline(row["row_ids"]) + "`.\n")
                if len(row["row_ids"].split(";")) > 1:
                    handle.write("  " + _inline(row["reason"]) + "\n")
            else:
                handle.write("  " + _inline(row["reason"]) + "\n")


def _write_summary(path, counts, examples, index, args):
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Claim receipts\n\n")
        handle.write("These are rule-based checks against computer-use actions and tool output. "
                     "An agent's own messages and session goals are not receipts. "
                     "Not shown means the available record does not establish an outcome.\n\n")
        handle.write("Window: " + str(args.window_hours) + " hours before each claim, plus earlier "
                     "turns in matching goal sessions for the same agent.\n\n")
        handle.write("| Agent | shown | contradicted | not shown | Total |\n")
        handle.write("| --- | ---: | ---: | ---: | ---: |\n")
        totals = Counter()
        for agent in sorted(counts):
            values = [counts[agent][answer] for answer in ANSWERS]
            totals.update(counts[agent])
            handle.write("| " + _inline(agent) + " | " + " | ".join(map(str, values)) +
                         " | " + str(sum(values)) + " |\n")
        handle.write("| Total | " + " | ".join(str(totals[answer]) for answer in ANSWERS) +
                     " | " + str(sum(totals.values())) + " |\n")
        _examples(handle, examples)
        handle.write("\n## Input notes\n\n")
        handle.write("Indexed records: `" + _inline(json.dumps(index.counts, sort_keys=True)) + "`.\n")
        if args.limit is not None:
            handle.write("This is a limited run: at most " + str(args.limit) + " physical rows per input file.\n")
        diagnostics = index.diagnostics
        if diagnostics:
            handle.write("Diagnostics: `" + _inline(json.dumps(diagnostics, sort_keys=True)) + "`.\n")
        handle.write("\n## Doubts considered and dismissed\n\n")
        handle.write("- A claim or matching session goal could sound convincing. Neither establishes an outcome; "
                     "a tied tool receipt is required. A false positive on a narration-only test would refute this.\n")
        handle.write("- The available inputs may omit the outcome. Such claims stay not shown; "
                     "a later dataset receipt could change their answers.\n")


def run(args):
    data_dir = Path(args.data)
    if not data_dir.is_dir():
        raise ValueError("data directory does not exist: " + str(data_dir))
    field_map = load_field_map(args.field_map)
    if args.inspect:
        inspect_data(data_dir, field_map, limit=args.limit, stream=sys.stdout)
        return 0
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    if data_dir.resolve() == out_dir.resolve():
        raise ValueError("output directory must differ from the input directory")
    counts = defaultdict(Counter)
    examples = {answer: [] for answer in ANSWERS}
    memory_counts = Counter()
    memory_examples = {answer: [] for answer in ANSWERS}
    total = 0
    with TurnIndex(data_dir, field_map, work_dir=out_dir, limit=args.limit) as index:
        index.build()
        with (out_dir / "claims.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
            writer.writeheader()
            for source in ("chat_messages", "agent_memories"):
                for source_row in iter_source(data_dir, source, field_map, limit=args.limit):
                    for claim in extract_claims(source_row, agent_lookup=index.is_agent):
                        candidates = index.candidates(claim.agent, claim.time, claim.keywords, args.window_hours)
                        decision = classify_claim(claim, candidates)
                        row = {
                            "claim_id": claim.claim_id, "agent": claim.agent,
                            "time": claim.time if claim.time is not None else "",
                            "source": claim.row_id, "claim_text": claim.text[:300],
                            "matched_phrase": claim.matched_phrase, "answer": decision.answer,
                            "deciding_line": decision.deciding_line,
                            "row_ids": ";".join(decision.row_ids), "reason": decision.reason,
                        }
                        writer.writerow(row)
                        counts[claim.agent][decision.answer] += 1
                        total += 1
                        if len(examples[decision.answer]) < 3:
                            examples[decision.answer].append(row)
                        if source == "agent_memories":
                            memory_counts[decision.answer] += 1
                            if len(memory_examples[decision.answer]) < 3:
                                memory_examples[decision.answer].append(row)
        _write_summary(out_dir / "summary.md", counts, examples, index, args)
        with (out_dir / "memory_check.md").open("w", encoding="utf-8") as handle:
            handle.write("# Memory claim receipts\n\n")
            handle.write("Memory claims use the same rules and computer-use receipts as chat claims. "
                         "A memory itself is not evidence for another claim.\n\n")
            for answer in ANSWERS:
                handle.write("- " + answer + ": " + str(memory_counts[answer]) + "\n")
            _examples(handle, memory_examples)
            handle.write("\n## Doubts considered and dismissed\n\n")
            handle.write("- A memory can accurately recall an unrecorded action. The checker cannot prove that; "
                         "an additional matching tool receipt would change a not shown answer.\n")
    print("Checked " + str(total) + " claims. " + ", ".join(
        answer + "=" + str(sum(counter[answer] for counter in counts.values())) for answer in ANSWERS))
    print("Wrote " + str(out_dir / "claims.csv") + ", " + str(out_dir / "summary.md") +
          ", " + str(out_dir / "memory_check.md"))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="fixtures", help="directory containing JSON Lines inputs")
    parser.add_argument("--out", default="results", help="directory for the three reports")
    parser.add_argument("--field-map", help="JSON logical-field overrides; see field_map.json")
    parser.add_argument("--window-hours", type=_window, default=24.0, help="hours before each claim (default 24)")
    parser.add_argument("--limit", type=_positive_limit, help="scan at most N physical rows per input file")
    parser.add_argument("--inspect", action="store_true", help="print input keys and three truncated sample rows")
    args = parser.parse_args(argv)
    try:
        return run(args)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print("swarm-receipts: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
