"""Fresh varied chat claims: measure extraction before scoring classification."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from generate_round1_fixture import build
from receipts_core import classify_claim, extract_claims
from tests.test_receipts import ANSWERS, ROOT, read_claims, run_cli


DATA = ROOT / "fixtures" / "round1"


class Round1FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="test-round1-", dir=ROOT)
        cls.out = Path(cls.temporary.name) / "results"
        result = run_cli(DATA, cls.out)
        if result.returncode:
            cls.temporary.cleanup()
            raise AssertionError("Round 1 fixture CLI failed:\n" + result.stdout + result.stderr)
        cls.claims = read_claims(cls.out)
        cls.truth = json.loads((DATA / "truth.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_extraction_recall_and_confusion_table(self):
        planted = {case["row_id"]: case for case in self.truth["claims"]}
        actual = {}
        for claim in self.claims:
            self.assertIn(claim["source"], planted, "An excluded statement became a claim: " + claim["claim_text"])
            self.assertNotIn(claim["source"], actual, "One planted claim was extracted twice")
            actual[claim["source"]] = claim
        found = len(set(actual) & set(planted))
        print("\nRound 1 extraction recall: {}/{} ({:.1%})".format(found, len(planted), found / len(planted)))
        table = {expected: {answer: 0 for answer in ANSWERS} for expected in ANSWERS}
        for row_id, case in planted.items():
            if row_id in actual:
                table[case["answer"]][actual[row_id]["answer"]] += 1
        print("Round 1 confusion table (rows = planted truth; columns = tool answer; extracted claims only)")
        print("{:<15} {:>8} {:>13} {:>11}".format("truth", *ANSWERS))
        for expected in ANSWERS:
            print("{:<15} {:>8} {:>13} {:>11}".format(expected, *(table[expected][answer] for answer in ANSWERS)))
        missing = [case["claim_text"] for row_id, case in planted.items() if row_id not in actual]
        self.assertEqual(found, len(planted), "Missed planted claims: " + repr(missing))
        for expected in ANSWERS:
            self.assertEqual(table[expected][expected], self.truth["counts"][expected], table)
        self.assertEqual(table["contradicted"]["shown"], 0, "A planted failure was called shown")

    def test_deciding_receipts_identify_the_planted_turn(self):
        planted = {case["row_id"]: case for case in self.truth["claims"]}
        for claim in self.claims:
            self.assertIn(claim["source"], planted)
            case = planted[claim["source"]]
            self.assertTrue(claim["matched_phrase"])
            if case["answer"] == "not shown":
                self.assertEqual(claim["deciding_line"], "")
                self.assertEqual(claim["row_ids"], "")
            else:
                self.assertTrue(claim["deciding_line"])
                self.assertIn(case["deciding_row_id"], claim["row_ids"].split(";"))

    def test_fixture_regeneration_is_deterministic(self):
        regenerated = Path(self.temporary.name) / "regenerated"
        manifest = build(regenerated)
        self.assertEqual(manifest["counts"], {answer: 10 for answer in ANSWERS})
        for path in regenerated.iterdir():
            original_hash = hashlib.sha256((DATA / path.name).read_bytes()).hexdigest()
            regenerated_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(original_hash, regenerated_hash, path.name)


class Round1SignalsRegressionTests(unittest.TestCase):
    def decide(self, claim_text, action, output):
        claims = extract_claims({
            "agent": "Aster", "time": "2026-09-01T12:00:00Z",
            "text": claim_text, "source": "chat_messages.jsonl.gz",
            "row_id": "chat_messages.jsonl.gz:1",
        })
        self.assertEqual(len(claims), 1, claim_text)
        return classify_claim(claims[0], [{
            "agent": "Aster", "time": "2026-09-01T11:55:00Z",
            "action": action, "output": output,
            "row_id": "computer_use_turns.jsonl.gz:1",
        }])

    def test_missing_required_field_is_tied_to_the_requested_action(self):
        decision = self.decide("I sent the citron notice.", "Send the citron notice", "Missing required field")
        self.assertEqual(decision.answer, "contradicted")
        self.assertEqual(decision.deciding_line, "Missing required field")

    def test_requested_http_failures_in_plain_http_and_nested_outputs(self):
        for status in (401, 403, 404, 409, 422, 429, 500, 501, 502, 503, 504, 599):
            for output in (str(status), "HTTP/1.1 " + str(status), {"result": {"status_code": status}}):
                with self.subTest(status=status, output=output):
                    decision = self.decide("Uploaded the bronze packet.", "Upload the bronze packet", output)
                    self.assertEqual(decision.answer, "contradicted")
                    self.assertIn(str(status), decision.deciding_line)
                    self.assertEqual(decision.row_ids, ("computer_use_turns.jsonl.gz:1",))
        for output in ("403 Forbidden", "503 Service Unavailable", "429 Too Many Requests"):
            with self.subTest(output=output):
                self.assertEqual(self.decide("Uploaded the bronze packet.", "Upload the bronze packet", output).answer,
                                 "contradicted")

    def test_requested_failure_phrases_with_a_matching_task(self):
        for phrase in ("rolled back", "reverted", "not completed", "missing required field", "timed out", "denied"):
            output = "monsoon portal " + phrase
            with self.subTest(phrase=phrase):
                decision = self.decide("Launched the monsoon portal.", "Deploy the monsoon portal", output)
                self.assertEqual(decision.answer, "contradicted")
                self.assertEqual(decision.deciding_line, output)

    def test_git_reference_updates_show_push_but_do_not_show_merge_or_deploy(self):
        for output in ("2f34ab1..8acde90  nightjar -> nightjar", "* [new branch]      nightjar -> nightjar"):
            with self.subTest(output=output):
                pushed = self.decide("Pushed nightjar.", "git push origin nightjar", output)
                self.assertEqual(pushed.answer, "shown")
                self.assertEqual(pushed.deciding_line, output)
                for claim in ("Merged nightjar.", "Nightjar is live now."):
                    self.assertEqual(self.decide(claim, "git push origin nightjar", output).answer, "not shown")

    def test_draft_saved_with_success_status_never_proves_delivery(self):
        cases = (
            ("Send the snowberry notice", "Draft saved for snowberry notice: HTTP 201 Created"),
            ("Send the snowberry notice", {"status": 201, "message": "Draft saved for snowberry notice."}),
            ("Save draft for snowberry notice", "HTTP 201 Created"),
            ("Save draft for snowberry notice then show the Send button", "Saved successfully: snowberry notice."),
        )
        for action, output in cases:
            with self.subTest(action=action, output=output):
                decision = self.decide("Emailed the snowberry notice.", action, output)
                self.assertEqual(decision.answer, "not shown")
                self.assertEqual(decision.deciding_line, "")

    def test_requested_success_signals_need_matching_mutating_actions(self):
        cases = (
            ("Posted the albatross notice.", "Post the albatross notice", "Message posted"),
            ("The mimosa portal is live.", "Deploy the mimosa portal", "Live at https://example.invalid/mimosa/portal"),
            ("Launched the vermilion portal.", "Deploy the vermilion portal", "200 OK"),
        )
        for claim, action, output in cases:
            with self.subTest(claim=claim, output=output):
                self.assertEqual(self.decide(claim, action, output).answer, "shown")
                self.assertEqual(self.decide(claim, "Read " + action, output).answer, "not shown")

    def test_row_counts_and_negated_receipts_do_not_become_successes(self):
        self.assertEqual(self.decide("Uploaded the bronze packet.", "Upload the bronze packet",
                                    "422 rows exported for bronze packet").answer, "not shown")
        self.assertNotEqual(self.decide("Posted the raven notice.", "Post the raven notice",
                                      "No raven notice posted").answer, "shown")
