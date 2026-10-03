"""Round-two evidence context remains agent-specific and cursor-backed."""

import json
from pathlib import Path
import tempfile
import unittest

from receipts_io import TurnIndex, parse_timestamp


ROOT = Path(__file__).resolve().parents[1]
CLAIM_TIME = "2026-10-03T12:00:00Z"


class CandidateContextTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="test-round2-io-", dir=ROOT)
        self.directory = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, source, rows):
        with (self.directory / (source + ".jsonl")).open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")

    @staticmethod
    def turn(stamp, agent="Lin", session="pine"):
        return {"agent": agent, "timestamp": stamp, "session_id": session,
                "agent_action": "Click confirmation", "tool_output": "Message posted"}

    def test_goal_is_joined_for_exact_agent_and_session_only(self):
        self.write("computer_use_sessions", [
            {"session_id": "pine", "agent": "Lin", "session_goal": "Post pine review"},
            {"session_id": "pine", "agent": "Sol", "session_goal": "Post spruce review"},
            {"session_id": "foreign", "agent": "Sol", "session_goal": "Post cedar review"},
        ])
        self.write("computer_use_turns", [
            self.turn("2026-10-03T11:58:00Z"),
            self.turn("2026-10-03T11:59:00Z", session="foreign"),
            self.turn("2026-10-03T11:57:00Z", agent="Sol"),
        ])
        with TurnIndex(self.directory) as index:
            rows = list(index.candidates("Lin", CLAIM_TIME, {"pine"}))
            self.assertEqual([row["session_goal"] for row in rows], ["Post pine review", ""])
            self.assertEqual([row["agent"] for row in rows], ["Lin", "Lin"])
            self.assertTrue(all(row["within_window"] for row in rows))
            payloads = index.connection.execute("SELECT payload FROM turns").fetchall()
            self.assertTrue(all("session_goal" not in payload and "within_window" not in payload
                                for (payload,) in payloads))

    def test_window_metadata_distinguishes_old_goal_related_turns(self):
        self.write("computer_use_sessions", [
            {"session_id": "pine", "agent": "Lin", "session_goal": "Post pine review"},
        ])
        self.write("computer_use_turns", [
            self.turn("2026-10-03T10:59:59Z"),
            self.turn("2026-10-03T11:00:00Z"),
            self.turn("2026-10-03T11:59:00Z"),
            self.turn(CLAIM_TIME),
            self.turn("2026-10-03T12:00:01Z"),
        ])
        with TurnIndex(self.directory) as index:
            rows = list(index.candidates("Lin", CLAIM_TIME, {"pine"}, window_hours=1))
            self.assertEqual([row["within_window"] for row in rows], [False, True, True])
            self.assertEqual([row["row_id"] for row in rows], [
                "computer_use_turns.jsonl:1", "computer_use_turns.jsonl:2", "computer_use_turns.jsonl:3",
            ])
            self.assertTrue(all(row["session_goal"] == "Post pine review" for row in rows))
            self.assertEqual(len(list(index.candidates("Lin", CLAIM_TIME, window_hours=1))), 2)

    def test_goal_join_keeps_agent_time_index_order_without_temporary_sort(self):
        self.write("computer_use_sessions", [
            {"session_id": "pine", "agent": "Lin", "session_goal": "Post pine review"},
        ])
        self.write("computer_use_turns", [self.turn("2026-10-03T11:59:00Z")])
        with TurnIndex(self.directory) as index:
            plans = index.connection.execute("""
                EXPLAIN QUERY PLAN
                SELECT t.payload, t.stamp, s.goal FROM turns t INDEXED BY turns_agent_time
                LEFT JOIN sessions s ON s.session=t.session AND s.agent=t.agent
                WHERE t.agent=? AND t.stamp < ? AND (t.stamp >= ? OR EXISTS (
                    SELECT 1 FROM session_keywords sk
                    WHERE sk.agent=t.agent AND sk.session=t.session AND sk.keyword IN (?)
                ))
                ORDER BY t.stamp, t.sequence
            """, ("Lin", parse_timestamp(CLAIM_TIME), 0, "pine")).fetchall()
            details = " ".join(str(row[3]) for row in plans)
            self.assertIn("turns_agent_time", details)
            self.assertNotIn("TEMP B-TREE", details.upper())


if __name__ == "__main__":
    unittest.main()
