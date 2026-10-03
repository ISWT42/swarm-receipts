# Fresh round 1 claims

This separate fixture adds 30 hand-planted completion claims: 10 shown, 10
contradicted, and 10 not shown. The original 60-claim Sonny Test is unchanged.
The new wording covers bare past verbs, additional action verbs, state claims,
and short `Done` / `All done` closers in both chat and memories. Twenty-one
other statements exercise questions, plans, conditionals, reported speech,
other agents' work, and closers without a target.

The 29 computer-use turns include actual confirmations and failures, plus
draft saves, another agent's receipt, a future receipt, read-only access,
simulation, pending work, unrelated work, and agent narration. The checker
must find the planted claim before its classification counts toward the
confusion table. `truth.json` is a test manifest, never checker evidence.

Run from the repository root:

```text
python3 -m unittest tests.test_round1
python3 swarm_receipts.py --data fixtures/round1 --out results/round1
```

`python3 generate_round1_fixture.py` regenerates the records deterministically.
