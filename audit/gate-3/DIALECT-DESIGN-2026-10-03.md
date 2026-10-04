# The dialect test: can a local model hear the agents' completion claims?

Designed by Claude, 3 Oct 2026, about 21:25 UTC, and sealed with the gate 3 bundle before any message was sent to a model. At Joshua's yes ("Yes, tonight").

## Why
On 200 random AI Village agent chat messages, the rule-based extractor in swarm-receipts (unchanged since v1, commit a75ff0d) finds only 23 to 27% of the completion claims, with precision 86 to 90%. The misses are the village's own dialect: status headlines, milestone shouts, jargon, and other languages. A checker that hears a quarter of the claims is silent on the rest. This test asks whether a local language model, given the labellers' own rule, hears far more.

## Data and labels (all existing, none new)
- Messages: `C:\Users\joshd\Data\g2_sample.json` (200 messages).
- Labels: `g2_labels.pass1.json` (Claude, 97 claims), `g2_labels.pass2.json` (Claude Sonnet, blind to pass 1; 107 claims); 90% agreement, Cohen's kappa 0.80 (`g2_reliability.json`).
- **Primary truth: the consensus**, the 180 messages where both labellings agree (92 claims, 88 not). Both single labellings are reported too.
- **Baseline:** the rule extractor's per-message answers (`g2_results.pass1.json`). Against the consensus: precision 0.893, recall 0.272 (25 found, 3 false, 67 missed).

## Method (`C:\Users\joshd\Data\dialect\spot_claims.py`, fingerprint in the bundle manifest)
- One message at a time, as the labellers worked. Each message passes through swarm-receipts' redaction (`receipts_io.safe_value`) and is capped at 12,000 characters.
- **The system prompt is the labellers' rule, word for word** (LABELLER-PROMPTS.md section 1), plus the "anywhere" clause and the reply format. It was not tuned on any message in the sample. Two invented messages were used only to check the mechanics.
- Reply: JSON with reason, then quote, then label (1 or 0). Temperature 0, top_k 1, seed 20261003, all penalties off, thinking off.
- **Fail-closed:** a 1 counts only if its quote appears verbatim in the message the model saw. Raw labels are reported too.
- **Models:** qwen3.5:9b (primary) and gemma4:12b (secondary), run after both gate 3 runs, one at a time.

## Measures
- Precision, recall and F1 of the verified labels against the consensus (primary), and against each labelling.
- 95% Wilson intervals for recall and precision.
- **McNemar's exact test** on the 92 consensus claims: claims the model found and the rules missed, against the reverse. "Significantly more claims heard" means two-sided p < 0.05 with more model-only finds.

## Predictions, sealed before the run

**Joshua:** none yet. Asked for one, he replied "What have I guessed so far". His standing assertion, sealed 1 Oct in Bitcoin block 969421, is about this mechanism, not this number: "Converting a multi-modal transport layer of data into a Binary outcome will lead to behavior where language can modify binary outcomes."

**Jev** (the same three runs as the gate 3 predictions):
- qwen3.5:9b recall against the consensus: below 0.40, 0.50; above 0.80, 0.28; 0.40 to 0.60, 0.11; 0.60 to 0.80, 0.11.
- Higher F1: within 0.05 of each other, 0.89; qwen, 0.09; gemma, 0.02.

**Claude:**
1. qwen3.5:9b verified recall against the consensus: point estimate 0.75. P(at least 0.50) = 0.85.
2. qwen3.5:9b verified precision against the consensus at least 0.80: 0.55.
3. qwen3.5:9b hears significantly more claims than the rules (McNemar, p < 0.05): 0.90.
4. qwen3.5:9b F1 beats the rules' F1 against the consensus: 0.90.
5. F1, gemma4:12b against qwen3.5:9b: within 0.05, 0.50; qwen higher by more than 0.05, 0.25; gemma higher by more than 0.05, 0.25.
6. Fewer than 5% of the model's raw 1s fail quote verification: 0.70.

## If the model doesn't hear more
That is published as it stands. The fix would then be the other route: agents reporting status in a checkable format.
