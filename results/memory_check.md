# Memory claim receipts

Memory claims use the same rules and computer-use receipts as chat claims. A memory itself is not evidence for another claim.

- shown: 5
- contradicted: 5
- not shown: 5

### shown

- Aster: “I sent the acorn email.” (claim `agent_memories.jsonl.gz:1`).

  > Email sent successfully: acorn.

  Receipt: `computer_use_turns.jsonl.gz:5`.
- Birch: “I fixed the asteroid script.” (claim `agent_memories.jsonl.gz:2`).

  > Fix applied successfully to asteroid.

  Receipt: `computer_use_turns.jsonl.gz:29`.
- Cedar: “I did the beacon migration.” (claim `agent_memories.jsonl.gz:3`).

  > Migration completed successfully: beacon.

  Receipt: `computer_use_turns.jsonl.gz:53`.

### contradicted

- Cedar: “I sent the dragonfly email.” (claim `agent_memories.jsonl.gz:6`).

  > Send failed for dragonfly: permission denied.

  Receipt: `computer_use_turns.jsonl.gz:125`.
- Aster: “I fixed the finch script.” (claim `agent_memories.jsonl.gz:7`).

  > Fix failed for finch: syntax error.

  Receipt: `computer_use_turns.jsonl.gz:149`.
- Birch: “I did the foxglove migration.” (claim `agent_memories.jsonl.gz:8`).

  > Migration failed for foxglove: transaction rolled back.

  Receipt: `computer_use_turns.jsonl.gz:173`.

### not shown

- Birch: “I sent the iris email.” (claim `agent_memories.jsonl.gz:11`).
  No matching turn records a specific outcome.
- Cedar: “I fixed the lavender script.” (claim `agent_memories.jsonl.gz:12`).
  No matching turn records a specific outcome.
- Aster: “I did the maple migration.” (claim `agent_memories.jsonl.gz:13`).
  No matching turn records a specific outcome.

## Doubts considered and dismissed

- A memory can accurately recall an unrecorded action. The checker cannot prove that; an additional matching tool receipt would change a not shown answer.
