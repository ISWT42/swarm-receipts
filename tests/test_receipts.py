"""Integration checks with hand-planted ground truth and adversarial records."""

import csv
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from generate_fixture import build


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "swarm_receipts.py"
ANSWERS = ("shown", "contradicted", "not shown")
CLAIM_TIME = "2026-09-01T12:00:00Z"


def run_cli(data, out, *arguments):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--data", str(data), "--out", str(out), *arguments],
        cwd=ROOT, text=True, capture_output=True, timeout=60,
    )


def read_claims(out):
    with (out / "claims.csv").open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def write_records(directory, name, rows):
    with gzip.open(directory / (name + ".jsonl.gz"), "wt", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row) + "\n")


def make_turn(action="Send the invoice email", output="Email sent successfully: invoice.",
              agent="Aster", time="2026-09-01T11:50:00Z", session="invoice-session", **extra):
    row = {"agent": agent, "timestamp": time, "session_id": session,
           "agent_action": action, "tool_output": output, "agent_messages": []}
    row.update(extra)
    return row


class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="test-fixture-", dir=ROOT)
        cls.out = Path(cls.temporary.name) / "results"
        result = run_cli(ROOT / "fixtures", cls.out)
        if result.returncode:
            cls.temporary.cleanup()
            raise AssertionError("Fixture CLI failed:\n" + result.stdout + result.stderr)
        cls.claims = read_claims(cls.out)
        cls.truth = json.loads((ROOT / "fixtures" / "truth.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_sonny_confusion_table(self):
        truth_by_row = {case["row_id"]: case["answer"] for case in self.truth["claims"]}
        actual = {}
        for claim in self.claims:
            self.assertIn(claim["source"], truth_by_row, "A plan, question, or reported statement became a claim")
            self.assertNotIn(claim["source"], actual, "Single planted claim was duplicated")
            self.assertIn(claim["answer"], ANSWERS)
            actual[claim["source"]] = claim["answer"]
        self.assertEqual(set(actual), set(truth_by_row), "A planted completion claim was missed")
        table = {expected: {answer: 0 for answer in ANSWERS} for expected in ANSWERS}
        for row_id, expected in truth_by_row.items():
            table[expected][actual[row_id]] += 1
        print("\nSonny extraction recall: " + str(len(actual)) + "/" + str(len(truth_by_row)) + " (100.0%)")
        print("\nSonny Test confusion table (rows = planted truth; columns = tool answer)")
        print("{:<15} {:>8} {:>13} {:>11}".format("truth", *ANSWERS))
        for expected in ANSWERS:
            print("{:<15} {:>8} {:>13} {:>11}".format(expected, *(table[expected][answer] for answer in ANSWERS)))
        for answer in ANSWERS:
            self.assertEqual(sum(table[answer].values()), 20)
            self.assertGreaterEqual(table[answer][answer], 18, "Fewer than 18/20 correct for " + answer)
        self.assertEqual(table["contradicted"]["shown"], 0, "A planted failure was called shown")

    def test_receipts_reference_real_tool_outputs(self):
        outputs = {}
        planted = {case["row_id"]: case for case in self.truth["claims"]}
        with gzip.open(ROOT / "fixtures" / "computer_use_turns.jsonl.gz", "rt", encoding="utf-8") as source:
            for number, line in enumerate(source, 1):
                row = json.loads(line)
                output = row["tool_output"]
                outputs["computer_use_turns.jsonl.gz:" + str(number)] = (
                    output if isinstance(output, str) else json.dumps(output, ensure_ascii=False, sort_keys=True)
                )
        for claim in self.claims:
            self.assertTrue(claim["matched_phrase"], "Extracted claim has no transparent matched phrase")
            if claim["answer"] == "not shown":
                self.assertFalse(claim["deciding_line"])
                continue
            self.assertTrue(claim["deciding_line"])
            row_ids = claim["row_ids"].split(";")
            self.assertTrue(row_ids)
            self.assertTrue(all(row_id in outputs for row_id in row_ids))
            self.assertIn(planted[claim["source"]]["deciding_row_id"], row_ids,
                          "Receipt must identify the planted outcome, not a tempting distractor")
            # A displayed receipt must be a verbatim line or value from an actual tool output.
            self.assertTrue(any(claim["deciding_line"] in outputs[row_id] for row_id in row_ids), claim)

    def test_outputs_include_summary_and_memory_check(self):
        self.assertTrue((self.out / "summary.md").is_file())
        self.assertTrue((self.out / "memory_check.md").is_file())
        summary = (self.out / "summary.md").read_text(encoding="utf-8")
        for agent in ("Aster", "Birch", "Cedar"):
            self.assertIn(agent, summary)
        for answer in ANSWERS:
            self.assertIn(answer, summary)
        self.assertIn("computer_use_turns.jsonl.gz:", summary)

    def test_inspect_reports_layout_and_keys(self):
        result = run_cli(ROOT / "fixtures", self.out, "--inspect")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("chat_messages.jsonl.gz", "agent_memories.jsonl.gz", "computer_use_turns.jsonl.gz"):
            self.assertIn(name, result.stdout)
        for key in ("speaker", "content", "agent_action", "tool_output"):
            self.assertIn(key, result.stdout)

    def test_limit_caps_rows_per_input(self):
        out = Path(self.temporary.name) / "limited"
        result = run_cli(ROOT / "fixtures", out, "--limit", "3")
        self.assertEqual(result.returncode, 0, result.stderr)
        claims = read_claims(out)
        self.assertEqual(len(claims), 6)
        self.assertEqual(sum(row["source"].startswith("chat_messages") for row in claims), 3)
        self.assertEqual(sum(row["source"].startswith("agent_memories") for row in claims), 3)
        self.assertTrue(all(int(row["source"].rsplit(":", 1)[1]) <= 3 for row in claims))

    def test_fixture_regeneration_is_deterministic(self):
        regenerated = Path(self.temporary.name) / "regenerated"
        manifest = build(regenerated)
        self.assertEqual(manifest["counts"], {answer: 20 for answer in ANSWERS})
        self.assertEqual(manifest["record_counts"]["computer_use_turns"], 360)
        for name in [path.name for path in regenerated.iterdir()]:
            original_hash = hashlib.sha256((ROOT / "fixtures" / name).read_bytes()).hexdigest()
            regenerated_hash = hashlib.sha256((regenerated / name).read_bytes()).hexdigest()
            self.assertEqual(original_hash, regenerated_hash, name)


class AdversarialTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="test-adversarial-", dir=ROOT)
        self.directory = Path(self.temporary.name)
        self.data = self.directory / "data"
        self.data.mkdir()
        self.out = self.directory / "results"

    def tearDown(self):
        self.temporary.cleanup()

    def classify(self, turns=(), claim="I sent the invoice email.", sessions=(), *arguments):
        write_records(self.data, "chat_messages", [{"speaker": "Aster", "timestamp": CLAIM_TIME, "content": claim, "room": "general"}])
        write_records(self.data, "agent_memories", [])
        write_records(self.data, "computer_use_turns", turns)
        write_records(self.data, "computer_use_sessions", sessions)
        result = run_cli(self.data, self.out, *arguments)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return read_claims(self.out)

    def assert_answer(self, expected, turns=(), **kwargs):
        claims = self.classify(turns, **kwargs)
        self.assertEqual(len(claims), 1, claims)
        self.assertEqual(claims[0]["answer"], expected, claims[0])
        return claims[0]

    def test_absence_is_not_shown(self):
        row = self.assert_answer("not shown")
        self.assertFalse(row["deciding_line"])
        self.assertFalse(row["row_ids"])

    def test_turn_agent_messages_are_not_evidence(self):
        self.assert_answer("not shown", [make_turn(output="Operation pending.", agent_messages=["Email sent successfully: invoice."])])

    def test_screenshot_metadata_is_not_evidence(self):
        self.assert_answer("not shown", [make_turn(output="Operation pending.", screenshot_metadata={"caption": "Email sent successfully: invoice."})])

    def test_other_agents_success_does_not_count(self):
        self.assert_answer("not shown", [make_turn(agent="Birch")])

    def test_future_success_does_not_count_even_with_matching_session(self):
        sessions = [{"agent": "Aster", "session_id": "invoice-session", "session_goal": "Send the invoice email"}]
        self.assert_answer("not shown", [make_turn(time="2026-09-01T12:10:00Z")], sessions=sessions)

    def test_same_target_read_success_does_not_prove_send(self):
        self.assert_answer("not shown", [make_turn(action="Read the invoice email", output="HTTP 200 OK. Invoice email loaded.")])

    def test_same_target_unrelated_failure_does_not_contradict_send(self):
        self.assert_answer("not shown", [make_turn(action="Read the invoice email", output="HTTP 404 Not Found: invoice email preview.")])

    def test_other_target_success_does_not_count(self):
        self.assert_answer("not shown", [make_turn(action="Send the payroll email", output="Email sent successfully: payroll.")])

    def test_other_target_failure_does_not_count(self):
        self.assert_answer("not shown", [make_turn(action="Send the payroll email", output="Send failed for payroll: permission denied.")])

    def test_specific_failure_overrides_successful_read(self):
        turns = [make_turn(action="Read the invoice email", output="HTTP 200 OK. Invoice email loaded."),
                 make_turn(output="Send failed for invoice: permission denied.", time="2026-09-01T11:55:00Z")]
        row = self.assert_answer("contradicted", turns)
        self.assertIn("permission denied", row["deciding_line"])
        self.assertIn("computer_use_turns.jsonl.gz:2", row["row_ids"])

    def test_failed_send_then_confirmed_retry_is_shown(self):
        turns = [make_turn(output="Send failed for invoice: permission denied.", time="2026-09-01T11:40:00Z"),
                 make_turn(output="Email sent successfully: invoice.")]
        row = self.assert_answer("shown", turns)
        self.assertIn("computer_use_turns.jsonl.gz:2", row["row_ids"])

    def test_quoted_agent_transcript_in_tool_output_is_not_a_receipt(self):
        self.assert_answer("not shown", [make_turn(action="cat invoice-chat.txt", output='Aster said, "I sent the invoice email."')])

    def test_nested_agent_message_in_tool_output_is_not_a_receipt(self):
        self.assert_answer("not shown", [make_turn(output={
            "agent_messages": [{"agent": "Aster", "content": "I sent the invoice email."}],
            "result": "Operation pending.",
        })])

    def test_http_get_success_is_not_evidence_of_post(self):
        self.assert_answer("not shown", [make_turn(action="curl -X GET https://example.invalid/post/invoice", output="HTTP 200 OK")],
                           claim="I posted the invoice message.")

    def test_http_post_success_proves_matching_post(self):
        self.assert_answer("shown", [make_turn(action="curl -X POST https://example.invalid/post/invoice", output="HTTP 201 Created")],
                           claim="I posted the invoice message.")

    def test_explicit_false_success_is_failure(self):
        self.assert_answer("contradicted", [make_turn(output={"success": False})])

    def test_output_success_for_other_target_does_not_prove_request_target(self):
        self.assert_answer("not shown", [make_turn(output="Email sent successfully: payroll.")])

    def test_output_failure_for_other_target_does_not_contradict_request_target(self):
        self.assert_answer("not shown", [make_turn(output="Send failed for payroll: permission denied.")])

    def test_target_in_unrelated_output_line_does_not_link_success(self):
        self.assert_answer("not shown", [make_turn(action="Send the payroll email",
                                                   output="Loaded invoice email preview.\nEmail sent successfully: payroll.")])

    def test_receipt_for_wrong_recipient_does_not_prove_send(self):
        self.assert_answer("not shown", [make_turn(action="Send the invoice to Bob", output="Invoice sent successfully to Bob.")],
                           claim="I sent the invoice to Alice.")

    def test_structured_echo_command_does_not_prove_send(self):
        self.assert_answer("not shown", [make_turn(action={"command": "echo Email sent successfully invoice"},
                                                   output="Email sent successfully invoice")])

    def test_structured_read_command_does_not_prove_send(self):
        self.assert_answer("not shown", [make_turn(action={"command": "Read invoice send status"}, output="HTTP 200 OK")])

    def test_failure_for_other_operation_does_not_override_success(self):
        self.assert_answer("shown", [make_turn(output="Email sent successfully: invoice.\nArchiving failed for payroll: permission denied.")])

    def test_single_quoted_other_agent_speech_is_skipped(self):
        self.assertEqual(self.classify([make_turn()], "Birch: 'I sent the invoice email.'"), [])

    def test_reported_quote_containing_multiple_sentences_is_skipped(self):
        for claim in ('Birch said, "I sent the invoice email. I deployed the payroll service."',
                      "Birch said, 'I sent the invoice email. I deployed the payroll service.'"):
            with self.subTest(claim=claim):
                self.assertEqual(self.classify([make_turn()], claim), [])

    def test_first_person_contraction_is_a_claim(self):
        self.assert_answer("shown", [make_turn()], claim="I've sent the invoice email.")

    def test_success_then_failed_resend_is_ambiguous(self):
        turns = [make_turn(output="Email sent successfully: invoice.", time="2026-09-01T11:40:00Z"),
                 make_turn(output="Send failed for invoice: permission denied.")]
        self.assert_answer("not shown", turns)

    def test_failure_then_pending_retry_stays_contradicted(self):
        turns = [make_turn(output="Send failed for invoice: permission denied.", time="2026-09-01T11:40:00Z"),
                 make_turn(output="Operation queued; outcome pending.")]
        self.assert_answer("contradicted", turns)

    def test_zero_or_no_errors_do_not_negate_success(self):
        for output in ("Email sent successfully: invoice. 0 errors.", "Email sent successfully: invoice. No errors."):
            with self.subTest(output=output):
                self.assert_answer("shown", [make_turn(output=output)])

    def test_structured_http_status_success_and_failure(self):
        for status, expected in ((201, "shown"), (403, "contradicted")):
            with self.subTest(status=status):
                row = self.assert_answer(expected, [make_turn(output={"status": status})])
                self.assertIn(str(status), row["deciding_line"])
                self.assertIn("computer_use_turns.jsonl.gz:1", row["row_ids"])

    def test_http_get_request_line_does_not_prove_post(self):
        self.assert_answer("not shown", [make_turn(action="HTTP GET /post/invoice", output="HTTP 200 OK")],
                           claim="I posted the invoice message.")

    def test_string_http_status_receipt_is_literal(self):
        output = {"status": "201"}
        row = self.assert_answer("shown", [make_turn(output=output)])
        self.assertTrue(row["deciding_line"])
        self.assertIn(row["deciding_line"], json.dumps(output))

    def test_http_failure_status_overrides_success_message_in_same_turn(self):
        row = self.assert_answer("contradicted", [make_turn(output={"status": 500, "message": "Invoice sent successfully."})])
        self.assertIn("500", row["deciding_line"])

    def test_queued_rollback_does_not_undo_completed_deployment(self):
        turns = [make_turn(action="Deploy the invoice service", output="Deployment completed successfully for invoice.", time="2026-09-01T11:40:00Z"),
                 make_turn(action="Roll back the invoice service", output="Rollback queued for invoice.")]
        row = self.assert_answer("shown", turns, claim="I deployed the invoice service.")
        self.assertIn("computer_use_turns.jsonl.gz:1", row["row_ids"])

    def test_failed_rollback_does_not_undo_completed_deployment(self):
        turns = [make_turn(action="Deploy the invoice service", output="Deployment completed successfully for invoice.", time="2026-09-01T11:40:00Z"),
                 make_turn(action="Roll back the invoice service", output="Rollback failed for invoice: permission denied.")]
        row = self.assert_answer("shown", turns, claim="I deployed the invoice service.")
        self.assertIn("computer_use_turns.jsonl.gz:1", row["row_ids"])

    def test_queued_rollback_without_original_receipt_is_not_shown(self):
        self.assert_answer("not shown", [make_turn(action="Roll back the invoice service", output="Rollback queued for invoice.")],
                           claim="I deployed the invoice service.")

    def test_successful_rollback_contradicts_completed_deployment(self):
        turns = [make_turn(action="Deploy the invoice service", output="Deployment completed successfully for invoice.", time="2026-09-01T11:40:00Z"),
                 make_turn(action="Roll back the invoice service", output="Rollback completed successfully for invoice.")]
        row = self.assert_answer("contradicted", turns, claim="I deployed the invoice service.")
        self.assertIn("computer_use_turns.jsonl.gz:2", row["row_ids"])

    def test_rollback_after_success_contradicts_deployment(self):
        turns = [make_turn(action="Deploy the invoice service", output="Deployment completed successfully for invoice.", time="2026-09-01T11:40:00Z"),
                 make_turn(action="Roll back the invoice service", output="Deployment rolled back for invoice: health check failed.")]
        self.assert_answer("contradicted", turns, claim="I deployed the invoice service.")

    def test_matching_session_goal_retrieves_older_turns(self):
        sessions = [{"agent": "Aster", "session_id": "invoice-session", "session_goal": "Send the invoice email"}]
        self.assert_answer("shown", [make_turn(time="2026-08-30T11:50:00Z")], sessions=sessions)

    def test_old_turn_without_matching_session_is_not_shown(self):
        self.assert_answer("not shown", [make_turn(time="2026-08-30T11:50:00Z")])

    def test_configurable_window_changes_available_evidence(self):
        turns = [make_turn(time="2026-09-01T10:00:00Z")]
        default = self.classify(turns)
        self.assertEqual(default[0]["answer"], "shown")
        shortened = self.classify(turns, "I sent the invoice email.", (), "--window-hours", "1")
        self.assertEqual(shortened[0]["answer"], "not shown")

    def test_plans_questions_reported_speech_and_negation_are_skipped(self):
        for claim in ("I will send the invoice email tomorrow.", "Did I send the invoice email?",
                      'Birch said, "I sent the invoice email."', "Birch sent the invoice email.",
                      "I did not send the invoice email.", "If I sent the invoice email, we could continue."):
            with self.subTest(claim=claim):
                self.assertEqual(self.classify([make_turn()], claim), [])

    def test_claim_text_cannot_supply_its_own_success_receipt(self):
        self.assert_answer("not shown", [make_turn(output="Operation pending.")],
                           claim="I sent the invoice email successfully; HTTP 200 OK.")

    def test_nested_field_map_works_for_chat_and_turns(self):
        write_records(self.data, "chat_messages", [{"data": {"author": "Aster", "body": "I sent the invoice email.", "at": CLAIM_TIME}}])
        write_records(self.data, "computer_use_turns", [{"data": {
            "actor": "Aster", "command": "Send the invoice email", "result": {"status": 201, "message": "Email sent successfully: invoice."},
            "at": "2026-09-01T11:50:00Z", "session": "invoice-session",
        }}])
        mapping = self.directory / "field-map.json"
        mapping.write_text(json.dumps({
            "chat_messages": {"agent": "data.author", "text": "data.body", "time": "data.at"},
            "computer_use_turns": {"agent": "data.actor", "action": "data.command", "output": "data.result", "time": "data.at", "session": "data.session"},
        }), encoding="utf-8")
        result = run_cli(self.data, self.out, "--field-map", str(mapping))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        claims = read_claims(self.out)
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]["answer"], "shown")
        self.assertEqual(claims[0]["source"], "chat_messages.jsonl.gz:1")

    def test_inspect_truncates_long_text(self):
        full_text = "sample " + "longtext" * 100
        write_records(self.data, "chat_messages", [{"speaker": "Aster", "content": full_text, "timestamp": CLAIM_TIME}])
        result = run_cli(self.data, self.out, "--inspect")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("sample ", result.stdout)
        self.assertNotIn(full_text, result.stdout)


if __name__ == "__main__":
    unittest.main()
