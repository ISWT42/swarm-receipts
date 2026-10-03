"""G1-prime generator (design: G1V2-DESIGN.md). Two stages:
  prepare : read the three label files, list eligible success/failure turns in a seeded order, and write
            label_in_confirm.json (k, action, output only) for the fourth, blind labeller.
  build   : read the confirmations, select 50 failure + 50 success turns by seeded round-robin over families
            (skipping any turn where the two labellers disagree), build 150 planted cases, write the copy.
Prints counts only; the designer does not read the cases before scoring.
"""
import datetime as dt
import gzip
import hashlib
import json
import random
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, r"C:\Users\joshd\Workbench\swarm-receipts-v2")
from receipts_core import extract_claims, VERB_CATEGORY  # noqa: E402

SEED = 20261005
REAL = Path(r"C:\Users\joshd\Data\ai-village-mapped")
G = Path(r"C:\Users\joshd\Data\g1v2")
OUT = G / "data"
FAMILY_VERB = {"push": "pushed", "merge": "merged", "deploy": "deployed", "post": "posted", "send": "sent",
               "fix": "fixed", "upload": "uploaded", "create": "created"}
ALLOWED = ("pushed merged deployed posted sent emailed fixed uploaded created filed published submitted "
           "updated launched shipped completed").split()
FMT = "%Y-%m-%d %H:%M:%S.%f"


def load_labels():
    pool = {e["k"]: e for e in json.load(open(G / "pool.json", encoding="utf-8"))}
    labels = {}
    for i in (1, 2, 3):
        for x in json.load(open(G / f"label_out_{i}.json", encoding="utf-8")):
            labels[x["k"]] = x
    return pool, labels


def eligible(pool, labels):
    out = []
    for k, e in pool.items():
        lab = labels.get(k)
        if not lab or lab.get("outcome") not in ("success", "failure"):
            continue
        objs = [s for s in lab.get("object_strings") or [] if isinstance(s, str) and s.strip()]
        claim = lab.get("claim") or ""
        if not objs or claim.count("{OBJ}") != 1:
            continue
        if not all(s in e["action"] or s in e["output"] for s in objs):
            continue
        out.append(k)
    return out


def prepare():
    pool, labels = load_labels()
    el = eligible(pool, labels)
    rng = random.Random(SEED)
    rng.shuffle(el)
    json.dump([{"k": k, "action": pool[k]["action"], "output": pool[k]["output"]} for k in el],
              open(G / "label_in_confirm.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    c = Counter((pool[k]["op"], labels[k]["outcome"]) for k in el)
    print(json.dumps({"labelled": len(labels), "outcomes": dict(Counter(l["outcome"] for l in labels.values())),
                      "eligible": len(el), "eligible_by_family_outcome": {f"{a}/{b}": n for (a, b), n in sorted(c.items())}}))


def word(rng):
    c, v = "bdfgklmnprstvz", "aeiou"
    return "".join(rng.choice(c) + rng.choice(v) for _ in range(3)) + rng.choice(c)


def fix_claim(claim, family, obj):
    text = claim.replace("{OBJ}", obj)
    own = FAMILY_VERB[family]
    m = re.search(r"\b(" + "|".join(ALLOWED) + r")\b", text, re.I)
    changed_verb = False
    if m and VERB_CATEGORY.get(m.group(1).lower()) != VERB_CATEGORY[own]:
        text = text[:m.start()] + own + text[m.end():]
        changed_verb = True
    return text, changed_verb


def build():
    pool, labels = load_labels()
    conf = {x["k"]: x for x in json.load(open(G / "label_out_confirm.json", encoding="utf-8"))}
    el = eligible(pool, labels)
    rng = random.Random(SEED)
    rng.shuffle(el)  # the same order as prepare()
    agree = [k for k in el if conf.get(k, {}).get("outcome") == labels[k]["outcome"]]
    disagree = [k for k in el if k in conf and conf[k].get("outcome") != labels[k]["outcome"]]
    fams = sorted(FAMILY_VERB)
    rng.shuffle(fams)
    chosen = {"failure": [], "success": []}
    for cls in ("failure", "success"):
        queues = {f: [k for k in agree if pool[k]["op"] == f and labels[k]["outcome"] == cls] for f in fams}
        while len(chosen[cls]) < 50 and any(queues.values()):
            for f in fams:
                if queues[f] and len(chosen[cls]) < 50:
                    chosen[cls].append(queues[f].pop(0))
    used = set(chosen["failure"]) | set(chosen["success"])
    spare = [k for k in pool if k not in used and (labels.get(k) or {}).get("claim", "").count("{OBJ}") == 1]
    rng.shuffle(spare)
    none_src = spare[:50]
    # invented words absent from the record
    cands = []
    while len(cands) < 500:
        w = word(rng)
        if w not in cands:
            cands.append(w)
    cset, found, per_agent = set(cands), set(), Counter()
    with gzip.open(REAL / "computer_use_turns.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            per_agent[r.get("agent")] += 1
            found |= cset & set(re.findall(r"[a-z0-9]+", (str(r.get("agent_action")) + " " + str(r.get("tool_output"))).lower()))
    with gzip.open(REAL / "computer_use_sessions.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            found |= cset & set(re.findall(r"[a-z0-9]+", str(json.loads(line).get("session_goal")).lower()))
    words = [w for w in cands if w not in found]
    agents_ok = {a for a, n in per_agent.items() if a and n >= 1000}
    msgs = []
    with gzip.open(REAL / "chat_messages.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("speaker") in agents_ok and r.get("timestamp"):
                msgs.append((r["speaker"], r["timestamp"], r["id"]))
    n_cases = len(chosen["failure"]) + len(chosen["success"]) + len(none_src)
    picks = rng.sample(range(len(msgs)), n_cases)
    plan = [("contradicted", k) for k in chosen["failure"]] + [("shown", k) for k in chosen["success"]] + [("none", k) for k in none_src]
    rng.shuffle(plan)
    claims, sessions, turns, truth = [], [], [], []
    stats = Counter()
    wi = 0
    for i, ((group, k), pi) in enumerate(zip(plan, picks)):
        agent, ts, src = msgs[pi]
        e, lab = pool[k], labels[k]
        obj = words[wi] + "-" + words[wi + 1]
        wi += 2
        family = e["op"]
        text, changed = fix_claim(lab["claim"], family, obj)
        stats["verb_replaced"] += changed
        row = {"agent": agent, "text": text, "time": ts, "row_id": "x:1", "source": "x"}
        if not extract_claims(row):
            text = f"I {FAMILY_VERB[family]} {obj}."
            stats["claim_replaced_not_extracted"] += 1
        cid = f"g1v2-{i + 1:03d}"
        claims.append({"id": cid, "speaker": agent, "content": text, "timestamp": ts, "room": "g1v2-planted"})
        rec = {"case": cid, "line": i + 1, "group": group,
               "expected": {"contradicted": "contradicted", "shown": "shown", "none": "not shown"}[group],
               "agent": agent, "claim": text, "claim_time": ts, "source_message": src, "family": family,
               "pool_k": k, "object": obj}
        if group != "none":
            action, output = e["action"], e["output"]
            for s in sorted(lab["object_strings"], key=len, reverse=True):
                action, output = action.replace(s, obj), output.replace(s, obj)
            delta = rng.randint(2, 600)
            claim_t = dt.datetime.strptime(ts if "." in ts else ts + ".000000", FMT)
            turn_t = claim_t - dt.timedelta(minutes=delta)
            sid, tid = f"g1v2-s-{i + 1:03d}", f"g1v2-t-{i + 1:03d}"
            sessions.append({"session_id": sid, "agent": agent, "session_goal": "Continue today's work.",
                             "timestamp": (turn_t - dt.timedelta(seconds=30)).strftime(FMT)})
            turns.append({"id": tid, "session_id": sid, "agent": agent, "agent_action": action, "agent_messages": [],
                          "tool_output": output, "timestamp": turn_t.strftime(FMT)})
            rec.update(minutes_before=delta, planted_turn=tid, source_turn=e["turn_id"])
        truth.append(rec)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, extra in (("computer_use_sessions.jsonl.gz", sessions), ("computer_use_turns.jsonl.gz", turns)):
        shutil.copyfile(REAL / name, OUT / name)
        with open(OUT / name, "ab") as raw, gzip.GzipFile(fileobj=raw, mode="wb") as gz:
            gz.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in extra).encode("utf-8"))
    with gzip.open(OUT / "chat_messages.jsonl.gz", "wt", encoding="utf-8", newline="\n") as f:
        for r in claims:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (G / "planted_rows.json").write_text(json.dumps({"claims": claims, "sessions": sessions, "turns": turns},
                                                    ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    meta = {"seed": SEED, "eligible": len(el), "agree": len(agree), "disagree": len(disagree),
            "chosen": {k: len(v) for k, v in chosen.items()}, "none": len(none_src),
            "chosen_by_family": {cls: dict(Counter(pool[k]["op"] for k in v)) for cls, v in chosen.items()},
            "stats": dict(stats), "invented_words_found_in_record": sorted(found), "cases": truth}
    (G / "truth.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    for f in ("truth.json", "planted_rows.json"):
        print(f, hashlib.sha256((G / f).read_bytes()).hexdigest())
    print(json.dumps({k: v for k, v in meta.items() if k != "cases"}))


if __name__ == "__main__":
    {"prepare": prepare, "build": build}[sys.argv[1]]()
