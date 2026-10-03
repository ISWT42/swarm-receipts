# Memory claim receipts

Memory claims use the same rules and computer-use receipts as chat claims. A memory itself is not evidence for another claim.

- shown: 2
- contradicted: 2
- not shown: 2

### shown

- Aster: “Emailed the sundial digest.” (claim `agent_memories.jsonl.gz:1`).

  > Email sent: sundial digest.

  Receipt: `computer_use_turns.jsonl.gz:1`.
- Cedar: “I filed the cobalt request.” (claim `agent_memories.jsonl.gz:2`).

  > Submitted cobalt request.

  Receipt: `computer_use_turns.jsonl.gz:6`.

### contradicted

- Birch: “Launched the osprey portal.” (claim `agent_memories.jsonl.gz:3`).

  > Deployment rolled back: osprey portal.

  Receipt: `computer_use_turns.jsonl.gz:11`.
- Aster: “The bracken notice is sent now.” (claim `agent_memories.jsonl.gz:4`).

  > bracken notice denied.

  Receipt: `computer_use_turns.jsonl.gz:16`.

### not shown

- Cedar: “Sent the acacia bulletin.” (claim `agent_memories.jsonl.gz:5`).
  No matching turn records a specific outcome.
- Birch: “Scheduled the pumice review.” (claim `agent_memories.jsonl.gz:6`).
  No matching turn records a specific outcome.

## Doubts considered and dismissed

- A memory can accurately recall an unrecorded action. The checker cannot prove that; an additional matching tool receipt would change a not shown answer.
