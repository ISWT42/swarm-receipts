"""Independent checks for ambiguous natural-chat completion wording."""

import unittest
import tempfile
from pathlib import Path

from receipts_core import extract_claims
from tests.test_receipts import ROOT, CLAIM_TIME, make_turn, read_claims, run_cli, write_records


def claims_for(text):
    return extract_claims({
        "agent": "Aster", "time": "2026-09-02T12:00:00Z",
        "text": text, "source": "chat_messages.jsonl.gz",
        "row_id": "chat_messages.jsonl.gz:1",
    })


class RoundOneBoundaryReviewTests(unittest.TestCase):
    def test_current_states_and_named_done_closers_are_claims(self):
        examples = (
            "The Planet dashboard is now live.",
            "Our Planet endpoint is up now.",
            "The Planet parser is fixed now.",
            "The Planet notice is sent now.",
            "The Planet migration is done now.",
            "All done: the Planet migration.",
            "Done — the Planet export.",
        )
        for text in examples:
            with self.subTest(text=text):
                found = claims_for(text)
                self.assertEqual(len(found), 1, found)
                self.assertIn("planet", found[0].keywords)
                self.assertTrue(found[0].matched_phrase)

    def test_state_in_a_conditional_does_not_assert_completion(self):
        examples = (
            "When the Planet dashboard is live, I can review it.",
            "Unless the Planet migration is done, hold the release.",
            "Provided the Planet parser is fixed, we can proceed.",
            "The Planet migration is done if the final upload succeeds.",
            "The Planet dashboard is live only if the upload finishes.",
            "The Planet notice is sent when the timer expires.",
        )
        for text in examples:
            with self.subTest(text=text):
                self.assertEqual(claims_for(text), [])

    def test_role_prefix_and_other_person_states_are_not_our_claims(self):
        examples = (
            "Birch: Updated the Planet config.",
            "Cedar — Done: filed the Planet receipts.",
            "Birch has the Planet dashboard live.",
            "Their Planet notice is sent now.",
            "His Planet parser is fixed now.",
            "Her Planet migration is done now.",
        )
        for text in examples:
            with self.subTest(text=text):
                self.assertEqual(claims_for(text), [])

    def test_quoted_bare_completion_and_state_are_not_our_claims(self):
        examples = (
            '"Merged the Planet branch."',
            "‘The Planet dashboard is live now.’",
            'Birch wrote:\n"Updated the Planet config.\nAll done: the Planet migration."',
            "Cedar wrote:\n'Filed the Planet receipts.\nThe Planet dashboard is live now.'",
        )
        for text in examples:
            with self.subTest(text=text):
                self.assertEqual(claims_for(text), [])

    def test_plan_and_future_states_are_not_completed_work(self):
        examples = (
            "Plan: the Planet dashboard is live by Friday.",
            "The goal is that the Planet migration is done before lunch.",
            "The Planet parser will be fixed soon.",
            "The Planet notice should be sent tomorrow.",
        )
        for text in examples:
            with self.subTest(text=text):
                self.assertEqual(claims_for(text), [])

    def test_inverted_questions_without_punctuation_are_skipped(self):
        examples = (
            "Have I posted the Planet announcement",
            "Had we completed the Planet migration",
            "Could I have merged the Planet branch",
        )
        for text in examples:
            with self.subTest(text=text):
                self.assertEqual(claims_for(text), [])

    def test_context_is_preserved_across_linked_completion_verbs(self):
        examples = (
            "If I merged the Planet branch and updated the Planet config, we could restart.",
            "I will have merged the Planet branch and updated the Planet config by tomorrow.",
            "I plan to have created the Planet page and updated the Planet dashboard.",
            "Birch merged the Planet branch and updated the Planet config.",
            "Birch: Merged the Planet branch; updated the Planet config.",
            "Cedar said: Updated the Planet config; deployed the Planet service.",
            "Have I merged the Planet branch and updated the Planet config",
        )
        for text in examples:
            with self.subTest(text=text):
                self.assertEqual(claims_for(text), [])

    def test_linked_own_completions_are_separate_claims(self):
        for text in (
            "I merged the Planet branch and updated the Planet config.",
            "Merged the Planet branch and updated the Planet config.",
        ):
            with self.subTest(text=text):
                self.assertEqual([claim.verb for claim in claims_for(text)],
                                 ["merged", "updated"])

    def test_by_can_describe_a_method_without_naming_another_agent(self):
        examples = (
            "Updated the Planet dashboard by adding icons.",
            "I fixed the Planet parser by handling empty input.",
            "Deployed the Planet service by using the local build.",
            "The Planet parser is fixed by the patch.",
            "I sent the Planet document by email.",
        )
        for text in examples:
            with self.subTest(text=text):
                self.assertEqual(len(claims_for(text)), 1)
        self.assertEqual(claims_for("The Planet parser is fixed by Cedar."), [])

    def test_done_closer_does_not_take_credit_for_another_actor(self):
        for text in ("All done: Cedar updated the Planet board.",
                     "Done: she filed the Planet receipts."):
            with self.subTest(text=text):
                self.assertEqual(claims_for(text), [])
        self.assertEqual(len(claims_for("Done: I filed the Planet receipts.")), 1)

    def test_known_participant_states_are_skipped_and_named_artifact_remains(self):
        with tempfile.TemporaryDirectory(prefix="test-participant-state-", dir=ROOT) as temporary:
            directory = Path(temporary)
            data, out = directory / "data", directory / "results"
            data.mkdir()
            write_records(data, "chat_messages", [
                {"speaker": "Aster", "timestamp": CLAIM_TIME, "room": "general", "content": text}
                for text in (
                    "Birch is done with the Planet migration.",
                    "Birch is done.",
                    "Birch is up.",
                    "birch is up.",
                    "Atlas is live.",
                )
            ])
            write_records(data, "agent_memories", [])
            write_records(data, "computer_use_sessions", [])
            write_records(data, "computer_use_turns", [
                make_turn(agent="Birch", action="Read the Planet migration", output="Loaded."),
                make_turn(action="Deploy Atlas", output="Live at https://atlas.invalid"),
            ])
            result = run_cli(data, out)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            found = read_claims(out)
            self.assertEqual(len(found), 1, found)
            self.assertEqual(found[0]["claim_text"], "Atlas is live.")
            self.assertEqual(found[0]["answer"], "shown")


if __name__ == "__main__":
    unittest.main()
