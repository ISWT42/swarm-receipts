# Correction before the draw: the seed rule (4 Oct 2026, written 07:23 to 07:26 UTC)

This note sits beside the sealed plan, `AGENT-RUN-PLAN-2026-10-04.md`:
- its SHA-256 is in `AGENT-RUN-PLAN-SHA256.txt`;
- FreeTSA stamped it at 05:14:40 UTC;
- its Bitcoin block is 969803.

The sealed file is not edited.

## The fault
The plan says the seed is "the first 16 hex digits of the hash of the Bitcoin block that confirms this plan's OpenTimestamps proof". It also says: "Nobody can know the seed when this plan is sealed."

Bitcoin block hashes begin with a run of zeros (proof of work).
- Block 969803's hash is `0000000000000000000174bde09896480611152a6faff8ca8956f0718aba76d6`, which starts with 19 zeros.
- So its first 16 hex digits are all zeros, and the rule as written gives seed 0.
- Every block mined at today's difficulty gives the same seed 0.
- Anyone could therefore have known the seed when the plan was sealed. The rule as written breaks the plan's own stated property.

## When it was caught
It was caught on 4 Oct 2026 at 07:14 UTC, while preparing the draw.
- No sample had been drawn, with seed 0 or any other seed.
- The memory-claim universe was still being written.
- The same rule worked for the labelling sample, because that seed came from a file's SHA-256, which has no leading zeros. That is how the fault slipped through.

## The correction (one rule, fixed before any draw)
- **The new rule:** the seed is the first 16 hex digits after the block hash's leading zeros, `int(block_hash.lstrip("0")[:16], 16)`.
- **For block 969803:** the digits are `174bde0989648061`, so the seed is 1678679418666778721.
- **Why this rule:**
  - It keeps the sealed wording, "first 16 hex digits".
  - It restores the property the plan states: those digits did not exist until the block was mined at 05:50 UTC, which was after the plan was sealed at 05:14:40 UTC.
- **Considered and not used:**
  - the whole hash as one integer;
  - the last 16 hex digits;
  - waiting for a later block.

  No sample was computed under any of them, or under seed 0. I chose the rule closest to the sealed words.

## The code change
In `make_agent_sample.py`, two edits, both in `draw()`:
- the seed line now strips the leading zeros;
- `SAMPLE.json` now records a `seed_rule` field.

| | SHA-256 of `make_agent_sample.py` |
|---|---|
| Before | b411b01e4d9ac8ad58480cc6869f8cfe80c6db83985fa20d110ce262a91ecfeb |
| After | f696117910bf0b5caa227d77d8d11c23582b8b8603a1693d231ad7df2459ad2a |

Everything else in the plan is unchanged: the universe, the draw order (chat first, then memory, from one generator), the sizes, the checker, the analysis and the predictions. The write-up reports this correction beside the results.

Claude (Opus 5.5), for Joshua Bauer
