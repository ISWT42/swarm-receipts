"""Build the sealed tool's own turn index once, on disk, so the full run can reuse it.
Uses receipts_io.TurnIndex unchanged; only close() is overridden so the index file is kept."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, r"C:\Users\joshd\Workbench\swarm-receipts")
from receipts_io import TurnIndex, load_field_map
data, work = sys.argv[1], Path(sys.argv[2])
class KeepIndex(TurnIndex):
    def close(self):
        if not self._closed:
            self.connection.close(); self._closed = True
t = time.time()
idx = KeepIndex(data, load_field_map(), work_dir=work)
idx.build()
info = {"index": str(idx.path), "counts": idx.counts, "diagnostics": idx.diagnostics,
        "build_seconds": round(time.time() - t), "data": data}
idx.close()
final = work / "turn-index.sqlite"
Path(info["index"]).rename(final); info["index"] = str(final)
(work / "index-info.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
print(json.dumps(info)[:2000])
