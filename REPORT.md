# swarm-receipts report

Built an offline, Python standard-library command-line checker. It extracts
explicit completion claims from chat and memories, links earlier computer-use
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
python swarm_receipts.py --data fixtures --inspect --limit 3
```

- **Unit tests: 72 passed**, including the planted-fault test, exact receipt
  checks, extraction exclusions, nested field remapping, timestamps, limits,
  session linking, temporary-index cleanup and adversarial outcomes.
- **Fixture run: 60 claims checked**, with 20 shown, 20 contradicted and 20 not
  shown. Created `results/claims.csv`, `results/summary.md` and
  `results/memory_check.md`.
- **Inspection: passed** on all seven fixture source files. The output is saved
  in `results/inspect.txt`; long-text truncation is also covered by a test.
- **Deterministic fixture regeneration: passed** byte-hash comparisons. The
  fixture contains three agents, 60 claims (45 chat, 15 memory), and 360 turns.

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

## Scale check

Ran `python3 benchmark_scale.py --out results/scale_check.json`. Separate
processes generated gzip records incrementally, built the index, and streamed
all candidate turns. Exact indexed and streamed counts, memory limits and
temporary-file cleanup passed for both runs.

| Turns | Peak process memory | Index build | Candidate stream | Total |
| ---: | ---: | ---: | ---: | ---: |
| 100,000 | 19.625 MiB | 3.526 s | 0.243 s | 4.171 s |
| 1,000,000 | 19.375 MiB | 36.723 s | 2.490 s | 43.591 s |

The million-turn index used 503,693,312 bytes (about 480 MiB) of disk before
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
  streamed query peaked at 19.375 MiB, with exact record counts and cleanup.
  Larger real rows or a different query workload could change those costs.
- **Could synthetic accuracy be passed off as real accuracy?** This report and
  README explicitly limit the claims to planted tests. An independently labeled
  real sample is still needed and could expose extraction or linking errors.
