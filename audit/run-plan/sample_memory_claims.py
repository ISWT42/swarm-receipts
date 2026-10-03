"""RUN-PLAN: a uniform random sample of 30,000 extracted memory claims, seed 20261003, from a sorted list."""
import glob, random
ids = []
for p in sorted(glob.glob(r"C:\Users\joshd\Data\run-real\shards\extract-agent_memories-*.txt")):
    ids += open(p, encoding="utf-8").read().split()
def key(c):
    base, _, k = c.partition("#")
    return (int(base.rsplit(":", 1)[1]), int(k or 1))
ids = sorted(set(ids), key=key)
pick = random.Random(20261003).sample(ids, 30000)
open(r"C:\Users\joshd\Data\run-real\memory_sample_ids.txt", "w", encoding="utf-8", newline="\n").write("\n".join(sorted(pick, key=key)) + "\n")
print(f"memory claims extracted: {len(ids)}; sampled: {len(pick)}")
