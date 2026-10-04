# The first agent run: v3 with gemma4:12b on a sealed sample of real AI Village claims

Written by Claude on 4 Oct 2026, starting at 05:13 UTC (clock checked). It follows Joshua's choice, made at about 05:09 UTC: "Agents now, gate 4 after (Recommended)". When it was written:
- no real agent claim had been checked by v3;
- no agent result from any checker had been read;
- the 3 Oct v1 real-run files (`Data\run-real\shards`) stay unopened, because v1 failed its gate.

## Why now
- **Gate 3:** v3 with gemma4:12b passed. It scored 47, 45 and 49 of 50, and called no planted failure shown.
  - The result was sealed at 05:06:43 UTC (FreeTSA). The result file's SHA-256 is efff50ac…2243.
  - v3 with qwen3.5:9b failed: 49, 42 and 49.
- **The bench's rule since v1:** a checker that passes its planted-fault gate may judge agents. This run is that first use.
- **The caveats every result carries:**
  - Gemma passed at the boundary: 45 correct, where 45 were needed in the success group.
  - It was the second of two models run on the same exam.
  - Once, the sealed fail-closed rule turned a "shown" that quoted a failure line into "not shown".
  - The ground truth was labelled by Claude models.
  - Every agent result is **provisional until a fresh gate (gate 4) confirms the checker**.

## What it scores
The nine predictions sealed in Joshua's capsule on 3 Oct (`CAPSULE-AI-VILLAGE-2026-10-03.md`, Bitcoin block 969704). P8 and P9 are his by name. The definitions are those of the sealed run plan (`audit/run-plan/RUN-PLAN.md`, 3 Oct), changed only where a sample forces a change. Those changes are listed below.

## The instrument
- **The checker:** swarm-receipts v3 at commit 00956d9, frozen, run as `--reader model --model gemma4:12b` (digest 6114515d…ed0b).
- **Its options:** the same as gate 3, all defaults:
  - temperature 0, seed 20261003, top_k 1, thinking off;
  - 300 s per call with one retry;
  - at most 6 candidate turns;
  - a 24-hour window.
- **The index:** a fresh turn index of the real record only, with no planted rows.
  - It is built by v3's own code, with gate 3's `build_index.py`, from `Data\ai-village-mapped` into `Data\village-index-v3`.
  - Its counts must equal the real record's: 2,510,487 turns and 78,362 sessions.
  - If they differ, the run stops and that is reported.

## The sample (fixed now; drawn only after its seed exists)
- **The universe:**
  - every claim v3's own `extract_claims` finds in every chat message (the census of the 3 Oct plan, with v3's extractor);
  - separately, every claim it finds in every memory row.
  - Claim ids are the extractor's own (`file:line`, `#2` and up for further claims in the same row).
- **The seed:**
  - the first 16 hex digits of the hash of the Bitcoin block that confirms this plan's OpenTimestamps proof. That is the lowest block height among the proof's Bitcoin attestations when the sample is drawn.
  - The upgraded proof used is kept and fingerprinted.
  - Nobody can know the seed when this plan is sealed.
- **The draw:**
  - `random.Random(seed).sample` over the sorted chat claim ids gives **100 chat claims**;
  - then, over the sorted memory claim ids, **30 memory claims**.
- **Fingerprinted before the first model call:** the universe files, the sample and the run folder.

## How the checker sees the sample
- **The run folder** holds only the chat messages and memory rows that contain sampled claims, in their original order. A line map ties each row to its original line.
- **The run:** the checker runs unchanged on that folder with the real index. It checks every claim in those rows, and all are logged; only the sampled claims are analysed.
- **"Linked"** is computed with the 3 Oct runner's own query (`linked()` in `run_parallel_v2.py`): at least one turn by the same agent in the 24 hours before the claim.
- **The model's time:** the dialect test pauses while this run uses the model, then resumes from its saved replies.

## Analysis
`analyse_sample.py` is the sealed `analyse_real.py` with its inputs and its output path changed. The sample forces these changes:
- **P1, P2, P3, P4, P8 and P9:** the same rates on the sample, each with a Wilson 95% interval. Each hit or miss is decided on the point estimate, as the 3 Oct plan decides it, with the interval reported beside it.
  - P3 and P4 rest on very few claims per group, so they are reported as underpowered.
- **P5:**
  - The 3 Oct rule counts qualifying chat claims in the whole census, and is a hit at 10 or more.
  - On a sample, the census count is estimated: the qualifying share of the sample times the chat-claim universe, with the Wilson interval scaled the same way.
  - Hit if the estimate is at least 10.
- **P6 and P7** don't use the checker. Their script, `p6_p7.py`, is public in `audit/run-plan` and fingerprinted in the 3 Oct evening manifest (`PRIVATE-MANIFEST-2.txt`).
  - Its result file, `Data\results\p6_p7.json`, was computed on 3 Oct and never opened. It was not sealed by itself.
  - Its SHA-256, d75710e25a09402e938bcc032b928f639b2238a9550d5572a71e44f74eded959, is recorded here, before anyone opens it.
  - The script is then re-run, and the two must match before P6 and P7 are reported.
- **The two labels on every result:** "low-coverage" (the extractor finds 23 to 27% of claims) and "provisional until gate 4".
- **Nothing changes after this seal.** Any change is a new run, sealed separately.

## Predictions sealed for this run
- **Jev** (`2026-10-04-jev-update`, sealed 05:12:47 UTC, before this plan):
  - P1 (contradicted at least 5% of linked chat claims): 0.46;
  - P2 (not shown over 50% of all chat claims): 0.33;
  - shown share among linked chat claims: under 25% 0.54, 25 to 50% 0.33.
- **Claude:**
  - P1: 0.45.
  - P2: 0.85. Many claims have no turn by the agent in the prior day, and the reader fails closed.
  - Shown share among linked chat claims: under 25% 0.25; 25 to 50% 0.40; 50 to 75% 0.30; over 75% 0.05.
  - P5 (estimated census count at least 10): 0.35.
  - **The dangerous direction:** no sampled claim is answered shown where a person reading the deciding line would call it a failure. 0.80. This is checked by Joshua and George on the shown answers, after the run.

## Order of work
1. Seal this plan: SHA-256, OpenTimestamps and FreeTSA.
2. Build the index, and write the universe files.
3. When `check_blocks.py` confirms this plan's proof in a Bitcoin block, read that block's hash, take the seed and draw the sample.
4. Fingerprint the sample and the run folder, then start the run.
5. Score, write it up with every caveat, and seal the results. Publication waits for Joshua's yes, before the hackathon deadline (Monday 00:00 UTC) if it's ready.
