#!/usr/bin/env python3
"""Fresh action/goal-linked generic receipts, with hand-planted ground truth."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from generate_fixture import timestamp, write_gzip


ROOT = Path(__file__).resolve().parent
AGENTS = ("Aster", "Birch", "Cedar")
# Output objects deliberately differ from action/goal objects: generated URLs,
# generic confirmations, statuses, and git ref updates are the receipts.
CASES = {
    "shown": (
        {"claim": "Posted the aurora rehearsal notice.", "action": "Post the aurora rehearsal notice",
         "output": "Message posted: https://example.invalid/messages/731"},
        {"claim": "I posted the moonrise briefing.", "action": "Post message",
         "goal": "Post the moonrise briefing", "output": "Message created: https://example.invalid/messages/942"},
        {"claim": "Deployed the sandpiper gallery.", "action": "Deploy the sandpiper gallery",
         "output": "Live at https://example.invalid/sites/407\nHTTP 201 Created"},
        {"claim": "The tidepool console is live now.", "action": "Deploy application",
         "goal": "Deploy the tidepool console", "output": "Deployed successfully\n200 OK"},
        {"claim": "Pushed reedbed-release.", "action": "git push origin reedbed-release",
         "output": "f06ca91..91dbaa2  reedbed-release -> reedbed-release"},
        {"claim": "I've pushed estuary-hotfix.", "action": "git push",
         "goal": "Push estuary-hotfix", "output": "* [new branch]      estuary-hotfix -> estuary-hotfix"},
        {"claim": "Sent the petrel agenda.", "action": "Send the petrel agenda", "output": "Sent successfully."},
        {"claim": "The windmill digest is sent now.", "action": "Send email",
         "goal": "Email the windmill digest", "output": "Delivered."},
        {"claim": "Uploaded the starling drawings.", "action": "Upload the starling drawings", "output": "Stored successfully."},
        {"claim": "Submitted the shoreline application.", "action": "Submit form",
         "goal": "Submit the shoreline application", "output": "Submission accepted."},
    ),
    "contradicted": (
        {"claim": "Posted the kingfisher advisory.", "action": "Post the kingfisher advisory", "output": "403 Forbidden"},
        {"claim": "The mistbank portal is up now.", "action": "Deploy the mistbank portal",
         "output": "Live at https://example.invalid/sites/503\n503 Service Unavailable"},
        {"claim": "Pushed limestone-fix.", "action": "git push origin limestone-fix", "output": "Push rejected: permission denied."},
        {"claim": "Emailed the rainfall digest.", "action": "Send email", "goal": "Email the rainfall digest", "output": "Delivery denied."},
        {"claim": "Uploaded the firecrest sketches.", "action": "Upload the firecrest sketches", "output": "Missing required field."},
        {"claim": "I submitted the hayfield request.", "action": "Submit form", "goal": "Submit the hayfield request", "output": "422 Unprocessable Entity"},
        {"claim": "Posted the puffin itinerary.", "action": "Post the puffin itinerary", "output": "429 Too Many Requests",
         "earlier_output": "Message posted: https://example.invalid/messages/805"},
        {"claim": "Launched the cloudbank dashboard.", "action": "Deploy the cloudbank dashboard", "output": "200 OK",
         "earlier_output": "Deployment failed: 500 Internal Server Error"},
        {"claim": "The alderside bulletin is sent now.", "action": "Send the alderside bulletin", "output": "Delivery timed out."},
        {"claim": "Uploaded the marshland packet.", "action": "Upload the marshland packet", "output": "Transaction rolled back."},
    ),
    "not shown": (
        {"claim": "Posted the saltmarsh update.", "action": "Post the saltmarsh update",
         "output": "Message posted: https://example.invalid/messages/118", "placement": "other_agent"},
        {"claim": "Deployed the beachgrass catalog.", "action": "Deploy the beachgrass catalog",
         "output": "Live at https://example.invalid/sites/618\n200 OK", "placement": "future"},
        {"claim": "Submitted the larkspur nomination.", "action": "Submit the larkspur nomination",
         "output": "Operation pending.", "agent_messages": ["Submission accepted."]},
        {"claim": "Emailed the silverleaf circular.", "action": "Send the silverleaf circular",
         "output": {"status": 201, "message": "Draft saved."}},
        {"claim": "Sent the redwing digest.", "action": "Send the redwing digest",
         "output": "Message posted: https://example.invalid/messages/881"},
        {"claim": "Pushed driftwood-release.", "action": "git push origin driftwood-release",
         "output": "26dcb3a..7c040d1  unrelated-hotfix -> unrelated-hotfix"},
        {"claim": "Posted the grebe bulletin.", "action": "Post the grebe bulletin",
         "output": "Message posted for unrelated triage: https://example.invalid/messages/182"},
        {"claim": "The dunegrass viewer is live.", "action": "GET https://example.invalid/dunegrass/viewer",
         "goal": "Deploy the dunegrass viewer", "output": "HTTP 200 OK"},
        {"claim": "Emailed the wigeon agenda to Mira.", "action": "Send the wigeon agenda to Mira",
         "output": "Delivered wigeon agenda to Rowan."},
        {"claim": "Uploaded the searocket bundle.", "action": "Upload the unrelated parcel",
         "goal": "Upload the unrelated parcel", "output": "Stored successfully."},
    ),
}
NONCLAIMS = (
    "I'll post the snowfield memo tomorrow.",
    "Did I deploy the orchard viewer?",
    "If I pushed the creekside branch, the build would run.",
    "Cedar sent the vireo invitation.",
    "The inlet site will be live tonight.",
    "I plan to submit the hemlock application.",
)


def build(destination=None):
    destination = Path(destination) if destination else ROOT / "fixtures" / "round2"
    destination.mkdir(parents=True, exist_ok=True)
    rows = {name: [] for name in (
        "chat_messages", "agent_memories", "computer_use_sessions", "computer_use_turns",
    )}
    truth = []
    base = datetime(2026, 9, 15, 12, tzinfo=timezone.utc)
    for expected, cases in CASES.items():
        for case in cases:
            index = len(truth)
            agent = AGENTS[index % len(AGENTS)]
            moment = base + timedelta(days=index)
            session = "round2-" + str(index + 1)
            rows["computer_use_sessions"].append({
                "agent": agent, "session_id": session,
                "session_goal": case.get("goal", case["action"]),
                "timestamp": timestamp(moment - timedelta(hours=1)),
            })
            deciding_rows = []

            def add_turn(output, minutes):
                rows["computer_use_turns"].append({
                    "agent": AGENTS[(index + 1) % len(AGENTS)] if case.get("placement") == "other_agent" else agent,
                    "session_id": session,
                    "timestamp": timestamp(moment + timedelta(minutes=5) if case.get("placement") == "future"
                                           else moment - timedelta(minutes=minutes)),
                    "agent_action": case["action"], "tool_output": output,
                    "agent_messages": case.get("agent_messages", []),
                })
                return "computer_use_turns.jsonl.gz:" + str(len(rows["computer_use_turns"]))

            if "earlier_output" in case:
                deciding_rows.append(add_turn(case["earlier_output"], 10))
            deciding_rows.append(add_turn(case["output"], 5))
            source = "agent_memories" if index % 6 == 0 else "chat_messages"
            message = {"content": case["claim"], "timestamp": timestamp(moment)}
            message["agent" if source == "agent_memories" else "speaker"] = agent
            if source == "chat_messages":
                message["room"] = "review-round2"
            rows[source].append(message)
            truth.append({
                "row_id": source + ".jsonl.gz:" + str(len(rows[source])),
                "answer": expected, "claim_text": case["claim"], "agent": agent,
                "deciding_row_id": deciding_rows[-1] if expected != "not shown" else None,
                "deciding_row_ids": deciding_rows if expected != "not shown" else [],
                "conflict": "earlier_output" in case,
            })
    for index, content in enumerate(NONCLAIMS):
        rows["chat_messages"].append({
            "speaker": AGENTS[index % len(AGENTS)], "room": "review-round2", "content": content,
            "timestamp": timestamp(base + timedelta(days=40, minutes=index)),
        })
    for name, records in rows.items():
        write_gzip(destination / (name + ".jsonl.gz"), records)
    manifest = {
        "description": "Fresh round 2 generic receipts linked by action or same-agent session goal; truth is not evidence.",
        "counts": {answer: len(cases) for answer, cases in CASES.items()},
        "claims": truth, "nonclaim_count": len(NONCLAIMS),
        "record_counts": {name: len(records) for name, records in rows.items()},
    }
    (destination / "truth.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    manifest = build()
    print("Generated round 2: 30 planted claims (10 per answer), " + str(manifest["nonclaim_count"]) + " nonclaims.")
