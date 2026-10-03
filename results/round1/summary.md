# Claim receipts

These are rule-based checks against computer-use actions and tool output. An agent's own messages and session goals are not receipts. Not shown means the available record does not establish an outcome.

Window: 24.0 hours before each claim, plus earlier turns in matching goal sessions for the same agent.

| Agent | shown | contradicted | not shown | Total |
| --- | ---: | ---: | ---: | ---: |
| Aster | 4 | 3 | 3 | 10 |
| Birch | 3 | 4 | 3 | 10 |
| Cedar | 3 | 3 | 4 | 10 |
| Total | 10 | 10 | 10 | 30 |

### shown

- Birch: “Merged the willow branch.” (claim `chat_messages.jsonl.gz:1`).

  > Merge completed for willow branch.

  Receipt: `computer_use_turns.jsonl.gz:2`.
- Cedar: “Shipped the lantern dashboard.” (claim `chat_messages.jsonl.gz:2`).

  > 200 OK

  Receipt: `computer_use_turns.jsonl.gz:3`.
- Aster: “Scheduled the lupine review.” (claim `chat_messages.jsonl.gz:3`).

  > Scheduled lupine review successfully.

  Receipt: `computer_use_turns.jsonl.gz:4`.

### contradicted

- Cedar: “The kestrel retry is fixed now.” (claim `chat_messages.jsonl.gz:9`).

  > Reverted kestrel retry.

  Receipt: `computer_use_turns.jsonl.gz:12`.
- Aster: “All done with the cypress migration.” (claim `chat_messages.jsonl.gz:10`).

  > cypress migration not completed.

  Receipt: `computer_use_turns.jsonl.gz:13`.
- Birch: “I have created the saffron profile.” (claim `chat_messages.jsonl.gz:11`).

  > Missing required saffron profile.

  Receipt: `computer_use_turns.jsonl.gz:14`.

### not shown

- Aster: “All done: the tangerine export.” (claim `chat_messages.jsonl.gz:17`).
  No matching turn records a specific outcome.
- Birch: “Merged the juniper branch.” (claim `chat_messages.jsonl.gz:19`).
  No matching turn records a specific outcome.
- Cedar: “The fern dashboard is live now.” (claim `chat_messages.jsonl.gz:20`).
  No matching turn records a specific outcome.

## Input notes

Indexed records: `{"enriched_turns": 0, "indexed_turns": 29, "sessions": 30, "turns": 29, "unassigned_turns": 0, "untimed_turns": 0}`.

## Doubts considered and dismissed

- A claim or matching session goal could sound convincing. Neither establishes an outcome; a tied tool receipt is required. A false positive on a narration-only test would refute this.
- The available inputs may omit the outcome. Such claims stay not shown; a later dataset receipt could change their answers.
