"""Fingerprint everything the gate 3 exam and the dialect test depend on, before either runs.
Writes GATE3-BUNDLE-MANIFEST-SHA256.txt (sha256sum format, absolute paths) beside this script."""
import hashlib
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = Path(r"C:\Users\joshd\Data")
V3 = Path(r"C:\Users\joshd\Workbench\swarm-receipts-v3")


def sha(p, chunk=1 << 22):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


files = sorted(p for p in HERE.rglob("*") if p.is_file() and not p.name.startswith("GATE3-BUNDLE-MANIFEST")
               and p.suffix not in (".ots", ".bak"))
g3 = D / "g3"
files += sorted(p for p in g3.iterdir() if p.is_file() and p.suffix in (".json", ".py", ".md", ".txt"))
files += sorted((g3 / "data").iterdir())
files += [D / "g3-index" / "index-info.json", D / "g3-index" / "turn-index.sqlite"]
files += [D / "dialect" / "spot_claims.py"]
files += [D / n for n in ("g2_sample.json", "g2_labels.pass1.json", "g2_labels.pass2.json", "g2_results.pass1.json",
                          "g2_reliability.json")]
files += [V3 / n for n in ("receipts_model.py", "swarm_receipts.py", "receipts_core.py", "receipts_io.py",
                           "field_map.json", "V3-CHANGES.md")]
head = subprocess.run(["git", "-C", str(V3), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(V3), "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
lines = [f"# swarm-receipts-v3 HEAD {head}; working tree {'CLEAN' if not dirty else 'DIRTY: ' + dirty}"]
for p in files:
    lines.append(f"{sha(p)}  {p}")
out = HERE / "GATE3-BUNDLE-MANIFEST-SHA256.txt"
out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print(lines[0])
print(len(files), "files fingerprinted ->", out)
print("manifest sha256", sha(out))
