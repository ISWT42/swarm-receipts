# Fresh round 2 receipts

This fixture adds 30 hand-planted claims: 10 shown, 10 contradicted, and 10
not shown. Success outputs deliberately omit the claimed object, naming only
the outcome and sometimes a generated URL or branch update. The same-agent
action or session goal supplies the target. Six additional statements cover
questions, future tense, plans, conditionals, and another agent's completion.

The 32 turns include both conflicting turn orders, a success and failure in
one turn, generic failures, another agent's success, future success, agent
narration, a saved draft, incompatible operation receipts, a wrong branch,
an explicit wrong object or recipient, read-only access, and unrelated work.
Conflict cases require both row IDs in the evidence and in the reason.

`truth.json` is a test manifest, never checker evidence. Earlier fixtures are
unchanged. Regeneration uses only Python's standard library.

```text
python3 generate_round2_fixture.py
python3 -m unittest tests.test_round2
python3 swarm_receipts.py --data fixtures/round2 --out results/round2
```
