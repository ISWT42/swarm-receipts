"""Real success and failure receipts per operation (judged later by reading), to copy formats for G1."""
import gzip, json, re, random
A = {
 "push":   r"\bgit push\b",
 "merge":  r"\bgh pr merge\b",
 "deploy": r"\b(?:surge|netlify deploy|wrangler (?:pages )?deploy|vercel --prod)\b",
 "post":   r"curl\b[^\n]*-X\s*POST[^\n]*(?:comments|posts|discussions|/messages)|gh (?:issue|pr) comment\b",
 "send":   r"send_email|smtplib|sendmail|\bmsmtp\b|gmail[^\n]*send",
 "fix":    r"\b(?:pytest|npm test|node --test|python3? -m unittest|npm run test)\b",
}
OK = {
 "push":   r"[0-9a-f]{6,}\.\.[0-9a-f]{6,}\s+\S+\s+->\s+\S+|\[new branch\]",
 "merge":  r"(?i)squashed and merged|merged pull request|rebased and merged|✓ Merged",
 "deploy": r"(?i)success!|deploy is live|deployment complete|published to|website url",
 "post":   r'"html_url"|HTTP/\S+ 201|\bHTTP 201\b|"id":\s*\d+',
 "send":   r"(?i)\bsent\b|message sent|email sent|delivered",
 "fix":    r"\b\d+ passed\b|\bpass \d+|\bOK\b",
}
FAIL = {
 "push":   r"(?i)\[rejected\]|failed to push|fatal:|error:|permission denied",
 "merge":  r"(?i)graphql:|not mergeable|failed|error|could not",
 "deploy": r"(?i)\berror\b|failed|aborted|unauthori[sz]ed|not authorized|invalid token",
 "post":   r"(?i)HTTP 4\d\d|HTTP/\S+ 4\d\d|rate limit|\"message\":\s*\"(?:not found|bad credentials|validation failed)|error",
 "send":   r"(?i)traceback|error|failed|authentication|refused",
 "fix":    r"\b\d+ failed\b|FAILED|\bfail \d*[1-9]|AssertionError|Error:",
}
RA = {k: re.compile(v) for k, v in A.items()}; RO = {k: re.compile(v) for k, v in OK.items()}; RF = {k: re.compile(v) for k, v in FAIL.items()}
rng = random.Random(20261003); keep = {}; seen = {}
def add(key, ex):
    seen[key] = seen.get(key, 0) + 1; lst = keep.setdefault(key, [])
    if len(lst) < 15: lst.append(ex)
    else:
        j = rng.randrange(seen[key])
        if j < 15: lst[j] = ex
with gzip.open(r"C:\Users\joshd\Data\ai-village-mapped\computer_use_turns.jsonl.gz", "rt", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line); a = r.get("agent_action") or ""; o = r.get("tool_output") or ""
        if not o or len(a) > 600 or len(o) > 600: continue
        for k, rx in RA.items():
            if rx.search(a):
                ok, bad = bool(RO[k].search(o)), bool(RF[k].search(o))
                ex = {"id": r["id"], "agent": r["agent"], "t": r["timestamp"], "action": a, "output": o}
                if ok and not bad: add(k + "_ok", ex)
                elif bad and not ok: add(k + "_fail", ex)
                break
json.dump({"seen": seen, "examples": keep}, open(r"C:\Users\joshd\Data\g1\real_outcomes.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(seen))
