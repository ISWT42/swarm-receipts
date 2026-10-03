"""Checks for streaming source mapping and conservative evidence indexing."""

import gzip
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from receipts_io import (
    DEFAULT_FIELD_MAP, TurnIndex, inspect_data, iter_source,
    load_field_map, meaningful_keywords, parse_timestamp,
)


ROOT = Path(__file__).resolve().parents[1]
CLAIM_TIME = "2026-09-01T12:00:00Z"


class TimestampTests(unittest.TestCase):
    def test_iso_offsets_naive_seconds_and_milliseconds_agree(self):
        expected = 1788264000.0
        for value in (CLAIM_TIME, "2026-09-01T08:00:00-04:00",
                      "2026-09-01T12:00:00", expected, int(expected),
                      expected * 1000, str(int(expected * 1000))):
            with self.subTest(value=value):
                self.assertEqual(parse_timestamp(value), expected)

    def test_malformed_timestamps_do_not_supply_temporal_evidence(self):
        for value in (None, True, {}, [], "", "unknown", "2026-99-99",
                      float("nan"), float("inf"), 10 ** 1000):
            with self.subTest(value=str(value)[:30]):
                self.assertIsNone(parse_timestamp(value))


class InputIndexTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="test-io-", dir=ROOT)
        self.directory = Path(self.temporary.name)
        self.data = self.directory / "data"
        self.out = self.directory / "out"
        self.data.mkdir()
        self.out.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, source, rows, compressed=True):
        path = self.data / (source + (".jsonl.gz" if compressed else ".jsonl"))
        opener = gzip.open if compressed else open
        with opener(path, "wt", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")
        return path

    @staticmethod
    def turn(agent="Ada", stamp="2026-09-01T11:00:00Z", session="alpha", **extra):
        row = {"agent": agent, "timestamp": stamp, "session_id": session,
               "agent_action": {"operation": "publish", "item": "alpha-brief"},
               "tool_output": {"status": 201, "message": "Published alpha-brief."}}
        row.update(extra)
        return row

    def index(self, **kwargs):
        return TurnIndex(self.data, work_dir=self.out, **kwargs)

    def test_default_map_file_matches_defaults(self):
        self.assertEqual(load_field_map(ROOT / "field_map.json"), DEFAULT_FIELD_MAP)

    def test_dotted_array_literal_and_null_field_mappings(self):
        self.write("chat_messages", [{
            "nested": {"identity": "Ada", "texts": [{"content": "I saved alpha."}]},
            "literal.time": CLAIM_TIME,
        }])
        mapping_path = self.directory / "map.json"
        mapping_path.write_text(json.dumps({"chat_messages.jsonl.gz": {
            "agent": "nested.identity", "text": "nested.texts.0.content",
            "time": "literal.time", "session": None,
        }}), encoding="utf-8")
        mapping = load_field_map(mapping_path)
        row = next(iter_source(self.data, "chat_messages", mapping))
        self.assertEqual(row["agent"], "Ada")
        self.assertEqual(row["text"], "I saved alpha.")
        self.assertEqual(row["time"], CLAIM_TIME)
        self.assertIsNone(row["session"])
        self.assertEqual(row["source"], "chat_messages.jsonl.gz")
        self.assertEqual(row["row_id"], "chat_messages.jsonl.gz:1")
        self.assertEqual(mapping["computer_use_turns"], DEFAULT_FIELD_MAP["computer_use_turns"])

    def test_invalid_field_map_is_an_explicit_error(self):
        mapping_path = self.directory / "map.json"
        for value in ([], {"unknown": {}}, {"chat_messages": {"unknown": "content"}},
                      {"chat_messages": {"text": 42}}):
            with self.subTest(value=value):
                mapping_path.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_field_map(mapping_path)

    def test_plain_fallback_and_gzip_preference(self):
        self.write("chat_messages", [{"speaker": "Plain", "content": "I saved alpha."}], False)
        row = next(iter_source(self.data, "chat_messages"))
        self.assertEqual(row["source"], "chat_messages.jsonl")
        self.write("chat_messages", [{"speaker": "Gzip", "content": "I saved beta."}])
        self.assertEqual(next(iter_source(self.data, "chat_messages"))["agent"], "Gzip")
        self.assertEqual(list(iter_source(self.data, "events")), [])

    def test_limit_counts_physical_lines_including_blank_lines(self):
        path = self.data / "chat_messages.jsonl"
        path.write_text("\n" + json.dumps({"speaker": "Ada", "content": "I saved alpha."}) +
                        "\n\n{malformed beyond the limit\n", encoding="utf-8")
        self.assertEqual(list(iter_source(self.data, "chat_messages", limit=0)), [])
        self.assertEqual(list(iter_source(self.data, "chat_messages", limit=1)), [])
        rows = list(iter_source(self.data, "chat_messages", limit=3))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["row_id"], "chat_messages.jsonl:2")
        with self.assertRaisesRegex(ValueError, "chat_messages.jsonl:4"):
            list(iter_source(self.data, "chat_messages"))

    def test_session_agent_enrichment_requires_one_owner(self):
        self.write("computer_use_sessions", [
            {"session_id": "unique", "agent": "Ada", "session_goal": "Publish alpha"},
            {"session_id": "shared", "agent": "Ada", "session_goal": "Publish alpha"},
            {"session_id": "shared", "agent": "Bert", "session_goal": "Publish alpha"},
        ])
        self.write("computer_use_turns", [
            self.turn(agent=None, session="unique"),
            self.turn(agent=None, session="shared"),
            self.turn(agent="Bert", session="unique"),
        ])
        with self.index() as index:
            rows = list(index.candidates("Ada", CLAIM_TIME, {"alpha"}))
            self.assertEqual([row["row_id"] for row in rows], ["computer_use_turns.jsonl.gz:1"])
            self.assertEqual(rows[0]["agent"], "Ada")
            self.assertEqual(index.counts["enriched_turns"], 1)
            self.assertEqual(index.counts["unassigned_turns"], 1)
            self.assertEqual(len(list(index.candidates("Bert", CLAIM_TIME, {"alpha"}))), 1)

    def test_old_matching_goal_uses_the_same_tokens_as_claims(self):
        self.write("computer_use_sessions", [
            {"session_id": "alpha", "agent": "Ada", "session_goal": "Publish alpha-brief for QA"},
            {"session_id": "foreign", "agent": "Bert", "session_goal": "Publish alpha-brief"},
        ])
        self.write("computer_use_turns", [
            self.turn(stamp="2026-08-25T11:00:00Z"),
            self.turn(agent="Bert", stamp="2026-08-25T11:00:00Z", session="foreign"),
        ])
        self.assertTrue({"alpha", "brief", "qa"} <= meaningful_keywords("Publish alpha-brief for QA"))
        with self.index() as index:
            self.assertEqual(len(list(index.candidates("Ada", CLAIM_TIME, {"alpha", "brief"}))), 1)
            self.assertEqual(len(list(index.candidates("Ada", CLAIM_TIME, {"qa"}))), 1)
            self.assertEqual(list(index.candidates("Ada", CLAIM_TIME, {"unrelated"})), [])
            self.assertEqual(list(index.candidates("Ada", CLAIM_TIME)), [])

    def test_future_equal_and_unknown_times_are_excluded_even_with_matching_goal(self):
        self.write("computer_use_sessions", [{"session_id": "alpha", "agent": "Ada", "session_goal": "Publish alpha-brief"}])
        self.write("computer_use_turns", [
            self.turn(stamp="2026-09-01T13:00:00Z"), self.turn(stamp=CLAIM_TIME),
            self.turn(stamp="bad"), self.turn(stamp=None), self.turn(),
        ])
        with self.index() as index:
            rows = list(index.candidates("Ada", CLAIM_TIME, {"alpha"}))
            self.assertEqual([row["row_id"] for row in rows], ["computer_use_turns.jsonl.gz:5"])
            self.assertEqual(index.counts["untimed_turns"], 2)
            self.assertEqual(list(index.candidates("Ada", None, {"alpha"})), [])
            self.assertEqual(list(index.candidates("Ada", "bad", {"alpha"})), [])

    def test_persisted_payload_excludes_narration_and_preserves_structures(self):
        narration = "Narration that must not become a receipt. " * 5000
        original = self.turn(agent_messages=[narration], screenshot_metadata={"caption": narration})
        self.write("computer_use_turns", [original])
        with self.index() as index:
            raw = index.connection.execute("SELECT payload FROM turns").fetchone()[0]
            self.assertNotIn("Narration", raw)
            self.assertLess(len(raw), 1000)
            row = next(index.candidates("Ada", CLAIM_TIME))
            self.assertEqual(set(row), {"agent", "time", "session", "action", "output", "source", "row_id"})
            self.assertEqual(row["action"], original["agent_action"])
            self.assertEqual(row["output"], original["tool_output"])

    def test_inspect_prints_three_rows_and_recursively_truncates_strings(self):
        full_text = "long-text " * 100
        self.write("chat_messages", [
            {"speaker": "Ada", "content": full_text, "nested": {"items": [full_text]}, "row": number}
            for number in range(4)
        ])
        stream = io.StringIO()
        report = inspect_data(self.data, stream=stream)
        item = report["chat_messages.jsonl.gz"]
        self.assertEqual(len(item["samples"]), 3)
        self.assertEqual(item["keys"], ["content", "nested", "row", "speaker"])
        self.assertEqual(len(item["samples"][0]["content"]), 200)
        self.assertEqual(len(item["samples"][0]["nested"]["items"][0]), 200)
        self.assertEqual(stream.getvalue().count("  sample "), 3)
        self.assertNotIn(full_text, stream.getvalue())

    def test_inspect_samples_three_nonblank_rows_with_a_physical_limit(self):
        path = self.data / "chat_messages.jsonl"
        path.write_text("\n" + "\n".join(json.dumps({"content": str(number)})
                                           for number in range(4)) + "\n", encoding="utf-8")
        complete = inspect_data(self.data)[path.name]["samples"]
        self.assertEqual([row["content"] for row in complete], ["0", "1", "2"])
        limited = inspect_data(self.data, limit=2)[path.name]["samples"]
        self.assertEqual([row["content"] for row in limited], ["0"])

    def test_malformed_json_error_names_physical_source_row(self):
        path = self.data / "computer_use_turns.jsonl"
        path.write_text("\n{broken\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "computer_use_turns.jsonl:2"):
            list(iter_source(self.data, "computer_use_turns"))

    def test_temp_index_is_inside_out_and_removed_on_normal_exit(self):
        self.write("computer_use_turns", [self.turn()])
        with self.index() as index:
            database = index.path
            self.assertEqual(database.parent.resolve(), self.out.resolve())
            self.assertTrue(database.exists())
        self.assertFalse(database.exists())
        self.assertEqual(list(self.out.iterdir()), [])

    def test_failed_context_entry_closes_and_removes_partial_index(self):
        path = self.data / "computer_use_turns.jsonl"
        path.write_text(json.dumps(self.turn()) + "\n{broken\n", encoding="utf-8")
        index = self.index()
        database = index.path
        with self.assertRaisesRegex(ValueError, "computer_use_turns.jsonl:2"):
            with index:
                self.fail("Malformed input reached the context body")
        self.assertFalse(database.exists())
        self.assertEqual(list(self.out.iterdir()), [])
        with self.assertRaises(sqlite3.ProgrammingError):
            index.connection.execute("SELECT 1")
        index.close()

    def test_candidate_query_streams_in_index_order_without_temp_sort(self):
        self.write("computer_use_turns", [self.turn()])
        with self.index() as index:
            plans = index.connection.execute("""
                EXPLAIN QUERY PLAN
                SELECT t.payload FROM turns t INDEXED BY turns_agent_time
                WHERE t.agent=? AND t.stamp < ? AND (t.stamp >= ? OR EXISTS (
                    SELECT 1 FROM session_keywords sk
                    WHERE sk.agent=t.agent AND sk.session=t.session AND sk.keyword IN (?, ?)
                ))
                ORDER BY t.stamp, t.sequence
            """, ("Ada", parse_timestamp(CLAIM_TIME), 0, "alpha", "brief")).fetchall()
            details = " ".join(str(row[3]) for row in plans)
            self.assertIn("turns_agent_time", details)
            self.assertNotIn("TEMP B-TREE", details.upper())


if __name__ == "__main__":
    unittest.main()
