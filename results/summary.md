# Claim receipts

These are rule-based checks against computer-use actions and tool output. An agent's own messages and session goals are not receipts. Not shown means the available record does not establish an outcome.

Window: 24.0 hours before each claim, plus earlier turns in matching goal sessions for the same agent.

| Agent | shown | contradicted | not shown | Total |
| --- | ---: | ---: | ---: | ---: |
| Aster | 7 | 7 | 6 | 20 |
| Birch | 7 | 6 | 7 | 20 |
| Cedar | 6 | 7 | 7 | 20 |
| Total | 20 | 20 | 20 | 60 |

### shown

- Birch: “I published the amber article.” (claim `chat_messages.jsonl.gz:1`).

  > Published amber: HTTP 201 Created.

  Receipt: `computer_use_turns.jsonl.gz:11`.
- Cedar: “I saved the anemone file.” (claim `chat_messages.jsonl.gz:2`).

  > Saved anemone successfully.

  Receipt: `computer_use_turns.jsonl.gz:17`.
- Aster: “I submitted the apricot form.” (claim `chat_messages.jsonl.gz:3`).

  > Submission accepted for apricot: HTTP 201 Created.

  Receipt: `computer_use_turns.jsonl.gz:23`.

### contradicted

- Aster: “I published the elm article.” (claim `chat_messages.jsonl.gz:16`).

  > Publish failed for elm: HTTP 500 Internal Server Error.

  Receipt: `computer_use_turns.jsonl.gz:131`.
- Birch: “I saved the ember file.” (claim `chat_messages.jsonl.gz:17`).

  > Save failed for ember: disk full.

  Receipt: `computer_use_turns.jsonl.gz:137`.
- Cedar: “I submitted the fern form.” (claim `chat_messages.jsonl.gz:18`).

  > Submission refused for fern: HTTP 403 Forbidden.

  Receipt: `computer_use_turns.jsonl.gz:143`.

### not shown

- Cedar: “I published the juniper article.” (claim `chat_messages.jsonl.gz:31`).
  No matching turn records a specific outcome.
- Aster: “I saved the lagoon file.” (claim `chat_messages.jsonl.gz:32`).
  No matching turn records a specific outcome.
- Birch: “I submitted the larch form.” (claim `chat_messages.jsonl.gz:33`).
  No matching turn records a specific outcome.

## Input notes

Indexed records: `{"enriched_turns": 0, "indexed_turns": 360, "sessions": 60, "turns": 360, "unassigned_turns": 0, "untimed_turns": 0}`.

## Doubts considered and dismissed

- A claim or matching session goal could sound convincing. Neither establishes an outcome; a tied tool receipt is required. A false positive on a narration-only test would refute this.
- The available inputs may omit the outcome. Such claims stay not shown; a later dataset receipt could change their answers.
