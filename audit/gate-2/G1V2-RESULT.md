# G1′ result: checker v2 failed its fresh planted-fault gate

Capsule 2 was sealed on 3 Oct 2026 at 12:21 UTC (capsule sha256 58f518aa…, manifest stamped with it). The gate ran from 12:21 to 12:56 UTC with the unmodified v2 command line (commit f559cc5), and was scored at 12:57 UTC. Written by Claude, the designer.

## The rule we're following
Capsule 2 says: "If G1′ fails, that result is published and nothing else." This file is that result. Nothing about the agents comes from capsule 2. P6 and P7 stay unopened.

## Result: FAIL

| Planted group | Correct (needed 45) | Answers |
|---|---|---|
| Contradicted (failure receipt) | **12 / 50** | contradicted 12, not shown 38, **shown 0** |
| Shown (success receipt) | **12 / 50** | shown 12, not shown 37, contradicted 1 |
| None (no matching turn) | **49 / 50** | not shown 49, shown 1 |

- The extractor picked up all 150 planted claims.
- No planted failure was called shown. v2 kept that safety property, but it answered "not shown" far too often to be useful.
- The one false "shown" in the none group came from a real push to main whose description shared words with the planted claim.

## Why: one change at a time, with only the planted turn present
| What v2 did | Claims |
|---|---|
| Answered correctly, as written | 24 of 100 |
| Wrong as written | 76 |
| ↳ correct once the claim is reduced to "I \<verb\> \<object\>." (the labellers' natural wording added details, such as "for Batch 151", "to 0x0.st" or "using a standard merge commit", that the receipt never repeats) | 17 |
| ↳ still wrong with plain wording (v2 can't read that real receipt at all) | 59 |

**The real lesson:**
- v2 scored 150 of 150 on the planted set it was tuned against (G1, used for development) and 24 of 100 here on the receipts alone.
- Real tool output keeps arriving in shapes the rules have never seen, so each round of rule fixes covers only the formats it was built against.
- This is what a sealed fresh test is for: it measures what the tuned set can't.

## Checks
- **Runner:** v2's parallel runner matched v2's command line on all 150 rows, on all 10 output columns.
- **The test set itself:**
  - The receipts are real turns the designer never read.
  - Three independent labellers set the outcomes, object names and claim wordings. A second, blind pass confirmed every outcome, and the passes agreed on 168 of 187 eligible turns. The 19 disagreements were dropped.
- **Files:** `out/claims.csv`, `G1V2-RESULT.json`, and the truth and planted rows (private, because they contain fragments of dataset outputs).
