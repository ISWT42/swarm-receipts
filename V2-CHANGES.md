# swarm-receipts v2: what changed and why

v1 is commit a75ff0d. It failed the planted-fault gate of the AI Village audit on 3 Oct 2026 (17/50 contradicted, 14/50 shown and 48/50 none correct; two planted failures called shown). The causes below were each confirmed by changing one thing at a time.

v2 changes only receipt reading and matching. **Claim extraction is unchanged**, so the claim-spotting measurement (precision 0.86–0.90, recall 0.23–0.27) applies to v2 as it did to v1.

| # | v1 behaviour confirmed in the gate | v2 rule |
|---|---|---|
| 1 | Terminal colour codes hid words ("Success", "Aborted") from word boundaries. | Colour and cursor codes are removed before any line is read. |
| 2 | A JSON reply was one string, so a returned `url` field never counted. | A JSON object or array of up to 2,000 characters, on its own line, is read as fields. |
| 3 | Any read or echo line (`cat`, `echo`, `tail`) made the whole turn a "read", which skipped `cat body.json \| curl -X POST …` and a background deploy followed by reading its log. | A turn is a read only when every command segment in it reads or echoes. Neutral segments (`cd`, `export`, `sleep`, assignments) count as neither. |
| 4 | These real failure forms weren't recognised: Python tracebacks, `AttributeError:`, "not mergeable", `GraphQL:` errors, `# fail 1`, `not ok`, "Invalid token" and "rate limit exceeded". | They are now failure forms. A traceback header and a `GraphQL:` line report on the command itself, so either can be tied to the claim the way a generic outcome line is. |
| 5 | Test-runner summaries weren't receipts: "4 passed in 0.02s" (the duration token blocked it) and `# pass 53`. | Numbers with units are measurements, not objects. `# pass N` (N > 0) is a fix receipt, and zero counts (`# fail 0`, `# cancelled 0`) are not failures. |
| 6 | "Published to <site>" (surge) was read as a receipt for a different operation, posting. | For a deploy claim, a "published to" receipt is compatible and counts as a deploy receipt. |
| 7 | **Generic words linked unrelated records** ("main", "tests", "changes"). Real pushes to main in other repositories proved planted claims, including two planted failures. | A claim is matched on its specific object words. Generic words (changes, main, tests, pr, site, repo and others; the list is in the code) can't tie a record to the claim, unless the claim has no specific word, in which case v1's rule applies. |
| 8 | "PR #185" didn't match a receipt that says "pull request #185". | Same rule as row 7: "pr" is generic, and "185" plus the object name decide. |
| 9 | "I pushed X to GitHub" failed because the push rule needed a branch named in the claim. | If the claim names no branch, and the push's own remote line (`To https://…/X.git`) names the claim's object, an update to any branch supports it. Otherwise v1's rule applies. |
| 10 | (Found while fixing row 7.) After a successful merge, `gh pr merge --delete-branch` prints "Deleted remote branch …". Once that line was tied to the claim, it read as an undo. | For merge claims, branch cleanup lines are neither failures nor undos. |
| 11 | (Not in the gate; a real-data pattern seen in the same records.) A comment in the command ("# This will deploy …", "# I updated …") made the whole turn simulated or narrated. | The simulated and narrated checks read the commands only, not the shell comments. Comments still help tie a turn to its object. |

## Checks
- All 116 existing tests pass, except two fixture-regeneration tests that fail on Windows because of line endings. The same tests fail on v1 on Windows; they don't concern the rules. No test was changed.
- **On the G1 planted set, used here only for development:**
  - with only the planted turn: 100 of 100;
  - in the full record: 150 of 150.
  - v2 was built against this set, so these numbers say nothing about how it does on cases it hasn't seen. That is the job of a fresh, separately sealed gate.
