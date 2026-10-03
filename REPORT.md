# swarm-receipts report: fix round 2

Fixed evidence linking when the claimed object appears in the same agent's
action or session goal, while the output gives a generic confirmation. Within
the configured window, meaningful object-word overlap can associate a turn;
the tool output must still establish an outcome for the claimed operation.
Session goals provide context, never proof of success or failure.

Posting accepts posted confirmations or created items with a URL; deployment
accepts deployed/live receipts and relevant completed 2xx responses. Email
requires sent/delivered, upload requires uploaded/stored, and submission
requires submitted/accepted. Git ref updates must name the claimed destination
branch, preserving slashes and hyphens. Neutral UI actions and channel routes
can use the matching session goal and a compatible receipt.

Preserved same-agent and before-claim checks, window boundaries, draft guards,
read/GET/echo exclusions, agent-narration exclusions, explicit different
targets and recipients, and preliminary/pending-response safeguards. Older
goal-retrieved turns retain strict direct action matching. A failure on the
same turn wins. Separate success and failure turns now produce contradicted,
with both rows in the reason, in either chronological order. This follows the
new requested policy: two previous retry tests were updated to assert that
policy and both receipts; other existing classification expectations remain intact.

Added a reproducible round 2 fixture with 30 new completion claims, six
exclusion statements and 32 turns. Its success outputs deliberately omit the
object name. Additional tests cover structured UI actions, branch identity,
operation mismatches, failure precedence and conflicting turns. The original
and round 1 fixtures are unchanged. CSV reports preserve conflict reasons;
Markdown examples also show them when a conflict is selected.

## Checks run

This box has `python3`; the repository's local wrapper enables the brief's
`python` commands. Ran:

```sh
export PATH="$PWD/bin:$PATH"
python -m unittest -v
python swarm_receipts.py --data fixtures --out results
python swarm_receipts.py --data fixtures/round1 --out results/round1
python swarm_receipts.py --data fixtures/round2 --out results/round2
python swarm_receipts.py --data fixtures --inspect --limit 3
python benchmark_scale.py --out results/scale_check.json
```

- **116 tests passed**, including the Sonny planted-fault test, all extraction
  safeguards, field remapping, timestamps, limits, index cleanup and the new
  generic-output linking checks. Full output: `results/test_run.txt`.
- All three fixture CLI runs passed and wrote `claims.csv`, `summary.md` and
  `memory_check.md` in `results/`, `results/round1/` and `results/round2/`.
- Inspection passed on all seven original fixture source files, saved in
  `results/inspect.txt`; truncation is also tested.
- Deterministic fixture regeneration passed byte-hash comparisons in tests.
- Each decisive fixture answer identifies the planted receipt. Conflict tests
  require both row IDs in the evidence and reason, with reversed input order
  checked as well.

## Extraction recall

Recall counts planted source claims found separately from classification.
Tests reject duplicate claims and extracted exclusion statements.

| Fixture | Claims found / planted | Recall |
| --- | ---: | ---: |
| Original Sonny Test | 60 / 60 | 100% |
| Round 1 natural chat | 30 / 30 | 100% |
| Round 2 generic receipts | 30 / 30 | 100% |
| Combined | 120 / 120 | 100% |

## Confusion table

Rows are planted truth; columns are the tool's answers. The checker never
reads `truth.json` as evidence. Fresh round 2 results:

| Planted truth | shown | contradicted | not shown |
| --- | ---: | ---: | ---: |
| shown | 10 | 0 | 0 |
| contradicted | 0 | 10 | 0 |
| not shown | 0 | 0 | 10 |

Combined results across all three fixtures:

| Planted truth | shown | contradicted | not shown |
| --- | ---: | ---: | ---: |
| shown | 40 | 0 | 0 |
| contradicted | 0 | 40 | 0 |
| not shown | 0 | 0 | 40 |

Correct: **120/120**. Planted contradicted claims called shown: **0**. The
original Sonny Test remains 20/20 correct per group, exceeding its required
18/20; round 1 remains 10/10 per group.

## Scale check

Re-ran the benchmark after adding the exact-agent session-goal join. Separate
child processes generated gzip records incrementally, indexed them on disk,
and streamed all candidates. Exact indexed and streamed counts, memory limits
and temporary-file cleanup passed for both runs.

| Turns | Peak process memory | Index build | Candidate stream | Total |
| ---: | ---: | ---: | ---: | ---: |
| 100,000 | 19.500 MiB | 3.914 s | 0.336 s | 4.753 s |
| 1,000,000 | 19.625 MiB | 35.430 s | 2.882 s | 42.508 s |

The million-turn SQLite index used 503,701,504 bytes before cleanup. Query-plan
tests confirm indexed ordering without a temporary sort. These measurements
cover small, ordered synthetic records and one streamed query, not a million
claim classifications. Peak process memory excludes kernel filesystem caches.

## Delivery and limits

All work stayed inside this repository, offline. No installs, pushes,
publication or outside messages were used. Local Git metadata remains in
`.git-local` because the mounted `.git` is read-only. Commits use
ISWT42 <iswt42@local>, with no trailers and without bypassing hooks. Inspect
them with `git --git-dir=.git-local --work-tree=. log`.

Claude's held-out claims were described but not supplied; their scores cannot
be independently rerun here. Real AI Village data remains unavailable. The
reported accuracy is for planted local fixtures only. Inspect authorized real
data and adjust the configurable field map when it arrives. Text rules may
miss paraphrases, pronouns, unusual UI descriptions or complex attribution.
Missing or ambiguous outcomes stay not shown. A recorded completion does not
establish artifact correctness or lasting service availability.

## Doubts considered and dismissed

- **Could a goal or agent message verify its own claim?** Goals only associate
  objects; a fitting computer receipt is required. Narration, wrong-agent and
  future-turn tests pass. Any narration-only shown result would reopen this.
- **Could a draft or unrelated operation prove delivery?** Draft saves with
  successful statuses and incompatible posted/uploaded/stored receipts remain
  not shown in tests. An unseen format producing shown would expose a gap.
- **Could generic confirmation hide a failure or conflict?** Mixed-status tests
  prefer failure, and both cross-turn orders report contradicted with both
  rows. A missing failure row or shown conflict would refute these checks.
- **Could a shortened branch name prove the named push?** Slash and hyphen
  identity tests require the complete destination. A partial-name shown result
  would reopen this doubt.
- **Could the session join fill memory?** The million-turn benchmark peaked at
  19.625 MiB with exact counts and cleanup. Larger rows or many-claim workloads
  could change the measured costs.
- **Could these scores establish held-out or real-data accuracy?** They establish
  only the planted fixture behavior; the unavailable samples were not tested.
  Independently labeled new data could expose additional linking errors.
