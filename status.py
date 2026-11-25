"""প্যানেলের জন্য লাইনের অবস্থা — এক ফাইলে (Owner ২০২৬-১১-২৫: "প্যানেলে আবার চাবি বসাতে চাই না")।
HF স্টেট-ঘর থেকে পড়ে, শুধু দরকারি ঘর ছেঁকে stdout-এ JSON দেয়; workflow সেটা `status` ব্রাঞ্চে রাখে (পাবলিক)।
কোনো চাবি/টোকেন এতে যায় না: শুধু ধাপ, ব্লকার, কোটার সংখ্যা; লেখা থেকে চাবি-সদৃশ অংশ মুছে দেওয়া হয়।"""
import json, os, re, sys, tempfile, time
from pathlib import Path
from huggingface_hub import hf_hub_download

REPO = os.environ.get("CLOUD_STATE_REPO", "raihanaal2/boichobi-cloud-state")
TOK = os.environ.get("HF_WRITE_TOKEN") or os.environ.get("HF_TOKEN")
SECRET_RE = re.compile(r"AIza[0-9A-Za-z_\-]{10,}|hf_[A-Za-z0-9]{10,}|sk-[A-Za-z0-9_\-]{10,}|gh[pousr]_[A-Za-z0-9]{10,}|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-\.]+|[A-Za-z0-9_\-+/=]{36,}")
ENV_SECRETS = [v for k, v in os.environ.items() if v and len(v) >= 12 and re.search(r"TOKEN|KEY|SECRET|PASSWORD", k)]


def scrub(o):
    if isinstance(o, str):
        for v in ENV_SECRETS:
            o = o.replace(v, "•••")
        return SECRET_RE.sub("•••", o)[:400]
    if isinstance(o, list):
        return [scrub(x) for x in o[:60]]
    if isinstance(o, dict):
        return {str(k)[:80]: scrub(v) for k, v in list(o.items())[:400]}
    return o


def rd(path, default=None, text=False):
    try:
        with tempfile.TemporaryDirectory() as td:
            t = Path(hf_hub_download(REPO, path, repo_type="dataset", token=TOK, cache_dir=td)).read_text(errors="ignore")
            return t if text else json.loads(t)
    except Exception:
        return default


def pick(d, keys):
    return {k: d[k] for k in keys if isinstance(d, dict) and k in d}


def main():
    hb = rd("heartbeat.json", {}) or {}
    focus = (rd("snap/jobs/FOCUS", "", text=True) or "").strip()[:80]
    st = (rd(f"snap/jobs/{focus}/long_state.json", {}) or {}) if focus else {}
    led = rd("snap/jobs/.locks/free_ledger.json", {}) or {}
    wd = rd("snap/jobs/.locks/watchdog_last.json", {}) or {}
    hand = rd("handover.md", "", text=True) or ""
    out = {
        "v": 1, "t": time.time(), "ok": bool(hb or focus),
        "hb": pick(hb, ["t", "iso"]),
        "lease": pick(rd("lease.json", {}) or {}, ["owner", "busy", "step", "t", "since"]),
        "focus": focus,
        "state": pick(st, ["step", "round", "fails", "not_before", "cooldowns", "parked", "build_chunks_n", "updated", "build_by"]),
        "wd": {"issues": [pick(x, ["what", "plan", "action", "owner", "ts"]) for x in (wd.get("issues") or [])[:12] if isinstance(x, dict)]},
        "cdown": pick(rd("snap/jobs/.locks/CLAUDE_DOWN.json", {}) or {}, ["until", "t"]),
        "cstat": pick(rd("cloud_status.json", {}) or {}, ["last", "t"]),
        "pre": pick(rd("cloud_preflight.json", {}) or {}, ["last_bad", "cli_ok", "cli_t"]),
        "led": {"day": led.get("day"), "d": {k: v for k, v in (led.get("d") or {}).items() if isinstance(v, (int, float))}},
        "hand": [l for l in hand.splitlines() if l.startswith("- ")][-8:],
    }
    json.dump(scrub(out), sys.stdout, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
