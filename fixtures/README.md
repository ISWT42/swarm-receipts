# Synthetic fixture

These files contain invented records for three agents, 60 completion claims,
and 360 computer-use turns. They are not AI Village data.

Run `python generate_fixture.py` from the repository to regenerate them. Gzip
headers and row order are deterministic. `truth.json` labels the planted
claims by their original file and 1-based line number and identifies each
deciding turn when one exists. The checker must not use this manifest.

Each group contains 20 claims: shown, contradicted, and not shown. Claim wording
covers sent, published, saved, submitted, fixed, deployed, posted, finished,
did, and have finished. Chat and memory rows both contain claims.

Every case includes tempting distractors: another agent succeeding, the same
agent succeeding on a different target, a read succeeding on the same target,
an agent reporting its own success in a turn message, and success after the
claim. Six extra chat rows contain plans, questions, other agents' work,
reported speech, or a conditional rather than completion claims.

The published dataset layout is provisional. These fixture fields make the
assumptions explicit; they do not establish the real dataset's field names.
