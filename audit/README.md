# The AI Village audit: what is here

The write-up is [../WRITEUP.md](../WRITEUP.md). This folder holds everything needed to check it, except the data, which is gated by its publishers.

| Folder | What it holds |
|---|---|
| `capsules/` | The two sealed study files, each with its SHA-256 and OpenTimestamps proof. Capsule 1 (v1) is confirmed in Bitcoin block 969704. Capsule 2 (v2) was stamped on 3 Oct 2026 at 12:21 UTC. |
| `gate-1/` | Gate 1, the planted-fault test for v1: its design, its generator (`make_g1.py`, plus the receipt miners), its scorer, its manifest with proof, and its result. |
| `gate-2/` | Gate 2, the fresh test for v2: its design, the random pool miner, the generator, the scorer, the note on the one unlabelled turn, the capsule-2 manifest with proof, and its result. |
| `claim-spotting/` | G2: the script, the pass-1 labels (ids and 0/1, with proof), the pass-2 labels (ids and 0/1 only), and the agreement and precision/recall summary. |
| `run-plan/` | The analysis plan sealed before any real claim was checked (with its correction note), the parallel runner and index builder, the analysis scripts, the P3 model-date table, and the memory-claim sample (ids only, with proof). |
| `LABELLER-PROMPTS.md` | The exact instructions the independent labellers received. |

## Checking a seal
1. **Hash it:** `sha256sum <file>` must match the value in the file's `*SHA256*.txt`.
2. **Check the proof:** `ots verify <file>.ots` with the OpenTimestamps client and a Bitcoin node. Or drop both files at https://opentimestamps.org.
3. **What a proof shows:** the file existed, exactly as it is, by the time of its block.

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

The scripts hold the author's local paths; change them to yours. The seeds are 20261003 (gate 1, the samples) and 20261005 (gate 2).
