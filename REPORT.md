# swarm-receipts report: fix round 1

Widened the offline, Python standard-library checker after the independent
review found missed natural-chat claims. Extraction now accepts bare past-tense
openings, the requested additional verbs, current state claims, and Done/All
done closers with a target. It preserves questions, plans, conditionals,
quotations and other-agent exclusions, including across linked clauses.

Added git ref-update receipts, the requested failure signals, message and
deployment confirmations, and explicit draft-save guards. A push does not
prove a merge or a live deployment; a saved draft does not prove delivery.

The tool extracts completion claims from chat and memories, links earlier computer-use
turns by agent, time and session goal, and answers shown, contradicted or not
shown. Decisive answers quote actual tool output and identify the receipt row.
The rules require matching operations and targets; agent narration, screenshots,
future evidence and unrelated successful reads cannot establish completion.

The repository includes configurable field maps, an inspection mode, a
disk-backed SQLite index, three generated reports, a deterministic synthetic
fixture, a reproducible scale check and plain-language instructions.

## Checks run

This machine supplies `python3`, but no `python` command. With the repository's
local wrapper enabled, the brief's commands work:

```sh
export PATH="$PWD/bin:$PATH"
python -m unittest
python swarm_receipts.py --data fixtures --out results
python swarm_receipts.py --data fixtures/round1 --out results/round1
python swarm_receipts.py --data fixtures --inspect --limit 3
```

- **Unit tests: 93 passed**, including the planted-fault test, exact receipt
  checks, extraction exclusions, nested field remapping, timestamps, limits,
  session linking, temporary-index cleanup and adversarial outcomes.
- **Fixture run: 60 claims checked**, with 20 shown, 20 contradicted and 20 not
  shown. Created `results/claims.csv`, `results/summary.md` and
  `results/memory_check.md`.
- **Fresh round 1 fixture: 30 claims checked**, with 10 shown, 10 contradicted
  and 10 not shown. Its three reports are in `results/round1/`. It adds 21
  exclusion statements and 29 computer-use turns in varied natural wording.
- **Inspection: passed** on all seven fixture source files. The output is saved
  in `results/inspect.txt`; long-text truncation is also covered by a test.
- **Deterministic fixture regeneration: passed** byte-hash comparisons. The
  fixture contains three agents, 60 claims (45 chat, 15 memory), and 360 turns.
  The separate round 1 fixture also passes deterministic regeneration.

The complete test output is saved in `results/test_run.txt`. New tests cover
each requested status family, normal and new-branch push confirmations, saved
drafts with successful statuses, state assertions, linked completion context,
method phrases, and known participant names without guessing artifact names.

## Extraction recall

Recall counts source completion claims found, separately from classification.
The tests also reject extracted exclusion statements and duplicate claims.

| Fixture | Claims found / planted | Recall |
| --- | ---: | ---: |
| Original Sonny Test | 60 / 60 | 100% |
| Fresh natural-chat round 1 | 30 / 30 | 100% |
| Combined | 90 / 90 | 100% |

## Confusion table

Rows are planted truth; columns are the tool's answers. Expected labels come
from `fixtures/truth.json`, which the checker never reads as evidence.

| Planted truth | shown | contradicted | not shown |
| --- | ---: | ---: | ---: |
| shown | 20 | 0 | 0 |
| contradicted | 0 | 20 | 0 |
| not shown | 0 | 0 | 20 |

Correct classifications: **60/60**; each group exceeds the required 18/20.
Planted contradicted claims called shown: **0**. Tests also require every
decisive answer to quote the exact planted receipt, so a correct label reached
through a distracting turn does not pass.

Fresh round 1 fixture, with truth in `fixtures/round1/truth.json`:

| Planted truth | shown | contradicted | not shown |
| --- | ---: | ---: | ---: |
| shown | 10 | 0 | 0 |
| contradicted | 0 | 10 | 0 |
| not shown | 0 | 0 | 10 |

Correct classifications: **30/30**. Combined: **90/90**, with 30 on each
diagonal and no off-diagonal results. Across both fixtures, planted
contradicted claims called shown: **0**.

## Scale check

Ran `python3 benchmark_scale.py --out results/scale_check.json`. Separate
processes generated gzip records incrementally, built the index, and streamed
all candidate turns. Exact indexed and streamed counts, memory limits and
temporary-file cleanup passed for both runs.

| Turns | Peak process memory | Index build | Candidate stream | Total |
| ---: | ---: | ---: | ---: | ---: |
| 100,000 | 19.625 MiB | 3.382 s | 0.250 s | 4.066 s |
| 1,000,000 | 19.500 MiB | 34.903 s | 2.484 s | 41.362 s |

Re-ran this benchmark after adding the on-disk participant-name lookup. The
million-turn index used 503,701,504 bytes (about 480 MiB) of disk before
cleanup. These measurements use small, ordered synthetic records. They cover
indexing and one streamed query, not a million claim classifications; peak
process memory excludes kernel filesystem caches.

## Delivery and limits

All work stayed inside this repository. No network, installs, pushes,
publication or outside messages were used.

The mounted `.git` directory is read-only, so ordinary `git init` failed.
Initialized local metadata with `git --git-dir=.git-local --work-tree=. init`.
Local commits use ISWT42 <iswt42@local>, with no trailers. Inspect them with
`git --git-dir=.git-local --work-tree=. log`; the normal `.git` mount remains
unchanged. The local Python wrapper is `bin/python`.

Real AI Village data was not tested: access is pending. The published layout
is provisional. Inspect the authorized data and adjust the field map before
using it. Text rules can miss paraphrases, pronouns and complex claims; missing
or ambiguous evidence stays not shown. A recorded success does not prove an
artifact correct or a service permanently available. Candidate queries can
scan substantial same-agent history, so many claims may take longer than the
single-query benchmark.

Claude's ten independent claims were not supplied, so their new recall cannot
be measured here. The recall above is for the original and fresh local
fixtures. Participant names absent from computer sessions and turns may still
be ambiguous; literal target matching can miss paraphrases and synonyms.

## Doubts considered and dismissed

- **Could the checker always avoid saying contradicted?** The Sonny Test
  correctly identifies all 20 planted failures. A dropped failure or a
  contradicted-to-shown result would fail the confusion checks.
- **Could successful distractors provide the receipts?** Tests check exact
  planted row ids and literal output quotes, including wrong-agent,
  wrong-target, metadata-read and future distractors. A different deciding row
  would fail those checks.
- **Could narration or quotation verify itself?** Tests exclude agent messages,
  nested transcripts, single and double quotes across sentences, and echo
  commands. A narration-only claim becoming shown would reopen this doubt.
- **Could preliminary success or a rollback request be mistaken for completion?**
  Tests cover parsed commands, authentication, HTTP 202, pending responses,
  pending and failed undo, actual rollback, conflicting statuses and retries.
  A new ambiguous response producing a decisive answer would show a rule gap.
- **Could a million turns fill memory?** The measured million-turn index and
  streamed query peaked at 19.500 MiB, with exact record counts and cleanup.
  Larger real rows or a different query workload could change those costs.
- **Could improved recall admit plans or another agent's work?** Fresh tests
  retain conditional, future, reporting and actor context across linked clauses;
  they also exclude case-insensitive known agent state claims while retaining
  named artifacts. A new excluded statement becoming a claim would reopen this.
- **Could a successful draft save prove a send?** Separate tests cover draft
  receipts with HTTP 201 and save actions that mention sending intent. They
  remain not shown. An uncovered draft-only shown result would refute the guard.
- **Could synthetic accuracy be passed off as real accuracy?** This report and
  README explicitly limit the claims to planted tests. An independently labeled
  real sample is still needed and could expose extraction or linking errors.
