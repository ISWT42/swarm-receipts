"""Preliminary tool successes must not establish completed external work."""

import unittest

from receipts_core import classify_claim, extract_claims


class OutcomeTests(unittest.TestCase):
    def check(self, output):
        claim = extract_claims({
            "agent": "Aster", "time": "2026-09-01T12:00:00Z",
            "text": "I sent the invoice email.", "source": "chat_messages.jsonl.gz",
            "row_id": "chat_messages.jsonl.gz:1",
        })[0]
        return classify_claim(claim, [{
            "agent": "Aster", "time": "2026-09-01T11:50:00Z",
            "action": "Send the invoice email", "output": output,
            "row_id": "computer_use_turns.jsonl.gz:1",
        }])

    def test_preparation_success_does_not_establish_delivery(self):
        for output in ("Command parsed successfully for invoice.",
                       "Authentication succeeded for invoice.",
                       "Successfully connected for invoice.",
                       "Connected to invoice: HTTP 200 OK.",
                       {"status": 200, "phase": "authenticated"}):
            with self.subTest(output=output):
                self.assertEqual(self.check(output).answer, "not shown")

    def test_accepted_asynchronous_request_is_not_complete(self):
        for output in ("HTTP 202 Accepted.", "HTTP 202 Accepted: invoice delivery queued.",
                       {"status": 201, "state": "pending"}):
            with self.subTest(output=output):
                self.assertEqual(self.check(output).answer, "not shown")

    def test_explicit_delivery_receipt_can_precede_waiting_for_a_reply(self):
        decision = self.check({"message": "Email sent successfully: invoice.",
                               "recipient_reply": "pending"})
        self.assertEqual(decision.answer, "shown")
        self.assertEqual(decision.deciding_line, "Email sent successfully: invoice.")

    def test_failure_with_a_pending_retry_still_establishes_failure(self):
        decision = self.check({"status": 403, "state": "retry pending"})
        self.assertEqual(decision.answer, "contradicted")
        self.assertIn("403", decision.deciding_line)
