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


MEDIA = os.environ.get("CLOUD_MEDIA_REPO", "raihanaal2/boichobi-cloud-media")
TOKEN_RE = re.compile(r"AIza[0-9A-Za-z_\-]{10,}|hf_[A-Za-z0-9]{10,}|sk-[A-Za-z0-9_\-]{10,}|gh[pousr]_[A-Za-z0-9]{10,}")


def files(focus):
    """চলতি গল্পের তৈরি ফাইলের তালিকা (শুধু নাম+মাপ; ফাইল নিজে private-ই থাকে) — প্যানেল ধাপের পাশে লিংক দেখায়।
    [[ঘর, পথ, বাইট]] · ঘর s = স্টেট-ঘর, m = মিডিয়া-ঘর।"""
    if not focus:
        return []
    from huggingface_hub import HfApi
    a, out = HfApi(token=TOK), []
    m = re.match(r"^himu-next-(\d+)$", focus)
    pj = f"next{m.group(1)}" if m else focus
    projs = [f"proj/{pj}"]
    try:   # প্রজেক্ট-ফোল্ডারের নাম next8_v6-এর মতোও হয় → proj/-এর যে ফোল্ডার pj দিয়ে শুরু (আর ঠিক তার পরে অঙ্ক নয়) সব
        projs = [f.path for f in a.list_repo_tree(MEDIA, "proj", repo_type="dataset", recursive=False)
                 if getattr(f, "size", None) is None and re.match(rf"^proj/{re.escape(pj)}(?!\d)", f.path)] or projs
    except Exception:
        pass
    for tag, repo, roots in (("s", REPO, [f"snap/jobs/{focus}"]), ("m", MEDIA, [f"jobs/{focus}", f"pub/{focus}"] + projs[-3:])):
        for root in roots:
            try:
                for f in a.list_repo_tree(repo, root, repo_type="dataset", recursive=True):
                    sz = getattr(f, "size", None)
                    if sz is None or "/node_modules/" in f.path or "/.locks/" in f.path or "/lib/" in f.path or "/assets/" in f.path or "/gen/" in f.path:
                        continue
                    out.append([tag, TOKEN_RE.sub("•••", f.path)[:200], int(sz)])
            except Exception:
                pass
    return out[:400]


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
    # ধাপ: স্টেট-ফাইলের `step` পিসির লেখা — অনলাইন এগিয়ে গেলে পুরনো থাকে (গল্প ৮: render চলছে, দেখাত build)। লিজের ধাপ এগিয়ে থাকলে সেটাই।
    try:
        order = ["script", "script_review", "package", "package_audit", "owner_ok", "voice", "voice_clean", "build", "storyboard", "render", "finish", "checks", "audit", "draft_tg", "publish", "teaser", "done"]
        ls, ss = out["lease"].get("step"), out["state"].get("step")
        if ls in order and (ss not in order or order.index(ls) > order.index(ss)):
            out["state"]["step"] = ls
    except Exception:
        pass
    try:   # Owner ২০২৬-১১-২৬ "proper update": গেটের মাপা সংখ্যা (পর্দা/মিনিট, পুনরাবৃত্তি, প্রাণ-স্কোর) প্যানেলে/চ্যাটে — আগে শুধু private night.log-এ ছিল
        nl = (rd(f"snap/jobs/{focus}/night.log", "", text=True) or "").splitlines() if focus else []
        out["gate"] = [l for l in nl if "গেট" in l or "চুক্তি" in l or "পট-রং" in l][-8:]
        mf = (rd(f"snap/jobs/{focus}/owner_feedback_motion.md", "", text=True) or "") if focus else ""
        out["motion"] = [mf[i:i + 380] for i in range(0, min(len(mf), 1900), 380)]
    except Exception:
        pass
    out = scrub(out)
    try:   # Owner ২০২৬-১১-২৬: ধাপের ফল Drive-এ লিংকে-দেখা (stage_share.py) — শুধু Drive-লিংক, চাবি নয়
        lk = rd(f"snap/jobs/{focus}/stage_links.json", {}) if focus else {}
        out["links"] = {st: [{"name": str(r.get("name", ""))[:160], "url": r["url"], "size": int(r.get("size", 0)), "t": r.get("t", "")}
                             for r in rows if isinstance(r, dict) and str(r.get("url", "")).startswith("https://drive.google.com/file/d/")][:8]
                        for st, rows in (lk or {}).items() if isinstance(rows, list) and not st.startswith("_")}
        out["links_pending"] = (lk or {}).get("_pending", [])[:20]
    except Exception:
        out["links"] = {}
    try:
        out["files"] = files(focus)   # scrub-এর পরে: লম্বা পথ যেন "চাবি-সদৃশ" বলে কাটা না পড়ে
    except Exception:
        out["files"] = []
    json.dump(out, sys.stdout, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
