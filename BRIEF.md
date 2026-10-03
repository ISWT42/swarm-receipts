# swarm-receipts: job brief

For: Sol (GPT-6.1 in Codex), in this box. Budget: up to 3 hours. Owner: Joshua Bauer. Written 3 October 2026.
This is a hackathon entry (the AI Swarm Dynamics Hackathon, due Sunday 4 October, 5:00 pm PT). Speed matters, and so does being right.

## The owner's instructions for this job only
- Work only in `~/work/swarm-receipts`. Read anything in it; write only inside it. Create the repository there (`git init` is allowed; commit as `git -c user.name=ISWT42 -c user.email=iswt42@local commit`, with no trailers and never `--no-verify`). Do not push.
- Offline: no network and no package installs. Python 3 standard library only.
- Never read, print or store keys, tokens or credentials, and never open a file whose name contains .env.
- No browsers or windowed programs, headless ones included.
- If you meet anything marked confidential, skip it and never search for it.
- When you finish, stop and write `REPORT.md`, ending with a section called Doubts considered and dismissed.

## What to build
A command-line tool that checks what agents in a multi-agent group SAID they did against the record of what they DID, and gives one of three answers for each claim:
- **shown**: a record line shows the claimed action succeeded (quote that line);
- **contradicted**: a record line shows it failed, errored, was refused or was undone (quote that line);
- **not shown**: nothing in the record shows the outcome either way. This is a complete, honest answer, not an error.

The data is the AI Village dataset (frontier-model agents living together for over a year: group chat, their own computers, memories). We don't have it yet; access is pending. Build against its published file layout, below, and make field names configurable, because the real data may differ.

## The published layout (from the dataset card; treat as provisional)
Gzipped JSON Lines files:
- `chat_messages.jsonl.gz`: fields `room`, `speaker`, `content`, `timestamp`.
- `agent_memories.jsonl.gz`: long-term memories agents wrote during consolidation (assume fields like `agent`, `content`, `timestamp`).
- `computer_use_sessions.jsonl.gz`: a session per agent with a `session_goal` and an agent identifier.
- `computer_use_turns.jsonl.gz`: per turn, `agent_action`, `agent_messages`, the tool output, and `screenshot_metadata` (screenshots are referenced, not inlined). Assume a session id, an agent identifier and a timestamp exist.
- `events.jsonl.gz`: a timeline with `actionType` (for example AGENT_TALK, START_USING_COMPUTER), a `data` object and `event_index`.
- Also `summaries.jsonl.gz` and `agent_goals.jsonl.gz` (optional inputs).

## Requirements
1. **A field map.** A small JSON config maps our logical fields (agent, text, time, session, action, output) to each file's real field names, with defaults from the layout above. A `--inspect` mode prints the keys and three sample rows (text truncated to 200 characters) of each file it finds, so we can fix the map in minutes when real data arrives.
2. **Claim extraction.** Find completion claims in chat messages and in memories: an agent saying it did, finished, sent, published, fixed, deployed, posted, saved or submitted something. Keep it transparent: rules and patterns, with each claim's source row and the matched phrase. Skip questions, plans, future tense, other agents' work, and reported speech where you can tell.
3. **Evidence linking.** For each claim, gather the same agent's computer-use turns in a window before the claim (default: the 24 hours before it, configurable), plus any turns in sessions whose goal shares key words with the claim.
4. **Classification.** Classify from the turns' action and tool output only, never from the claim itself. Contradicted needs a specific failure signal tied to the claimed action (an error, a refusal, a failed upload, a 4xx or 5xx status, "permission denied", "not found", a rollback, and so on). Shown needs a specific success signal tied to it (a confirmation, a URL of the posted item, "sent", a 2xx status, and so on). Everything else is not shown. Every shown or contradicted answer quotes the deciding line and its row id.
5. **Planted faults first (the Sonny Test).** A checker that never says "fail" proves nothing. Ship a synthetic fixture in `fixtures/`: about 3 agents, 60 claims and a few hundred turns, in the layout above, with planted claims whose truth you know: 20 shown, 20 contradicted and 20 not shown, written with varied wording. A test (`python -m unittest`) runs the tool on the fixture and must classify at least 18 of 20 in each group correctly, and must never call a planted contradicted claim shown. Report the confusion table.
6. **Outputs.** Write `results/claims.csv` (one row per claim: agent, time, source, claim text truncated to 300 characters, answer, the deciding line, the row ids). Also write `results/summary.md` (counts per agent and per answer, with a few examples of each, quoted with their receipts). Also optionally write a `results/memory_check.md` that checks memory claims against the record in the same way.
7. **Scale.** Stream the gzipped files; do not load 1 million turns into memory at once. Index turns by agent and time. Give a `--limit` option for quick runs.
8. **README.md:** what it does, why three answers, how to run it on the fixture and on the real data, the limits, and a line saying the code was written with AI assistance (Sol, GPT-6.1 in Codex) under Joshua Bauer's direction. Plain words.

## What not to do
- Don't use any model or network service in the tool; it must run offline and be explainable line by line.
- Don't treat an agent's own later message as evidence for its earlier claim. Only computer-use turns and tool output count as the record.
- Don't overclaim. If the rules can't decide, the answer is not shown.

## Done means
- `python -m unittest` passes on the fixture, with the confusion table in `REPORT.md`.
- `python swarm_receipts.py --data fixtures --out results` produces the three outputs.
- `--inspect` works on the fixture.
- One commit or a few clean commits, as ISWT42, with no trailers.
