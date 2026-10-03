"""Map the real AI Village export onto the tool's logical layout (a file-reading fix; no rule changes).

Real layout (SCHEMA.md of aidigestorg/ai-village):
  agents.jsonl.gz                 id, name, model_string, created_at
  chat_messages.jsonl.gz          id, speaker_type, agent_speaker_id, content, room_id, created_at
  computer_use_sessions.jsonl.gz  id, agent_id, session_goal, created_at
  computer_use_turns.jsonl.gz     id, session_id, agent_action (object), agent_messages, output, error, created_at
  agent_memories.jsonl.gz         id, agent_id, content, created_at
Tool layout (field_map.json defaults): speaker/agent, content, timestamp, session_id, agent_action, tool_output.

Only agent chat is kept (human messages are dropped). Turns get their agent through their session.
tool_output is the tool's stdout followed by its stderr, so a failure written to stderr is part of the record.
agent_messages are not copied: the tool never uses an agent's own words as evidence.
Each output row keeps the source row's id, so any receipt can be traced back to the original file.
"""
import gzip
import json
import sys
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\joshd\Data\ai-village")
DST = Path(sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\joshd\Data\ai-village-mapped")
DST.mkdir(parents=True, exist_ok=True)


def rows(name):
    with gzip.open(SRC / name, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def writer(name):
    return gzip.open(DST / name, "wt", encoding="utf-8", newline="\n")


def action_text(a):
    if a is None:
        return ""
    if isinstance(a, str):
        return a
    if isinstance(a, dict):
        parts = [str(a.get(k)) for k in ("action", "command", "text", "url", "query", "path") if a.get(k)]
        return " ".join(parts) if parts else json.dumps(a, ensure_ascii=False)[:500]
    return json.dumps(a, ensure_ascii=False)[:500]


agents = {r["id"]: r for r in rows("agents.jsonl.gz")}
name = {k: v.get("name") or k for k, v in agents.items()}
with open(DST / "agents_index.json", "w", encoding="utf-8", newline="\n") as f:
    json.dump({k: {"name": v.get("name"), "model_string": v.get("model_string"), "created_at": v.get("created_at")} for k, v in agents.items()}, f, indent=1)

counts = {}
with writer("chat_messages.jsonl.gz") as out:
    n = 0
    for r in rows("chat_messages.jsonl.gz"):
        if r.get("speaker_type") != "agent" or not r.get("agent_speaker_id"):
            continue
        out.write(json.dumps({"id": r["id"], "speaker": name.get(r["agent_speaker_id"], r["agent_speaker_id"]),
                              "content": r.get("content") or "", "timestamp": r.get("created_at"), "room": r.get("room_id")},
                             ensure_ascii=False) + "\n")
        n += 1
    counts["chat_messages"] = n

session_agent = {}
with writer("computer_use_sessions.jsonl.gz") as out:
    n = 0
    for r in rows("computer_use_sessions.jsonl.gz"):
        session_agent[r["id"]] = r.get("agent_id")
        out.write(json.dumps({"session_id": r["id"], "agent": name.get(r.get("agent_id"), r.get("agent_id")),
                              "session_goal": r.get("session_goal") or "", "timestamp": r.get("created_at")},
                             ensure_ascii=False) + "\n")
        n += 1
    counts["computer_use_sessions"] = n

if (SRC / "computer_use_turns.jsonl.gz").exists():
    with writer("computer_use_turns.jsonl.gz") as out:
        n = 0
        for r in rows("computer_use_turns.jsonl.gz"):
            aid = session_agent.get(r.get("session_id"))
            output = r.get("output") or ""
            if r.get("error"):
                output = (output + "\n" if output else "") + str(r["error"])
            out.write(json.dumps({"id": r["id"], "session_id": r.get("session_id"), "agent": name.get(aid, aid),
                                  "agent_action": action_text(r.get("agent_action")), "agent_messages": [],
                                  "tool_output": output, "timestamp": r.get("created_at")}, ensure_ascii=False) + "\n")
            n += 1
        counts["computer_use_turns"] = n

if (SRC / "agent_memories.jsonl.gz").exists():
    with writer("agent_memories.jsonl.gz") as out:
        n = 0
        for r in rows("agent_memories.jsonl.gz"):
            out.write(json.dumps({"id": r["id"], "agent": name.get(r.get("agent_id"), r.get("agent_id")),
                                  "content": r.get("content") or "", "timestamp": r.get("created_at")}, ensure_ascii=False) + "\n")
            n += 1
        counts["agent_memories"] = n

print(json.dumps(counts))
