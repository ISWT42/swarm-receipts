"""Gate 3 label inputs: the three files the blind first-pass labellers receive (label_in_1.json, _2, _3).

Gate 2 left no script for this step (make_g1v2.py only writes label_in_confirm.json), so this reproduces it. The
reconstruction was checked against gate 2: from Data/g1v2/pool.json it regenerates Data/g1v2/label_in_1/2/3.json
byte for byte (run with --check-gate2; that mode writes nothing).

The step: label_in_i.json holds pool[i-1::3] (round robin, so k = i, i+3, i+6, ...), each turn cut down to the four
fields the labellers see, in this order: k, op, action, output. No turn id, stratum or seed is shown to them.
Format, as in gate 2: json with ensure_ascii=False and indent=1, utf-8, CRLF line ends, no trailing newline.
Prints counts and hashes only.
"""
import hashlib
import json
import sys
from pathlib import Path

G3 = Path(r"C:\Users\joshd\Data\g3")
G2 = Path(r"C:\Users\joshd\Data\g1v2")
FIELDS = ("k", "op", "action", "output")


def render(pool, i):
    """Bytes of label_in_{i+1}.json for a pool (i = 0, 1, 2)."""
    rows = [{f: e[f] for f in FIELDS} for e in pool[i::3]]
    return json.dumps(rows, ensure_ascii=False, indent=1).replace("\n", "\r\n").encode("utf-8")


def main():
    if "--check-gate2" in sys.argv:
        pool = json.load(open(G2 / "pool.json", encoding="utf-8"))
        same = [render(pool, i) == (G2 / f"label_in_{i + 1}.json").read_bytes() for i in range(3)]
        print(json.dumps({"gate2_label_inputs_reproduced_byte_for_byte": same}))
        sys.exit(0 if all(same) else 1)
    pool = json.load(open(G3 / "pool.json", encoding="utf-8"))
    out = {}
    for i in range(3):
        data = render(pool, i)
        (G3 / f"label_in_{i + 1}.json").write_bytes(data)
        out[f"label_in_{i + 1}.json"] = {"turns": len(pool[i::3]), "k_first": pool[i]["k"], "k_last": pool[i::3][-1]["k"],
                                         "sha256": hashlib.sha256(data).hexdigest()}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
