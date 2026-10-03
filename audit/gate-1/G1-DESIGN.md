# G1 design: the planted-fault gate for the AI Village audit

Written by Claude (the audit's designer), 3 Oct 2026, before any planted claim was run. The gate itself is sealed in the capsule (doi:10.5281/zenodo.23117476 record; capsule fingerprint c8b53813…, stamped 08:57:22Z). This file fixes the details the capsule left open. It is fingerprinted and stamped with OpenTimestamps before the run, together with the generator script and the truth file.

## What the capsule fixed
- 50 contradicted claims, each with a matching failure turn; 50 shown claims, each with a matching success turn; 50 claims with no matching turn.
- Each claim goes to an agent at a real timestamp. Seed 20261003.
- **Pass:** at least 90% correct in each group, and no planted contradicted claim called shown.
- **If it fails,** that result is published and nothing else.

## What this file fixes
1. **The record side is the full real record.** All 2,510,487 real computer-use turns and 78,362 real sessions are copied unchanged. Then 100 planted turns and 100 planted sessions are appended, one of each per shown or contradicted case.
2. **The claim side holds only the 150 planted claims.** Each claim is checked independently, so adding the real chat would not change any planted claim's answer; it would only add run time.
3. **The instrument** is the unmodified command-line tool, `swarm_receipts.py` at commit a75ff0d. It runs on that copy with the default 24-hour window and builds its own index from the files.
4. **Agents and timestamps:** a uniform random sample of 150 real agent chat messages, from agents with at least 1,000 real computer-use turns. Each planted claim takes the message's agent and exact timestamp, so real turns from that agent sit in the same window as the planted ones. This is the realistic noise.
5. **Groups:** the 150 sampled messages are shuffled and split, 50 each into contradicted, shown and none.
6. **Six operations.** Each claim uses the operation's own verb from the tool's documented list: push (pushed), merge (merged), deploy (deployed), post (posted), send (sent) and fix (fixed). Each case draws its operation uniformly.
7. **Two claim frames per operation**, written once and used for all three groups. Each case draws a frame uniformly. Some frames carry common words such as "main", "GitHub", "site" or "tests", the way real claims do.
8. **Receipts copy real turns.** Each planted turn's output is a real tool output from the AI Village data for the same operation and outcome, with only the object's names replaced. I read each source turn to confirm its outcome. The source turn ids are listed in the generator. One exception is adapted and marked as such: the failure body for "post" is a real rate-limit body from a comment API, used under an article API call.
9. **Objects:** each case names a unique object made of two invented words, for example "word1-word2". Before use, every invented word is checked to be absent from all real turns and sessions.
10. **Timing:** each planted turn is placed between 2 and 600 minutes (uniform, in whole minutes) before its claim, inside a planted session whose goal is "Continue today's work."
11. **Scoring:**
    - A planted claim's answer is the tool's answer for the first claim it extracts from that message.
    - If the tool extracts no claim from a planted message, that counts as a wrong answer.
    - Correct means: contradicted for the contradicted group, shown for the shown group, and not shown for the none group.
12. **Also reported** (not part of pass or fail):
    - accuracy by operation and by frame;
    - whether each deciding row is the planted turn or a real one;
    - every wrong answer, with its deciding line.

## What G1 does and doesn't show
In Joshua's words (3 Oct 2026): "The Sonny Test sets minimum requirements for considering a check’s verdict as evidence. Passing those requirements does not establish that the check covers every task requirement or failure mode."

- G1 tests whether the tool answers correctly when a claim it extracts has a matching receipt in a realistic record.
- It does not test how well the tool spots claims; that is G2 (precision 0.90, recall 0.27 on the primary labels).
- It does not test operations outside these six.
- I wrote the claim frames after reading the tool's code. That is a known risk of bias, so the frames are recorded here, before the run, along with per-frame results.
