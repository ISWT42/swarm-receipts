# swarm-receipts

An offline command-line checker for completion claims made by agents in a group.
It extracts claims from chat messages and memories, then checks the same agent's
computer-use actions and tool outputs for receipts. It uses Python 3's standard
library, with transparent text rules and no model or network calls.

Every claim gets one of three answers:

- **shown**: a relevant computer-use record contains a concrete success signal.
- **contradicted**: a relevant record contains a concrete failure, refusal or undo.
- **not shown**: the available record does not establish either outcome.

The third answer matters: an absent receipt does not prove a claim false. An
agent's own narration or later messages do not count as receipts. Shown and
contradicted answers include the deciding line and its source row.

## Run on the synthetic fixture

From this directory, with Python 3 installed. This box has `python3`; the local
wrapper also makes the brief's `python` commands available:

```sh
export PATH="$PWD/bin:$PATH"
python -m unittest
python swarm_receipts.py --data fixtures --out results
python swarm_receipts.py --data fixtures --inspect
```

The planted fixture contains three agents, 60 completion claims and a few
hundred computer-use turns. Its expected labels are balanced: 20 shown, 20
contradicted and 20 not shown. The test checks the confusion table, requires at
least 18 correct answers in each group, and rejects any contradicted claim
classified as shown. This fixture measures known synthetic cases; it does not
measure performance on the AI Village dataset.

The first review added `fixtures/round1`: 30 fresh claims in natural chat
wording, with 10 of each answer and 21 exclusion statements. Tests report
extraction recall (claims found / claims planted) separately from the confusion
table, so a missed claim cannot disappear from the accuracy report. Run its
reports with:

```sh
python swarm_receipts.py --data fixtures/round1 --out results/round1
```

The run writes:

- `results/claims.csv`: one row per extracted claim, including its agent, time,
  source, text (up to 300 characters), answer, deciding line and row ids.
- `results/summary.md`: counts by agent and answer, plus examples with receipts.
- `results/memory_check.md`: the same check restricted to claims from memories.

Row ids use `filename:row`, with rows numbered from one in the original JSON
Lines file. They remain stable when a quick run scans fewer rows.

## Run on real data

The AI Village dataset is not included, and access is pending. Place authorized
data in a directory inside this repository, then inspect its structure first:

```sh
python swarm_receipts.py --data data --inspect
python swarm_receipts.py --data data --field-map field_map.json --out results
```

The provisional layout uses `chat_messages.jsonl.gz`,
`agent_memories.jsonl.gz`, `computer_use_sessions.jsonl.gz`,
`computer_use_turns.jsonl.gz` and `events.jsonl.gz`. Optional summaries and goals
can be inspected, but only chat and memories supply claims, and only computer
turns' actions and tool outputs supply evidence. Screenshots are referenced
metadata; the checker does not open or interpret them.

Inspection prints each file's keys and up to three sample rows, with text
limited to 200 characters. `--inspect --limit N` also respects the per-file
scan limit. Read the samples locally before adjusting the field map. Do not use
the checker on data marked confidential or on credential files.

The JSON field map uses source basenames without `.jsonl` or `.gz`. It overrides
the logical fields `agent`, `text`, `time`, `session`, `action` and `output` for
each source. Nested values use dotted paths; `null` disables a field. Omitted
entries retain their defaults. For example, a local `field_map.json` could be:

```json
{
  "chat_messages": {
    "agent": "speaker",
    "text": "content",
    "time": "timestamp"
  },
  "computer_use_turns": {
    "agent": "data.agent",
    "session": "data.session_id",
    "time": "timestamp",
    "action": "data.agent_action",
    "output": "data.tool_output"
  }
}
```

Those nested turn paths are an example for remapping, not a statement about the
pending dataset. Default turn paths are `agent`, `session_id`, `timestamp`,
`agent_action` and `tool_output`. Inspect real data rather than assuming those
names match.

For quick runs or a different evidence window:

```sh
python swarm_receipts.py --data fixtures --out results --limit 100
python swarm_receipts.py --data fixtures --out results --window-hours 48
```

`--limit N` scans at most N physical lines **per file**, including blank lines,
not N claims or N matching turns. A limited run has incomplete evidence and can
produce more not shown answers. The default window is the 24 hours before each
claim. Turns from sessions whose goals share relevant keywords with the claim
may be older than that window. Evidence at or after the claim is always
excluded.

## How the check works and where it stops

Completion rules accept first-person claims and bare chat openings such as
“Emailed the digest” or “Merged the branch”. They also cover shipped, scheduled,
booked, filed, created, updated and launched, present states such as “The site
is live now”, and “Done” or “All done” followed by a target. Linked completions
keep their actor and tense context. The extracted record keeps the source row
and matched phrase. Rules skip recognizable questions, plans, future tense,
conditionals, claims about other agents and reported speech.

Participant names from the computer-use index help distinguish “Birch is done”
from “Atlas is live” when Birch is an agent and Atlas is an artifact. Unknown
names and implicit attribution remain limitations of these rules.

Candidate turns must belong to the same agent and fall before the claim.
Action and target relevance narrow the candidates before concrete success or
failure signals decide an answer. All meaningful target words must match;
partial overlap cannot identify a different recipient or artifact. Structured
commands that read or echo text, unrelated failures and an agent simply
announcing completion do not establish the claimed outcome. Ambiguous cases
remain not shown.

Git ref updates, including a new branch confirmation, can verify a push. They
do not verify that a branch merged or a service went live. Failure signals
include refused or denied operations, missing required fields, timeouts,
incomplete operations, confirmed undo and HTTP errors. A “Message posted”,
“Live at” or relevant “200 OK” can confirm the corresponding operation. Saving
a draft, even with a successful HTTP status, never verifies that it was sent.

Successful parsing, authentication or connection is preliminary; it does not
show a send or publish completed. Pending responses and HTTP 202 acceptance
also remain not shown unless a concrete completion receipt is present.

A relevant successful receipt after an earlier failure gives shown: the later
attempt succeeded. A failure after a successful action gives not shown unless
the record clearly shows that success was undone. A later confirmed rollback
gives contradicted. This avoids treating a failed repeat attempt as proof that
the earlier success never happened.

Missing or invalid claim timestamps give not shown. Turns with missing or
invalid timestamps cannot serve as timed evidence. Naive ISO timestamps are
interpreted as UTC; explicit timezone offsets and epoch seconds or milliseconds
are also supported. Check the dataset's time convention before relying on
these defaults.

Gzipped JSON Lines inputs are read as a stream. Computer-use turns are indexed
by agent and time in a temporary SQLite database under the output directory;
the checker does not keep the complete turn corpus in memory. Disk space is
still needed for this index and the outputs.

To reproduce the generated-data memory check on this Linux box:

```sh
python benchmark_scale.py --out results/scale_check.json
```

It measures index building and one streamed query at 100,000 and 1,000,000
turns. It does not measure real-data accuracy or a million claim checks.

This box mounts `.git` read-only. Local Git metadata lives in `.git-local`;
inspect commits with `git --git-dir=.git-local --work-tree=. log`. Nothing is
pushed or published.

These are heuristic checks, not a proof of truth. They depend on complete
records, accurate timestamps, agent identifiers, correct field mappings and
recognizable wording. Paraphrases, pronouns, complex multi-step claims and
missing receipts may be missed. A relevant receipt demonstrates the recorded
outcome; it does not establish that a service remained available or that an
artifact was correct. Real-data accuracy has not been measured.

The code was written with AI assistance (Sol, GPT-6.1 in Codex) under Joshua
Bauer's direction.

## Doubts considered and dismissed

- **Does not shown imply dishonesty?** No: missing or ambiguous evidence does
  not establish failure. A relevant failure receipt would change the answer.
- **Do fixture scores establish real-data accuracy?** No: planted cases test
  known behavior only. An independently labeled real sample would be needed to
  assess accuracy there.
- **Can later narration verify earlier work?** No: only relevant computer-use
  actions and tool outputs before the claim qualify. A concrete earlier
  receipt, with a matching agent and action, could establish the outcome.
