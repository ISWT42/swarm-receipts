# Run plan: gate 3 (the exam) and the dialect test, 3 October 2026

Written by Claude, about 21:30 UTC. Joshua's decisions, given in chat at about 20:00 UTC:
- the exam: "Tonight, once sealed";
- Gemma 4: "Yes, gemma4:12b, ~8 GB" (downloaded from Ollama's official library at about 20:05 UTC);
- his prediction: "Collate it from my words";
- the dialect test: "Yes, tonight".

## The instrument, frozen
- **Code:** swarm-receipts v3, the model reader. Worktree `C:\Users\joshd\Workbench\swarm-receipts-v3`, branch v3-model-reader, commit **00956d9** (author ISWT42, no trailers; checked). `receipts_core.py` and `receipts_io.py` are identical to v2 (f559cc5).
- **Tests:** 164 run, 162 pass. The 2 failures are the Windows fixture-regeneration tests that fail on v1 and v2 as well.
- **System prompt:** sha256 659cadf64855d40332cb87b8b5f61efe23fad631dc74d85c95804287cdb27432.
- **Options:**
  - temperature 0, top_k 1, top_p 1, seed 20261003;
  - all penalties off, num_ctx 16384, num_predict 512, thinking off;
  - 300 s per call with one retry; three failed calls in a row stop the run.
- **Shown to the model:** at most 6 candidate turns per claim, with each output capped at its first 500 and last 1,000 characters.
- **Server:** Ollama 0.34.4, local only (127.0.0.1:11434). It never downloads models.
- **Models:**
  - qwen3.5:9b (primary): digest 6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7.
  - gemma4:12b (secondary): digest 6114515d63c17436a7c0417d82820ac65ad643e2806c5a3c89cb62846436ed0b. A mechanical check on 3 development claims (gate 1) gave 3 verified answers at about 103 s per call. Nothing was changed for it.
- **The exam:**
  - Data: `C:\Users\joshd\Data\g3\data`.
  - Index: `C:\Users\joshd\Data\g3-index\turn-index.sqlite`, built in 918 s by `Data\g3\build_index.py` with v3's own receipts_io. It holds 2,510,587 turns: the real record plus 100 planted turns.
  - A first build that used v1's receipts_io by mistake was stopped and set aside, unused, in `g3-index\discarded-v1-build`.

## Commands, in this order, one at a time
```
cd C:\Users\joshd\Workbench\swarm-receipts-v3
python swarm_receipts.py --data C:\Users\joshd\Data\g3\data --index C:\Users\joshd\Data\g3-index\turn-index.sqlite --out C:\Users\joshd\Data\g3\out-qwen3.5-9b --reader model --model qwen3.5:9b
python swarm_receipts.py --data C:\Users\joshd\Data\g3\data --index C:\Users\joshd\Data\g3-index\turn-index.sqlite --out C:\Users\joshd\Data\g3\out-gemma4-12b --reader model --model gemma4:12b
cd C:\Users\joshd\Data\g3
python score_g3.py out-qwen3.5-9b
python score_g3.py out-gemma4-12b
cd C:\Users\joshd\Data\dialect
python spot_claims.py --model qwen3.5:9b --out qwen3.5-9b
python spot_claims.py --model gemma4:12b --out gemma4-12b
python spot_claims.py --score --out qwen3.5-9b
python spot_claims.py --score --out gemma4-12b
```
- **If a run is interrupted:** repeat the same command with `--resume`. It reuses the cached replies and changes nothing.
- **If a run can't complete for a technical reason:** it is reported as not completed, with the reason.

## Start rule
- No exam call and no dialect call happens before this bundle's OpenTimestamps proof is confirmed in a Bitcoin block and checked against that block's header (`check_blocks.py`). The block and its time are recorded with the results.
- **Why:** this afternoon's pressure-direction predictions were stamped before that run, but their blocks had not landed when it began. A late block can only show that a file existed before that block.

## Nothing changes after this seal
- The checker, prompt, models, options, exam, scoring and pass marks stay exactly as sealed.
- Any change would be a new run on a fresh gate, sealed separately.

## Publication
- Both models' results, pass or fail, and every prediction scored, hits and misses, go to github.com/ISWT42/swarm-receipts after Joshua's yes.
- Published the same way as gates 1 and 2: the design, the manifest and its proofs, the result summary and the scripts.
- The answer key and the planted rows stay private, because they contain record text and the AI Village data terms forbid redistributing the record. Their fingerprints are in the sealed manifest.
