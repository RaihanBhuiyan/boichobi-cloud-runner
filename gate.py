"""সস্তা দরজা-চেক: পিসির সংকেত টাটকা আর চাবি পিসির হাতে → সহকারী কিছু করে না (প্রাইভেট repo নামানোও নয়)।"""
import json, os, time, tempfile
from pathlib import Path
from huggingface_hub import hf_hub_download
REPO = os.environ.get("CLOUD_STATE_REPO", "raihanaal2/boichobi-cloud-state")
TOK = os.environ.get("HF_WRITE_TOKEN") or os.environ.get("HF_TOKEN")
def rd(p, d):
    try:
        with tempfile.TemporaryDirectory() as td:
            return json.loads(Path(hf_hub_download(REPO, p, repo_type="dataset", token=TOK, cache_dir=td)).read_text())
    except Exception:
        return d
hb = rd("heartbeat.json", {}) or {}; ls = rd("lease.json", {}) or {}
age = (time.time() - hb.get("t", 0)) / 60
run = os.environ.get("SIMULATE") == "1" or age > 20 or (ls.get("owner") == "cloud")
print(f"পিসির সংকেত {age:.0f} মিনিট আগে · চাবি {ls.get('owner', 'pc')} → {'চালাও' if run else 'চুপ'}")
with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as f:
    f.write(f"run={'1' if run else '0'}\n")
