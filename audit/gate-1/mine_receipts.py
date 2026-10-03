"""Collect real action/output pairs per operation, so planted receipts copy the data's own formats."""
import gzip, json, re, random
P = {
 "git_push": r"\bgit push\b",
 "gh_issue_create": r"\bgh issue create\b",
 "gh_pr_merge": r"\bgh pr merge\b",
 "gh_release_upload": r"\bgh release (?:create|upload)\b",
 "site_deploy": r"\b(?:netlify deploy|wrangler (?:pages )?deploy|vercel --prod|surge )",
 "curl_post": r"curl\b.*(?:-X\s*POST|--request POST)",
 "gh_api_post": r"\bgh api\b.*(?:-X POST|--method POST)",
 "email_send": r"(?i)send_email|sendmail|smtplib|gmail.*send|mail -s",
}
R = {k: re.compile(v) for k, v in P.items()}
keep = {k: [] for k in P}; seen = {k: 0 for k in P}
rng = random.Random(20261003)
with gzip.open(r"C:\Users\joshd\Data\ai-village-mapped\computer_use_turns.jsonl.gz", "rt", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line); a = r.get("agent_action") or ""; o = r.get("tool_output") or ""
        if not o or len(a) > 500 or len(o) > 700: continue
        for k, rx in R.items():
            if rx.search(a):
                seen[k] += 1
                # reservoir sample of 40 per operation
                ex = {"id": r["id"], "agent": r["agent"], "t": r["timestamp"], "action": a, "output": o}
                if len(keep[k]) < 40: keep[k].append(ex)
                else:
                    j = rng.randrange(seen[k])
                    if j < 40: keep[k][j] = ex
                break
json.dump({"seen": seen, "examples": keep}, open(r"C:\Users\joshd\Data\g1\real_receipts.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(seen)
