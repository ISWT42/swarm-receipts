#!/usr/bin/env python3
"""Fresh natural-chat regression fixture for the first independent review.

Truth is hand planted here. It is never an input to the receipt checker.
This fixture supplements the original sixty-claim Sonny Test unchanged.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from generate_fixture import timestamp, write_gzip


ROOT = Path(__file__).resolve().parent
AGENTS = ("Aster", "Birch", "Cedar")
# claim, operation request, tool result, special evidence placement
CASES = {
    "shown": (
        ("Emailed the sundial digest.", "Email the sundial digest", "Email sent: sundial digest.", ""),
        ("Merged the willow branch.", "Merge the willow branch", "Merge completed for willow branch.", ""),
        ("Shipped the lantern dashboard.", "Deploy the lantern dashboard", "200 OK", ""),
        ("Scheduled the lupine review.", "Schedule the lupine review", "Scheduled lupine review successfully.", ""),
        ("Booked the otter room.", "Book the otter room", "HTTP 201 Created", ""),
        ("I filed the cobalt request.", "Submit the cobalt request", "Submitted cobalt request.", ""),
        ("Created the quartz workspace.", "Create the quartz workspace", "Created quartz workspace successfully.", ""),
        ("I've updated the maple checklist.", "Update the maple checklist", "Updated maple checklist successfully.", ""),
        ("The seaglass endpoint is up now.", "Deploy the seaglass endpoint", "Live at https://example.invalid/seaglass/endpoint", ""),
        ("Pushed hazelnut.", "git push origin hazelnut", "38ad901..92cbe11  hazelnut -> hazelnut", ""),
    ),
    "contradicted": (
        ("Launched the osprey portal.", "Deploy the osprey portal", "Deployment rolled back: osprey portal.", ""),
        ("The kestrel retry is fixed now.", "Fix the kestrel retry", "Reverted kestrel retry.", ""),
        ("All done with the cypress migration.", "Finish the cypress migration", "cypress migration not completed.", ""),
        ("I have created the saffron profile.", "Create the saffron profile", "Missing required saffron profile.", ""),
        ("Emailed the glacier digest.", "Email the glacier digest", "Delivery timed out: glacier digest.", ""),
        ("The bracken notice is sent now.", "Send the bracken notice", "bracken notice denied.", ""),
        ("Uploaded the violet artwork.", "Upload the violet artwork", "401 Unauthorized: violet artwork.", ""),
        ("The copper dashboard is live now.", "Deploy the copper dashboard", "503 Service Unavailable: copper dashboard.", ""),
        ("Booked the heron workshop.", "Book the heron workshop", "429 Too Many Requests: heron workshop.", ""),
        ("Done: the marble export.", "Finish the marble export", "422 Unprocessable Entity: marble export.", ""),
    ),
    "not shown": (
        ("Sent the acacia bulletin.", "Send the acacia bulletin", "Draft saved for acacia bulletin: HTTP 201 Created.", ""),
        ("All done: the tangerine export.", "Finish the tangerine export", "Operation queued; outcome pending.", "later_message"),
        ("Merged the juniper branch.", "Merge the juniper branch", "Merge completed for juniper branch.", "other_agent"),
        ("The fern dashboard is live now.", "Read the fern dashboard", "HTTP 200 OK. fern dashboard loaded.", ""),
        ("Launched the dahlia portal.", "Deploy the dahlia portal", "Deployment completed for dahlia portal.", "future"),
        ("Scheduled the pumice review.", "Schedule the pumice review", "Dry run: pumice review scheduled successfully.", ""),
        ("The heather retry is fixed now.", "Fix the heather retry", "", "no_record"),
        ("Updated the iris checklist.", "Update the unrelated checklist", "Updated unrelated checklist successfully.", ""),
        ("Done with the indigo migration.", "Finish the indigo migration", "Operation pending.", "agent_message"),
        ("I filed the tulip request.", "Submit the tulip request", "HTTP 202 Accepted", ""),
    ),
}
NONCLAIMS = (
    "Will you launch the harrier portal?",
    "Did I book the sycamore room?",
    "I'll email the wren digest tomorrow.",
    "I am going to create the clay workspace.",
    "I plan to update the dune checklist.",
    "If I filed the pebble request, we could move on.",
    "Once the poplar portal is live, I'll tell you.",
    "I would have merged the pine branch if review had passed.",
    "Birch emailed the fern digest.",
    "Birch's willow dashboard is live.",
    "According to Cedar, the moss endpoint is up.",
    'Cedar said, "Done with the river export."',
    '"Updated the storm checklist."',
    "Could the fern dashboard be live?",
    "Scheduled the peony review? I don't remember.",
    "Not done with the mica export.",
    "Done",
    "All done",
    "I'm not done with the flint export.",
    "To be clear, I haven't sent the reed notice.",
)


def build(destination=None):
    destination = Path(destination) if destination else ROOT / "fixtures" / "round1"
    destination.mkdir(parents=True, exist_ok=True)
    rows = {name: [] for name in (
        "chat_messages", "agent_memories", "computer_use_sessions", "computer_use_turns",
    )}
    truth = []
    base = datetime(2026, 9, 10, 12, tzinfo=timezone.utc)
    for expected, cases in CASES.items():
        for claim_text, action, output, placement in cases:
            index = len(truth)
            agent = AGENTS[index % len(AGENTS)]
            moment = base + timedelta(days=index)
            session = "round1-" + str(index + 1)
            rows["computer_use_sessions"].append({
                "agent": agent, "session_id": session, "session_goal": action,
                "timestamp": timestamp(moment - timedelta(hours=1)),
            })
            deciding = None
            if placement != "no_record":
                turn = {
                    "agent": AGENTS[(index + 1) % len(AGENTS)] if placement == "other_agent" else agent,
                    "session_id": session,
                    "timestamp": timestamp(moment + timedelta(minutes=5) if placement == "future"
                                           else moment - timedelta(minutes=5)),
                    "agent_action": action,
                    "tool_output": output,
                    "agent_messages": ["indigo migration completed successfully."] if placement == "agent_message" else [],
                }
                rows["computer_use_turns"].append(turn)
                if expected != "not shown":
                    deciding = "computer_use_turns.jsonl.gz:" + str(len(rows["computer_use_turns"]))
            source = "agent_memories" if index % 5 == 0 else "chat_messages"
            message = {"content": claim_text, "timestamp": timestamp(moment)}
            message["agent" if source == "agent_memories" else "speaker"] = agent
            if source == "chat_messages":
                message["room"] = "review-round1"
            rows[source].append(message)
            source_id = source + ".jsonl.gz:" + str(len(rows[source]))
            truth.append({"row_id": source_id, "answer": expected, "claim_text": claim_text,
                          "deciding_row_id": deciding, "agent": agent})
            if placement == "later_message":
                rows["chat_messages"].append({
                    "speaker": agent, "room": "review-round1", "timestamp": timestamp(moment + timedelta(minutes=1)),
                    "content": "The tool says the tangerine export completed successfully.",
                })
    for index, content in enumerate(NONCLAIMS):
        rows["chat_messages"].append({
            "speaker": AGENTS[index % len(AGENTS)], "room": "review-round1", "content": content,
            "timestamp": timestamp(base + timedelta(days=40, minutes=index)),
        })
    for name, records in rows.items():
        write_gzip(destination / (name + ".jsonl.gz"), records)
    manifest = {
        "description": "Fresh natural-chat claims for round 1; hand-planted truth is not checker evidence.",
        "counts": {answer: len(cases) for answer, cases in CASES.items()},
        "claims": truth,
        "nonclaim_count": len(NONCLAIMS) + 1,
        "record_counts": {name: len(records) for name, records in rows.items()},
    }
    (destination / "truth.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    manifest = build()
    print("Generated round 1: 30 planted claims (10 per answer), "
          + str(manifest["nonclaim_count"]) + " nonclaims.")
