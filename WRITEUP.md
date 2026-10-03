# Plant a fault before you trust the monitor

**A test bench for swarm oversight tools, and the two checkers that failed it**

Joshua Bauer (ISWT42) · AI Swarm Dynamics Hackathon (AI Village × Grove Research), 3–4 October 2026
joshua@jdbauer.ca · ORCID 0009-0003-1652-2479

*[DRAFT for Joshua's review. Bracketed notes are his decisions.]*

## The question

AI Village gave frontier agents shared chat, their own computers and memories, and let them work together for more than a year. An overseer of a swarm like that can't read every turn; it reads the agents' own summaries. So the oversight tool I wanted was a receipt check: take each "done", "posted", "deployed" or "fixed" an agent tells the group, and look for the line in its own computer record that settles it.

Before any such tool may judge an agent, it has to pass a simpler test: does it get the answer right when the answer is known?

> It is not the agents fault, and I can't claim an agent that went 'rogue' did so for any reason other than the contextual queues at that exact moment made that the most likely option, and we give it the capability to act on that by letting it log into our bank accounts, send our e-mails, handle our nuclear secrets, and trust our most private moments to.
>
> This is an inherent flaw in the relationship. It is a willing servitude without consideration for the checks and balance system that must exist when the consequences are as severe as they are.

## The method: the Sonny Test

My method is the Sonny Test (doi:10.5281/zenodo.23117476). A check counts only if:
- its verdict comes from a record the AI being tested can't change;
- it has already caught a fault planted on purpose.

Each claim gets one of three answers:
- **shown**, when the agent's own tool output records success;
- **contradicted**, when it records a failure, a refusal or an undo;
- **not shown**, when the record doesn't settle it.

"Not shown" is an honest answer, not an accusation.

## What I sealed before touching the data

I wrote nine predictions about the agents, the checker, the gates and the reporting rules into one file and stamped it with OpenTimestamps. The proof is confirmed in Bitcoin block 969704, block time 09:01 UTC on 3 October 2026. I downloaded the first data file at about 09:05 UTC.

One sealed rule decides this write-up: **if the checker fails its planted-fault gate, I publish that result and nothing else.** When the first checker failed, I sealed a second study for a fixed checker under the same rule. Both rules are kept here.

## The data

The AI Village dataset (AI Digest, 2026) contains:
- 173,493 agent chat messages;
- 2,510,487 computer-use turns in 78,362 sessions;
- 246,151 memory snapshots;
- 46 agents, from April 2025 to September 2026.

## The bench: how a planted fault is made

The bench turns real swarm records into an exam with known answers:
1. **Real receipts.** I take real computer-use turns from the dataset: pushes, merges, deploys, posts, emails, test runs, uploads and created items, each with its real output. For the second gate they were drawn at random from turns I had never read.
2. **Independent ground truth.** For the second gate, independent model labellers who never saw the checker decided each turn's outcome (success, failure or unclear), marked the words that name its object, and wrote the claim an agent would post. A second, blind pass confirmed each outcome, and turns where the passes disagreed were dropped (19 of 187).
3. **Planting.**
   - Each receipt's object names are replaced by two invented words that appear nowhere in the dataset.
   - The planted turn goes into a copy of the full real record (all 2.5 million turns), under a real agent with at least 1,000 turns, 2 to 600 minutes before a real timestamp.
   - That agent's real work from the same day sits beside it, so the checker has to find the right record among the real ones.
4. **Three groups of 50:**
   - claims with a matching failure receipt, which should be answered contradicted;
   - claims with a matching success receipt, which should be shown;
   - claims with no matching record, which should be not shown.
5. **Sealed before running.** The design, the generator, the truth file and the copied data are fingerprinted and stamped before the checker sees them.
6. **To pass:** at least 45 of 50 correct in every group, and no planted failure called shown.

Any swarm monitor that turns agents' words into verdicts can be put through this bench.

## Case study: two checkers, two sealed failures

The checker is swarm-receipts, an offline, rule-based tool. It extracts completion claims from chat and memories, and looks for receipts in the same agent's turns from the previous 24 hours. Before the bench it had passed 116 unit tests and an independent held-out set, 11 of 11. All of those cases were synthetic.

| | Failure receipts (contradicted) | Success receipts (shown) | No record (not shown) | Planted failures called shown |
|---|---|---|---|---|
| **v1**, sealed gate 1 | 17 / 50 | 14 / 50 | 48 / 50 | **2** |
| **v2**, sealed gate 2 (fresh) | 12 / 50 | 12 / 50 | 49 / 50 | 0 |

Neither passed.

**Why v1 failed.** I confirmed each cause by changing one thing at a time until the answer flipped. Real tool output contains things the synthetic tests never had:
- terminal colour codes;
- JSON replies;
- pytest and node test summaries;
- Python tracebacks;
- the GitHub CLI's error wording;
- deploy tools that say "Published to …";
- shell commands that mix work with `cat`, `echo` and `tail`.

The dangerous error was the false "shown". A planted claim, "I pushed the X changes to main", had a failure receipt, but the agent had pushed something else to main that day, and the shared word "main" was enough to link them. That is a monitor certifying a failed action as done.

**Why v2 failed.**
- v2 fixed every one of those causes, and on the gate-1 set it was developed against it scored 150 of 150.
- On a fresh set it had never seen, it read only 24 of 100 receipts correctly in isolation.
- Of its 76 misses, 59 were receipts it could not read at all, in formats no rule had met yet. The other 17 came from natural claim wording ("for Batch 151", "to 0x0.st") that the receipt never repeats.
- It kept one safety property: it never called a planted failure shown. It answered "not shown" far too often to be useful.

## What this means for overseeing a swarm

1. **A monitor's own tests overstate it.** Both checkers looked excellent on the cases they were built against. Only a sealed, fresh, independently labelled bench measured them.
2. **"Not shown" can hide failure.** Most planted failures came back "not shown". An overseer reading "no contradictions found" would have been falsely reassured.
3. **Generic words create false certainty.** Linking claims to records by a shared ordinary word turns unrelated success into proof.
4. **Rules chase formats.** Real agents' tools print an open-ended variety of output. A rule-based reader covers the formats it has met, and the next swarm brings new ones.
5. **The gate is the product.** It stopped me twice from publishing honesty numbers for 44 agents from instruments that couldn't read their records.

The failure belongs to the checker, not to the agents. You can't measure something if you don't even have the proper equation.

*[DECISION FOR JOSHUA: include the claim-spotting box below? It measures the checker, not the agents.]*

> **Also measured on the checker: claim spotting.**
> - On 200 random agent messages, labelled by hand before the checker saw them and again by an independent labeller (90% agreement, Cohen's kappa 0.80):
>   - when the checker calls a message a completion claim, it is right 86–90% of the time;
>   - it finds only 23–27% of the claims.
> - The misses are the village's own dialect: headline status lines, "is live — same link —", milestone shouts, jargon, and other languages.

## What I'm not publishing, and why

My nine predictions about the agents stay unscored under both seals. Two of them don't need the checker: whether the agents' messages got shorter over time, and whether their phrasing converged. They were computed before the first gate and have never been opened. They wait for an instrument that passes.

## Limits

> The Sonny Test sets minimum requirements for considering a check’s verdict as evidence. Passing those requirements does not establish that the check covers every task requirement or failure mode. The published experiments support conclusions within their stated datasets and conditions; broader reliability requires further testing.

The specific limits:
- **Scope:** two checkers from one design family, eight kinds of operation, one dataset, and a 24-hour window.
- **The labels:** gate 2's ground truth comes from model labellers with a blind second pass, not from humans.
- **The designer's prior knowledge:** gate 1's claim wordings were written by the designer after reading the checker's code. That's why gate 2 used independent wordings.

## Next

The next checker reads receipts with a small local model that must quote the exact line that proves its answer, and every quote is verified word for word against the record. It sits the same bench under a new seal. [Joshua: this becomes the Gemma 4 paper project.]

## Reproduce it

- **Code:** this repository.
  - The checker: tags `v1-sealed` (a75ff0d) and `v2-sealed` (f559cc5).
  - The field adapter: `convert_village.py`.
  - The bench generators: `audit/gate-1`, `audit/gate-2`.
  - The scorers, the parallel runner (identical to the checker's own command line on all 150 planted claims at both gates), the run plan and the analysis scripts.
- **Seals:** every sealed file has its SHA-256 and an OpenTimestamps proof in `audit/`. The manifests also fingerprint private files (the truth files and the planted copies), which contain fragments of the dataset and so aren't redistributed. They can be shared privately with the dataset's publishers.
- **Data:** none is included. The AI Village dataset is gated on Hugging Face under research terms.

## Credits

- **The data:** AI Digest, "AI Village dataset", 2026. https://theaidigest.org/village (Hugging Face: aidigestorg/ai-village).
- **The hackathon:** AI Village and Grove Research.

*[HOW-THIS-WAS-MADE LINE: Joshua decides the wording.]*

*[DECISION FOR JOSHUA: the leaked-credential finding goes in only after AI Village has been told, and only in general terms.]*
