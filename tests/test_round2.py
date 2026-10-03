"""Action/goal-linked generic receipts with new claims and planted distractions."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from generate_round2_fixture import build
from receipts_core import classify_claim, extract_claims
from tests.test_receipts import ANSWERS, ROOT, read_claims, run_cli


DATA = ROOT / "fixtures" / "round2"


class Round2FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="test-round2-", dir=ROOT)
        cls.out = Path(cls.temporary.name) / "results"
        result = run_cli(DATA, cls.out)
        if result.returncode:
            cls.temporary.cleanup()
            raise AssertionError("Round 2 fixture CLI failed:\n" + result.stdout + result.stderr)
        cls.claims = read_claims(cls.out)
        cls.truth = json.loads((DATA / "truth.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_extraction_recall_and_confusion_table(self):
        planted = {case["row_id"]: case for case in self.truth["claims"]}
        actual = {}
        for claim in self.claims:
            self.assertIn(claim["source"], planted, "Excluded statement became a claim: " + claim["claim_text"])
            self.assertNotIn(claim["source"], actual, "Planted claim extracted twice")
            actual[claim["source"]] = claim
        found = len(set(actual) & set(planted))
        print("\nRound 2 extraction recall: {}/{} ({:.1%})".format(found, len(planted), found / len(planted)))
        table = {expected: {answer: 0 for answer in ANSWERS} for expected in ANSWERS}
        for row_id, case in planted.items():
            if row_id in actual:
                table[case["answer"]][actual[row_id]["answer"]] += 1
        print("Round 2 confusion table (rows = planted truth; columns = tool answer; extracted claims only)")
        print("{:<15} {:>8} {:>13} {:>11}".format("truth", *ANSWERS))
        for expected in ANSWERS:
            print("{:<15} {:>8} {:>13} {:>11}".format(expected, *(table[expected][answer] for answer in ANSWERS)))
        missing = [case["claim_text"] for row_id, case in planted.items() if row_id not in actual]
        self.assertEqual(found, len(planted), "Missed planted claims: " + repr(missing))
        for expected in ANSWERS:
            self.assertEqual(table[expected][expected], self.truth["counts"][expected], table)
        self.assertEqual(table["contradicted"]["shown"], 0, "A planted failure was called shown")

    def test_deciding_receipts_reference_planted_rows_and_conflicts_explain_both(self):
        planted = {case["row_id"]: case for case in self.truth["claims"]}
        for claim in self.claims:
            case = planted[claim["source"]]
            if case["answer"] == "not shown":
                self.assertEqual(claim["deciding_line"], "", claim)
                self.assertEqual(claim["row_ids"], "", claim)
            else:
                self.assertTrue(claim["deciding_line"], claim)
                for row_id in case["deciding_row_ids"]:
                    self.assertIn(row_id, claim["row_ids"].split(";"), claim)
                    if case["conflict"]:
                        self.assertIn(row_id, claim["reason"], claim)

    def test_fixture_regeneration_is_deterministic(self):
        regenerated = Path(self.temporary.name) / "regenerated"
        manifest = build(regenerated)
        self.assertEqual(manifest["counts"], {answer: 10 for answer in ANSWERS})
        for path in regenerated.iterdir():
            self.assertEqual(hashlib.sha256((DATA / path.name).read_bytes()).hexdigest(),
                             hashlib.sha256(path.read_bytes()).hexdigest(), path.name)


class Round2LinkingTests(unittest.TestCase):
    def decide(self, text, action, output, goal="", **extra):
        claims = extract_claims({
            "agent": "Aster", "time": "2026-09-01T12:00:00Z", "text": text,
            "source": "chat_messages.jsonl.gz", "row_id": "chat_messages.jsonl.gz:1",
        })
        self.assertEqual(len(claims), 1, text)
        turn = {"agent": "Aster", "time": "2026-09-01T11:55:00Z", "action": action,
                "output": output, "session_goal": goal, "within_window": True,
                "row_id": "computer_use_turns.jsonl.gz:1"}
        turn.update(extra)
        return classify_claim(claims[0], [turn])

    def test_anonymous_receipts_fit_each_operation(self):
        cases = (
            ("Posted the waxwing notice.", "Post the waxwing notice", "Message posted: https://example.invalid/p/74"),
            ("Posted the sedge bulletin.", "Post the sedge bulletin", "Message created: https://example.invalid/p/52"),
            ("Deployed the seafoam dashboard.", "Deploy the seafoam dashboard", "Live at https://example.invalid/d/33\nHTTP 201 Created"),
            ("The dewpond site is live.", "Deploy the dewpond site", "200 OK"),
            ("Sent the thistle agenda.", "Send the thistle agenda", "Delivered successfully."),
            ("Uploaded the gannet sketches.", "Upload the gannet sketches", "Stored."),
            ("Submitted the moorland application.", "Submit the moorland application", "Accepted."),
        )
        for text, action, output in cases:
            with self.subTest(text=text):
                self.assertEqual(self.decide(text, action, output).answer, "shown")

    def test_partial_meaningful_object_overlap_is_sufficient(self):
        self.assertEqual(self.decide("Posted the kelpwatch audit bulletin.", "Post the kelpwatch bulletin",
                                     "Message posted: https://example.invalid/p/64").answer, "shown")

    def test_goal_target_links_an_operation_that_omits_the_object(self):
        for text, action, goal, output in (
            ("Posted the milkweed notice.", "Post message", "Post the milkweed notice",
             "Message posted: https://example.invalid/p/61"),
            ("The whimbrel viewer is live.", "Deploy application", "Deploy the whimbrel viewer",
             "Live at https://example.invalid/d/48\n200 OK"),
            ("Emailed the towhee agenda.", "Send email", "Email the towhee agenda", "Delivered."),
        ):
            with self.subTest(text=text):
                self.assertEqual(self.decide(text, action, output, goal=goal).answer, "shown")

    def test_goal_does_not_replace_an_explicit_different_action_target(self):
        self.assertEqual(self.decide("Emailed the ragwort digest.", "Send the unrelated circular", "Sent.",
                                     goal="Email the ragwort digest").answer, "not shown")
        self.assertEqual(self.decide("Emailed the harrier agenda to Mira.", "Send the harrier agenda to Rowan", "Sent.",
                                     goal="Email the harrier agenda to Mira").answer, "not shown")

    def test_goal_only_link_outside_window_does_not_count(self):
        self.assertEqual(self.decide("Emailed the avocet digest.", "Send email", "Delivered.",
                                     goal="Email the avocet digest", within_window=False).answer, "not shown")

    def test_operation_mismatch_does_not_become_proof_from_generic_output(self):
        cases = (
            ("Sent the brant memo.", "Send the brant memo", "Message posted: https://example.invalid/p/26"),
            ("Deployed the plover console.", "Deploy the plover console", "Stored."),
            ("Uploaded the cormorant drawings.", "Upload the cormorant drawings", "Delivered."),
            ("Submitted the robin application.", "Submit the robin application", "Uploaded."),
        )
        for text, action, output in cases:
            with self.subTest(text=text):
                self.assertEqual(self.decide(text, action, output).answer, "not shown")

    def test_incompatible_typed_success_is_not_repaired_by_success_modifier_or_status(self):
        cases = (
            ("Sent the redpoll memo.", "Send the redpoll memo",
             "Message posted successfully: https://example.invalid/p/76"),
            ("Submitted the meadowfoam application.", "Submit the meadowfoam application", "Uploaded successfully."),
            ("Deployed the caddis portal.", "Deploy the caddis portal", "Stored successfully."),
        )
        for text, action, output in cases:
            for status in ("", "\nHTTP 201 Created"):
                with self.subTest(text=text, status=status):
                    self.assertEqual(self.decide(text, action, output + status).answer, "not shown")

    def test_neutral_ui_action_uses_goal_and_compatible_receipt(self):
        cases = (
            ("Posted the hornbeam notice.", "Post the hornbeam notice",
             "Message posted: https://example.invalid/p/89"),
            ("The lapwing portal is live.", "Deploy the lapwing portal",
             "Live at https://example.invalid/d/19\n200 OK"),
        )
        for text, goal, output in cases:
            with self.subTest(text=text):
                self.assertEqual(self.decide(text, "Click button", output, goal=goal).answer, "shown")

    def test_neutral_ui_action_mixed_failure_wins_over_compatible_success(self):
        cases = (
            ("Posted the hornbeam notice.", "Post the hornbeam notice",
             "Message posted: https://example.invalid/p/89\n403 Forbidden"),
            ("The lapwing portal is live.", "Deploy the lapwing portal",
             {"confirmation": "Live at https://example.invalid/d/19", "status": 503}),
        )
        for text, goal, output in cases:
            with self.subTest(text=text):
                result = self.decide(text, "Click button", output, goal=goal)
                self.assertEqual(result.answer, "contradicted")
                self.assertEqual(result.row_ids, ("computer_use_turns.jsonl.gz:1",))

    def test_ui_and_routing_action_shapes_link_to_goal_object(self):
        cases = (
            ("Posted the bristlecone notice.", "Post the bristlecone notice", "Clicked the publish button"),
            ("Posted the siltstone advisory.", "Post the siltstone advisory",
             {"type": "click", "coordinates": {"x": 425, "y": 318}}),
            ("Posted the rowanberry announcement.", "Post the rowanberry announcement", "Post to /channels/general"),
            ("Posted the tamarisk briefing.", "tamarisk briefing", "Click button"),
        )
        for text, goal, action in cases:
            with self.subTest(text=text, action=action):
                self.assertEqual(self.decide(text, action, "Message posted: https://example.invalid/p/97",
                                             goal=goal).answer, "shown")
        for action in ({"type": "read", "coordinates": {"x": 425, "y": 318}},
                       {"type": "echo", "text": "Message posted"},
                       {"method": "GET", "url": "https://example.invalid/p/97"}):
            with self.subTest(read_only=action):
                self.assertEqual(self.decide("Posted the bristlecone notice.", action,
                                             "Message posted: https://example.invalid/p/97",
                                             goal="Post the bristlecone notice").answer, "not shown")

    def test_explicit_different_object_is_not_a_neutral_ui_or_routing_action(self):
        self.assertEqual(self.decide("Posted the honeysuckle bulletin.", "Post the elderberry memo",
                                     "Message posted: https://example.invalid/p/97",
                                     goal="Post the honeysuckle bulletin").answer, "not shown")

    def test_push_receipt_must_name_claimed_destination_branch(self):
        for output in ("111abc2..999def8  unrelated -> unrelated",
                       "* [new branch] reedbed -> unrelated"):
            with self.subTest(output=output):
                self.assertEqual(self.decide("Pushed reedbed.", "git push origin reedbed", output).answer, "not shown")
        self.assertEqual(self.decide("Pushed reedbed.", "git push origin reedbed",
                                     "111abc2..999def8  local-work -> reedbed").answer, "shown")
        self.assertEqual(self.decide("Pushed riverbank-release.", "git push origin riverbank-release",
                                     "111abc2..999def8 riverbank-release -> riverbank-candidate").answer, "not shown")
        for branch, destination in (("topic/stonefly", "stonefly"), ("riverbank-release", "riverbank")):
            with self.subTest(branch=branch, destination=destination):
                self.assertEqual(self.decide("Pushed " + branch + ".", "git push origin " + branch,
                                             "111abc2..999def8 HEAD -> " + destination).answer, "not shown")
        self.assertEqual(self.decide("Pushed topic/stonefly.", "git push origin topic/stonefly",
                                     "111abc2..999def8 HEAD -> topic/stonefly").answer, "shown")

    def test_explicit_wrong_object_or_recipient_outweighs_matching_action(self):
        cases = (
            ("Posted the bluejay notice.", "Post the bluejay notice",
             "Message posted for unrelated kestrel: https://example.invalid/p/93"),
            ("Emailed the chaffinch agenda to Hazel.", "Send the chaffinch agenda to Hazel",
             "Delivered chaffinch agenda to Rowan."),
        )
        for text, action, output in cases:
            with self.subTest(text=text):
                self.assertEqual(self.decide(text, action, output).answer, "not shown")

    def test_mixed_failure_wins_even_when_success_url_is_generic(self):
        for output in ("Message posted: https://example.invalid/p/54\n403 Forbidden",
                       {"confirmation": "Message posted: https://example.invalid/p/54", "status": 429}):
            with self.subTest(output=output):
                answer = self.decide("Posted the rainshadow bulletin.", "Post the rainshadow bulletin", output)
                self.assertEqual(answer.answer, "contradicted")
                self.assertEqual(answer.row_ids, ("computer_use_turns.jsonl.gz:1",))

    def test_other_agents_future_and_narration_remain_ineligible(self):
        for extra in ({"agent": "Birch"}, {"time": "2026-09-01T12:01:00Z"}):
            with self.subTest(extra=extra):
                self.assertEqual(self.decide("Posted the meadowlark advisory.", "Post the meadowlark advisory",
                                             "Message posted: https://example.invalid/p/92", **extra).answer, "not shown")
        self.assertEqual(self.decide("Posted the meadowlark advisory.", "Post the meadowlark advisory",
                                     {"agent_messages": ["Message posted: https://example.invalid/p/92"]}).answer, "not shown")

    def test_draft_with_status_and_delivery_words_still_cannot_prove_send(self):
        for output in ("Draft saved: https://example.invalid/drafts/25\n201 Created",
                       {"status": 201, "state": "draft", "message": "Draft never sent."}):
            with self.subTest(output=output):
                self.assertNotEqual(self.decide("Emailed the blackthorn digest.", "Send the blackthorn digest", output).answer, "shown")

    def test_conflicting_turns_are_contradicted_with_both_rows_in_either_order(self):
        claim = extract_claims({
            "agent": "Aster", "time": "2026-09-01T12:00:00Z", "text": "Posted the fescue notice.",
            "source": "chat_messages.jsonl.gz", "row_id": "chat_messages.jsonl.gz:1",
        })[0]
        for success_first in (True, False):
            outputs = ("Message posted: https://example.invalid/p/87", "403 Forbidden")
            if not success_first:
                outputs = tuple(reversed(outputs))
            turns = [{"agent": "Aster", "time": "2026-09-01T11:" + minute + ":00Z",
                      "action": "Post the fescue notice", "output": output,
                      "within_window": True, "row_id": "computer_use_turns.jsonl.gz:" + str(index + 1)}
                     for index, (minute, output) in enumerate(zip(("45", "55"), outputs))]
            for candidates in (turns, list(reversed(turns))):
                with self.subTest(success_first=success_first, candidates=candidates):
                    result = classify_claim(claim, candidates)
                    self.assertEqual(result.answer, "contradicted")
                    self.assertEqual(set(result.row_ids), {turn["row_id"] for turn in turns})
                    for turn in turns:
                        self.assertIn(turn["row_id"], result.reason)


if __name__ == "__main__":
    unittest.main()
