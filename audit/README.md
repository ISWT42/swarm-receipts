# The AI Village audit: what is here

The write-up is [../WRITEUP.md](../WRITEUP.md). This folder holds everything needed to check it, except the data, which is gated by its publishers.

| Folder | What it holds |
|---|---|
| `capsules/` | The two sealed study files, each with its SHA-256 and OpenTimestamps proof. Capsule 1 (v1) is confirmed in Bitcoin block 969704. Capsule 2 (v2) was stamped on 3 Oct 2026 at 12:21 UTC. |
| `gate-1/` | Gate 1, the planted-fault test for v1: its design, its generator (`make_g1.py`, plus the receipt miners), its scorer, its manifest with proof, and its result. |
| `gate-2/` | Gate 2, the fresh test for v2: its design, the random pool miner, the generator, the scorer, the note on the one unlabelled turn, the capsule-2 manifest with proof, and its result. |
| `gate-3/` | Gate 3, the fresh test for v3 (the model reader), sealed before the first call: its design, pool miner, label-input maker, generator, index builder and scorer; the run plan and the dialect-test design; the bundle manifest, with its OpenTimestamps proof (Bitcoin block 969768) and a FreeTSA RFC 3161 timestamp; the start-rule change and the other-tool folder check, each with proof; and the qwen3.5:9b and gemma4:12b results, each sealed with its own fingerprints and timestamps. Also the dialect test's script (`spot_claims.py`, unchanged since the gate 3 seal) and the qwen3.5:9b result (`DIALECT-RESULT-qwen3.5-9b.json`, with its fingerprints and timestamps); and the gemma4:12b result (`DIALECT-RESULT-gemma4-12b.json`, with its fingerprints and a FreeTSA timestamp). The models' replies hold message text and stay private. |
| `agent-run/` | The first agent run, provisional. It holds the plan, sealed before the sample existed (FreeTSA 05:14 UTC on 4 Oct, Bitcoin block 969803, with the upgraded proof); the correction to the seed rule, stamped before the draw; the sample (ids and line maps only) and its seal, made before the first model call; the sampling, resume and analysis scripts; and the interim chat results (`INTERIM-CHAT-RESULTS.json`: counts and rates, no message text) with the fingerprints of the private files they come from. The memory claims were still running at the deadline. |
| `claim-spotting/` | G2: the script, the pass-1 labels (ids and 0/1, with proof), the pass-2 labels (ids and 0/1 only), and the agreement and precision/recall summary. |
| `run-plan/` | The analysis plan sealed before any real claim was checked (with its correction note), the parallel runner and index builder, the analysis scripts, the P3 model-date table, and the memory-claim sample (ids only, with proof). `P6-P7-RESULTS.json` is the two predictions that need no checker, computed on 3 Oct before gate 1 and opened on 4 Oct after a checker passed (its SHA-256, d75710e2..., was recorded in a sealed plan before opening; a fresh re-run of `p6_p7.py` reproduces it). |
| `LABELLER-PROMPTS.md` | The exact instructions the independent labellers received. |

## Checking a seal
1. **Hash it:** `sha256sum <file>` must match the value in the file's `*SHA256*.txt`.
2. **Check the proof:** `ots verify <file>.ots` with the OpenTimestamps client and a Bitcoin node. Or drop both files at https://opentimestamps.org.
3. **What a proof shows:** the file existed, exactly as it is, by the time of its block.
4. **Gate 3's second timestamp:** `GATE3-BUNDLE-MANIFEST-SHA256.txt.tsr` is an RFC 3161 reply from freetsa.org. Check it with OpenSSL and FreeTSA's published certificates (cacert.pem and tsa.crt from freetsa.org): `openssl ts -verify -in GATE3-BUNDLE-MANIFEST-SHA256.txt.tsr -data GATE3-BUNDLE-MANIFEST-SHA256.txt -CAfile cacert.pem -untrusted tsa.crt`.

The manifests also fingerprint private files: the truth files, the planted rows, and the copied record with planted turns appended. Those contain fragments of the dataset, so they aren't redistributed. They can be shared privately with the dataset's publishers.

## Reproducing the gates
You need research access to the AI Village dataset (Hugging Face: aidigestorg/ai-village).
1. **Map the export:** `python convert_village.py <raw export dir> <mapped dir>`. This is the field adapter; it changes no rule.
2. **Gate 1:** run `gate-1/mine_receipts.py` and `gate-1/mine_outcomes.py`, then `gate-1/make_g1.py`. Then run the checker at tag `v1-sealed`:

   ```
   python swarm_receipts.py --data <copy> --out <out>
   ```

   Then score with `gate-1/score_g1.py`.
3. **Gate 2:**
   - run `gate-2/mine_fresh.py`;
   - label the pool with the prompts in `LABELLER-PROMPTS.md`;
   - run `gate-2/make_g1v2.py prepare`, then the confirmation pass, then `make_g1v2.py build`;
   - run the checker at tag `v2-sealed`;
   - score with `gate-2/score_g1v2.py`.

4. **Gate 3:**
   - run `gate-3/mine_g3.py` (it excludes every turn in the gate 1 and gate 2 pools) and `gate-3/make_label_inputs.py`;
   - label with the prompts in `LABELLER-PROMPTS.md` (first pass, then the blind confirmation pass);
   - run `gate-3/make_g3.py prepare`, then `make_g3.py build`, then `gate-3/build_index.py` to build the turn index with v3's own code;
   - run the checker at v3 with `--reader model --model qwen3.5:9b --index <index>` (a local Ollama server), then again with `--model gemma4:12b`;
   - score with `gate-3/score_g3.py out-<model>`.

The scripts hold the author's local paths; change them to yours. The seeds are 20261003 (gate 1, the samples), 20261005 (gate 2) and 20261004 (gate 3).
