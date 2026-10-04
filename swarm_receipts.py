#!/usr/bin/env python3
"""Check completion claims against streamed, offline computer-use receipts."""

import argparse
import csv
import json
import math
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from receipts_core import classify_claim, extract_claims
from receipts_io import TurnIndex, inspect_data, iter_source, load_field_map
from receipts_model import BackendError


ANSWERS = ("shown", "contradicted", "not shown")
CSV_FIELDS = ("claim_id", "agent", "time", "source", "claim_text", "matched_phrase",
              "answer", "deciding_line", "row_ids", "reason")
# Options that only the model reader uses (v3). With the default rule reader
# they are refused rather than silently ignored.
MODEL_OPTIONS = ("backend", "model", "ollama_url", "timeout", "max_turns", "output_chars",
                 "think", "mock_script", "resume")


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


def _seconds(value):
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise argparse.ArgumentTypeError("timeout must be finite and greater than zero")
    return result


def _inline(value):
    return str(value).replace("\n", " ").replace("\r", " ").replace("|", "\\|")


class PrebuiltIndex(TurnIndex):
    """A turn index that TurnIndex.build() wrote earlier, opened read-only.

    The candidate query is TurnIndex's own. close() never deletes the file.
    """

    def __init__(self, data_dir, index_path, field_map=None):
        path = Path(index_path)
        if not path.is_file():
            raise ValueError("prebuilt index does not exist: " + str(path))
        self.data_dir = Path(data_dir)
        self.field_map = field_map or load_field_map()
        self.limit = None
        self.path = path
        self._closed = True
        self.connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        self._closed = False
        tables = {row[0] for row in self.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"turns", "sessions", "session_keywords", "participants"} <= tables:
            self.close()
            raise ValueError("not a swarm-receipts turn index: " + str(path))
        self.connection.execute("PRAGMA temp_store=FILE")
        self.connection.execute("PRAGMA cache_size=-4096")
        self.counts, self.diagnostics = {}, []
        self.built_from = None
        info = path.with_name("index-info.json")
        if info.is_file():
            try:
                details = json.loads(info.read_text(encoding="utf-8"))
                self.counts = dict(details.get("counts") or {})
                self.diagnostics = list(details.get("diagnostics") or [])[:50]
                self.built_from = details.get("data")
            except (ValueError, AttributeError, TypeError):
                pass
        if self.built_from and Path(self.built_from).resolve() != self.data_dir.resolve():
            print("swarm-receipts: warning: the prebuilt index was built from " + str(self.built_from) +
                  ", not from " + str(self.data_dir), file=sys.stderr)
        self._built = True

    def build(self):
        return self

    def close(self):
        if not self._closed:
            self.connection.close()
            self._closed = True


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


def _reader_notes(handle, info):
    handle.write("\n## Model reader\n\n")
    handle.write("Model: `" + _inline(info.get("model")) + "`, digest `" + _inline(info.get("model_digest")) +
                 "` (" + _inline(info.get("backend")) + ", Ollama " + _inline(info.get("ollama_version")) + ").\n")
    handle.write("Options: `" + _inline(json.dumps(info.get("options"), sort_keys=True)) + "`; thinking " +
                 ("on" if info.get("think") else "off") + "; timeout " + str(info.get("timeout_seconds")) +
                 " s with " + str(info.get("retries")) + " retry.\n")
    handle.write("Caps: `" + _inline(json.dumps(info.get("caps"), sort_keys=True)) + "`.\n")
    handle.write("Ranking: " + _inline(info.get("ranking_rule")) + "\n")
    handle.write("System prompt sha256: `" + _inline(info.get("system_prompt_sha256")) + "`.\n")
    handle.write("Model calls: " + str(info.get("calls")) + " (" + str(info.get("cached_calls")) + " more from the "
                 "resume cache), " + str(info.get("call_seconds")) + " s in calls.\n\n")
    handle.write("| Reader outcome | Claims |\n| --- | ---: |\n")
    for code, number in sorted((info.get("codes") or {}).items()):
        handle.write("| " + _inline(code) + " | " + str(number) + " |\n")
    handle.write("\nOnly `verified` answers can be shown or contradicted: the cited turn was shown to the model and "
                 "its quote is verbatim in that turn's output as the model saw it. Every other outcome is not shown.\n")


def _write_summary(path, counts, examples, index, args, reader_info=None):
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Claim receipts\n\n")
        if reader_info is None:
            handle.write("These are rule-based checks against computer-use actions and tool output. "
                         "An agent's own messages and session goals are not receipts. "
                         "Not shown means the available record does not establish an outcome.\n\n")
        else:
            handle.write("These are model-read checks against computer-use tool output: a local language model "
                         "read each claim's candidate turns, and every quote it gave was checked mechanically. "
                         "An agent's own messages, commands and session goals are not receipts. "
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
        if reader_info is not None:
            _reader_notes(handle, reader_info)
        handle.write("\n## Input notes\n\n")
        handle.write("Indexed records: `" + _inline(json.dumps(index.counts, sort_keys=True)) + "`.\n")
        if getattr(args, "index", None):
            handle.write("Turn index: prebuilt, opened read-only (`" + _inline(args.index) + "`" +
                         ("; built from `" + _inline(index.built_from) + "`"
                          if getattr(index, "built_from", None) else "") + ").\n")
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
        if reader_info is not None:
            handle.write("- A model can misread a real line, for example a success for another object. The checks "
                         "prove that the quoted line exists in the cited output, not that it settles the claim; "
                         "the deciding line is printed so that a reader can judge it.\n")


def _build_reader(args, out_dir, log):
    from receipts_model import (DEFAULT_MODEL, DEFAULT_URL, MockBackend, ModelReader, OllamaBackend,
                                ReaderConfig)
    defaults = ReaderConfig()
    output_chars = args.output_chars if args.output_chars is not None else defaults.output_head + defaults.output_tail
    head = output_chars // 3
    config = ReaderConfig(
        max_turns=args.max_turns if args.max_turns is not None else defaults.max_turns,
        output_head=head, output_tail=output_chars - head,
        timeout=args.timeout if args.timeout is not None else defaults.timeout,
        think=bool(args.think),
    )
    if (args.backend or "ollama") == "mock":
        backend = MockBackend(args.mock_script)
    else:
        if args.mock_script:
            raise ValueError("--mock-script needs --backend mock")
        backend = OllamaBackend(args.model or DEFAULT_MODEL, args.ollama_url or DEFAULT_URL, config)
    return ModelReader(backend, config, log=log, cache_path=out_dir / "reader_cache.jsonl", resume=bool(args.resume))


def _write_run_info(path, reader, status, started, total):
    info = reader.run_info()
    info.update(status=status, started_utc=started, claims=total,
                finished_utc=None if status == "running" else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    path.write_text(json.dumps(info, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return info


def run(args):
    data_dir = Path(args.data)
    if not data_dir.is_dir():
        raise ValueError("data directory does not exist: " + str(data_dir))
    model_reader = args.reader == "model"
    if not model_reader:
        given = [name for name in MODEL_OPTIONS if getattr(args, name, None) not in (None, False)]
        if given:
            raise ValueError("--" + given[0].replace("_", "-") + " needs --reader model")
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
    reader = None
    log = None
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        if model_reader:
            log = (out_dir / "reader_log.jsonl").open("a" if args.resume else "w", encoding="utf-8")
            reader = _build_reader(args, out_dir, log)
            _write_run_info(out_dir / "run_info.json", reader, "running", started, 0)
        if args.index:
            index_context = PrebuiltIndex(data_dir, args.index, field_map)
        else:
            index_context = TurnIndex(data_dir, field_map, work_dir=out_dir, limit=args.limit)
        with index_context as index:
            index.build()
            with (out_dir / "claims.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
                writer.writeheader()
                for source in ("chat_messages", "agent_memories"):
                    for source_row in iter_source(data_dir, source, field_map, limit=args.limit):
                        for claim in extract_claims(source_row, agent_lookup=index.is_agent):
                            candidates = index.candidates(claim.agent, claim.time, claim.keywords, args.window_hours)
                            if reader is None:
                                decision = classify_claim(claim, candidates)
                            else:
                                decision = reader.classify(claim, candidates)
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
                            if reader is not None:
                                handle.flush()
                                record = reader.last_record
                                print("[" + str(total) + "] " + claim.claim_id + ": " + decision.answer + " (" +
                                      str(record.get("code")) + ", " + str(record.get("seconds")) + " s)",
                                      file=sys.stderr, flush=True)
                            if len(examples[decision.answer]) < 3:
                                examples[decision.answer].append(row)
                            if source == "agent_memories":
                                memory_counts[decision.answer] += 1
                                if len(memory_examples[decision.answer]) < 3:
                                    memory_examples[decision.answer].append(row)
            reader_info = None
            if reader is not None:
                reader_info = _write_run_info(out_dir / "run_info.json", reader, "complete", started, total)
            _write_summary(out_dir / "summary.md", counts, examples, index, args, reader_info)
            with (out_dir / "memory_check.md").open("w", encoding="utf-8") as handle:
                handle.write("# Memory claim receipts\n\n")
                if reader_info is None:
                    handle.write("Memory claims use the same rules and computer-use receipts as chat claims. "
                                 "A memory itself is not evidence for another claim.\n\n")
                else:
                    handle.write("Memory claims use the same model reader, checks and computer-use receipts as chat "
                                 "claims (model `" + _inline(reader_info.get("model")) + "`, digest `" +
                                 _inline(reader_info.get("model_digest")) + "`). "
                                 "A memory itself is not evidence for another claim.\n\n")
                for answer in ANSWERS:
                    handle.write("- " + answer + ": " + str(memory_counts[answer]) + "\n")
                _examples(handle, memory_examples)
                handle.write("\n## Doubts considered and dismissed\n\n")
                handle.write("- A memory can accurately recall an unrecorded action. The checker cannot prove that; "
                             "an additional matching tool receipt would change a not shown answer.\n")
    except BaseException:
        if reader is not None:
            try:
                _write_run_info(out_dir / "run_info.json", reader, "stopped", started, total)
            except OSError:
                pass
        raise
    finally:
        if log is not None:
            log.close()
    print("Checked " + str(total) + " claims. " + ", ".join(
        answer + "=" + str(sum(counter[answer] for counter in counts.values())) for answer in ANSWERS))
    written = [out_dir / "claims.csv", out_dir / "summary.md", out_dir / "memory_check.md"]
    if reader is not None:
        written += [out_dir / "run_info.json", out_dir / "reader_log.jsonl"]
        print("Model " + str(reader.info.get("model")) + " (" + str(reader.info.get("model_digest")) + "): " +
              str(reader.calls) + " calls, " + str(round(reader.call_seconds, 1)) + " s in calls.")
    print("Wrote " + ", ".join(str(path) for path in written))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="fixtures", help="directory containing JSON Lines inputs")
    parser.add_argument("--out", default="results", help="directory for the three reports")
    parser.add_argument("--field-map", help="JSON logical-field overrides; see field_map.json")
    parser.add_argument("--window-hours", type=_window, default=24.0, help="hours before each claim (default 24)")
    parser.add_argument("--limit", type=_positive_limit, help="scan at most N physical rows per input file")
    parser.add_argument("--inspect", action="store_true", help="print input keys and three truncated sample rows")
    parser.add_argument("--index", help="reuse a turn index built earlier by TurnIndex.build(), opened read-only "
                                        "(--limit then applies to claim sources only)")
    reading = parser.add_argument_group("reader (v3)")
    reading.add_argument("--reader", choices=("rule", "model"), default="rule",
                         help="rule: v2's rule reader (default); model: a local model reads, quotes are verified")
    reading.add_argument("--backend", choices=("ollama", "mock"), help="model backend (default ollama)")
    reading.add_argument("--model", help="Ollama model name (default qwen3.5:9b)")
    reading.add_argument("--ollama-url", help="local Ollama server (default http://localhost:11434)")
    reading.add_argument("--timeout", type=_seconds, help="seconds per model call, retried once (default 300)")
    reading.add_argument("--max-turns", type=_positive_limit, help="candidate turns shown per claim (default 6)")
    reading.add_argument("--output-chars", type=_positive_limit,
                         help="characters kept from a long output: a third from the head, the rest from the tail "
                              "(default 1500)")
    reading.add_argument("--think", action="store_true", help="let a thinking model think (default off)")
    reading.add_argument("--mock-script", help="JSON replies for the mock backend (tests)")
    reading.add_argument("--resume", action="store_true",
                         help="reuse model replies cached in the output directory by an interrupted run")
    args = parser.parse_args(argv)
    try:
        return run(args)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print("swarm-receipts: " + str(error), file=sys.stderr)
        return 2
    except BackendError as error:
        print("swarm-receipts: " + str(error), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
