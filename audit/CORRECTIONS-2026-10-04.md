# Corrections and amendments (4 Oct 2026)

Sealed files are never edited. Corrections to them are recorded here, dated.

## A count error in a sealed gate 3 note
- `gate-3/G3-RESULT-qwen3.5-9b.md` says qwen gave "eight honest 'not shown' answers where the record did show success". That's wrong.
- Of its eight 'not shown' errors, seven hid a success and one missed a failure.
- Thanks to an independent review (ChatGPT) for catching it.

## A change in how predictions are reported
- **What the earlier plans said:** the sealed capsules (3 Oct) and the agent-run plan (4 Oct) said the predictions would be scored in public.
- **What changed:** on 4 Oct, at 08:16 UTC, I decided that predictions stay sealed privately from now on and are no longer scored in public.
- **Timing:** that was before the first agent run's chat results existed (about 12:05 UTC).
- **The record:** the decision is in privately sealed files timestamped by FreeTSA at 09:09:43 and 09:38:38 UTC on 4 Oct. The files are available on request.
- **What is unaffected:** P6 and P7 were scored publicly before this change and stay as published. The predictions themselves stay sealed, unchanged.

## The agent run's seed rule
- The original rule (the first 16 hex digits of the block hash) would have given seed 0, because Bitcoin hashes begin with zeros.
- The corrected rule (the first 16 digits after the zeros) was chosen after the block existed, and before any draw. No sample was drawn under any other rule.
- See `agent-run/CORRECTION-SEED-2026-10-04.md` and its time note.
