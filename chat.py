"""প্যানেল-চ্যাট (Owner ২০২৬-১১-২৫: "UI-তে চ্যাট — ব্লকার নিয়ে কথা, ফাইল জোড়া, ফিক্স")।
প্রশ্ন আসে private boier-golpo-র `panel` ব্রাঞ্চে (panel/chat/<thread>.json, জোড়া ফাইল panel/files/…)।
এখানে: লাইনের অবস্থা + শেষ রানের কারণ-লাইন + দরকারি কোড-ফাইল পড়ে Gemini (লাইট/জেমা — বিল্ডের ফ্ল্যাশ-কোটা খায় না) উত্তর দেয়।
উত্তর থ্রেডের নিজের চাবিতে (চাবি শুধু private ব্রাঞ্চে) AES-256-GCM এনক্রিপ্ট হয়ে এই পাবলিক রিপোর `chat` ব্রাঞ্চে যায় —
তাই চাবি ছাড়া কেউ পড়তে পারে না; প্যানেল খুলে private থ্রেডে লিখে রাখে।"""
import base64, json, mimetypes, os, random, re, sys, time
from pathlib import Path
import requests

WS = Path(os.environ.get("GITHUB_WORKSPACE", "."))
PNL, PROJ = WS / "pnl" / "panel", WS / "proj"
THREAD = re.sub(r"[^A-Za-z0-9_\-]", "", os.environ.get("CHAT_THREAD", ""))[:40]
MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-lite-latest", "gemma-4-31b-it"]
TOKEN_RE = re.compile(r"AIza[0-9A-Za-z_\-]{10,}|hf_[A-Za-z0-9]{10,}|sk-[A-Za-z0-9_\-]{10,}|gh[pousr]_[A-Za-z0-9]{10,}|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-\.]+")
ENV_SECRETS = [v for k, v in os.environ.items() if v and len(v) >= 12 and re.search(r"TOKEN|KEY|SECRET|PASSWORD", k)]

SYSTEM = """তুমি "বইছবি" প্রোডাকশন-লাইনের প্যানেল-সহকারী। Owner প্যানেলের চ্যাটে ব্লকার বা লাইন নিয়ে জিজ্ঞেস করছেন।
নিয়ম:
- উত্তর বাংলায়, সংক্ষেপে (ফোনের এক পর্দা), আগে মূল কথা। শব্দ: "অফলাইন" = Owner-এর পিসি, "অনলাইন" = ক্লাউড-সহকারী।
- শুধু নিচের তথ্য (লাইনের অবস্থা, রান-লগ, ফাইল) থেকে বলো। যা জানো না তা বানিয়ো না — "এই তথ্য আমার কাছে নেই" বলো।
- কারণ বললে প্রমাণ দাও (কোন লগ-লাইন/কোন ঘর)। অনুমান হলে "অনুমান" বলো।
- কোনো চাবি/টোকেন/পাসওয়ার্ড কখনো লিখো না, চেয়ো না।
- কোডের ফাইল দেখা দরকার হলে শুধু এক লাইন লেখো: NEED: পথ১, পথ২  (সর্বোচ্চ ৪টা, রিপোর ভেতরের পথ, যেমন scripts/cloud_tick.py)। তখন ফাইল পেয়ে আবার উত্তর দেবে।
- তুমি নিজে কোড বদলাতে পারো না। কোড-ফিক্স লাগলে লেখো: কোন ফাইল, কোন জায়গা, কী বদল — যাতে Owner সেটা ডেভেলপার-সেশনে দিতে পারেন।
- নিরাপদ আদেশ সুপারিশ করতে চাইলে উত্তরের একদম শেষে আলাদা লাইনে একটাই লেখো (Owner বোতাম চেপে নিশ্চিত করবেন, তুমি নিজে চালাও না):
  ACTION: skip_cooldown   (চলতি ধাপের ঠান্ডা-সময় বাদ দিয়ে এখনই আবার চেষ্টা)
  ACTION: hold_publish    (চলতি গল্পের প্রকাশ থামানো)
  ACTION: release_publish (প্রকাশ-হোল্ড তোলা)
- টাকা, পাসওয়ার্ড, মোছা, FB/YT-তে কিছু করা — এগুলো শুধু Owner; সুপারিশ কোরো না।"""


def scrub(t):
    for v in ENV_SECRETS:
        t = t.replace(v, "•••")
    return TOKEN_RE.sub("•••", t)


def keys():
    ks = [os.environ.get("GEMINI_API_KEY" + ("" if i == 1 else f"_{i}"), "") for i in range(1, 9)]
    ks = [k for k in ks if k]
    random.shuffle(ks)
    return ks


def gemini(contents, system):
    last = "চাবি নেই"
    for model in MODELS:
        gemma = model.startswith("gemma")
        body = {"contents": contents, "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1400}}
        if gemma:   # জেমা system-নির্দেশ/ছবি নেয় না → লেখায় মিশিয়ে
            c2 = [{"role": c["role"], "parts": [p for p in c["parts"] if "text" in p] or [{"text": "(ছবি)"}]} for c in contents]
            c2[0]["parts"].insert(0, {"text": system + "\n\n"})
            body["contents"] = c2
        else:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        for k in keys()[:4]:
            try:
                r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                  headers={"x-goog-api-key": k}, json=body, timeout=90)
                if r.status_code == 200:
                    parts = (((r.json().get("candidates") or [{}])[0].get("content") or {}).get("parts")) or []
                    t = "".join(p.get("text", "") for p in parts).strip()
                    if t:
                        return t, model
                    last = f"{model}: ফাঁকা উত্তর"
                else:
                    last = f"{model}: HTTP {r.status_code}"
                    if r.status_code in (400, 404):
                        break   # এই মডেলে অনুরোধই চলে না → পরের মডেল
            except Exception as e:
                last = f"{model}: {type(e).__name__}"
    return "", last


def run_log():
    """শেষ শেষ-হওয়া cloud-assistant রানের কারণ-লাইন (পাবলিক Actions-লগ থেকে)।"""
    tok, repo = os.environ.get("GH_TOKEN", ""), os.environ.get("GITHUB_REPOSITORY", "")
    h = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}
    out = []
    try:
        runs = requests.get(f"https://api.github.com/repos/{repo}/actions/workflows/cloud.yml/runs?per_page=12&status=completed", headers=h, timeout=30).json().get("workflow_runs", [])
        runs = [r for r in runs if r.get("conclusion") in ("success", "failure")][:2]
        for r in runs:
            jobs = requests.get(r["jobs_url"], headers=h, timeout=30).json().get("jobs", [])
            if not jobs:
                continue
            lg = requests.get(f"https://api.github.com/repos/{repo}/actions/jobs/{jobs[0]['id']}/logs", headers=h, timeout=60).text
            keep = [re.sub(r"^\S+Z\s+", "", l)[:300] for l in lg.splitlines()
                    if re.search(r"⟫|ধাপ|ব্যর্থ|Drive|প্যানেল|media pull|অমিল|চাবি|ঠান্ডা|টুকরো|gemini-cli|Traceback|Error", l)]
            out.append(f"— রান {r['created_at']} ({r['conclusion']}):\n" + "\n".join(keep[-45:]))
    except Exception as e:
        out.append(f"(রান-লগ আনা যায়নি: {type(e).__name__})")
    return scrub("\n".join(out))[:9000]


def read_proj(paths):
    out = []
    for p in paths[:4]:
        p = p.strip().strip("`'\" ")
        f = (PROJ / p).resolve()
        if not p or ".." in p or p.startswith("/") or ".env" in Path(p).name or not str(f).startswith(str(PROJ.resolve())):
            out.append(f"### {p}\n(এই পথ পড়া যায় না)"); continue
        if not f.is_file():
            out.append(f"### {p}\n(ফাইল নেই)"); continue
        out.append(f"### {p}\n" + scrub(f.read_text(errors="ignore"))[:40000])
    return "\n\n".join(out)


def parts_of(m):
    ps = []
    for a in (m.get("files") or [])[:4]:
        f = WS / "pnl" / str(a.get("path", ""))
        if ".." in str(a.get("path", "")) or not f.is_file() or f.stat().st_size > 4_000_000:
            continue
        mime = a.get("mime") or mimetypes.guess_type(f.name)[0] or ""
        if mime.startswith("image/") or mime == "application/pdf":
            ps.append({"inlineData": {"mimeType": mime, "data": base64.b64encode(f.read_bytes()).decode()}})
        else:
            ps.append({"text": f"[জোড়া ফাইল {a.get('name', f.name)}]\n" + scrub(f.read_text(errors='ignore'))[:30000]})
    ps.append({"text": m.get("text") or "(শুধু ফাইল)"})
    return ps


def main():
    tf = PNL / "chat" / f"{THREAD}.json"
    if not THREAD or not tf.is_file():
        print("chat: থ্রেড নেই"); return 0
    th = json.loads(tf.read_text())
    msgs = th.get("msgs") or []
    if not msgs or msgs[-1].get("role") != "user":
        print("chat: উত্তর দেওয়ার মতো নতুন প্রশ্ন নেই"); return 0
    n = int(msgs[-1].get("n") or len(msgs))
    try:
        status = json.loads(Path("/tmp/status.json").read_text())
        status.pop("files", None)
    except Exception:
        status = {}
    rules = ""
    try:
        rules = "\n".join((PROJ / "CLAUDE.md").read_text(errors="ignore").splitlines()[:14])[:6000]
    except Exception:
        pass
    ctx = (f"এখন {time.strftime('%F %H:%M')} (ঢাকা)।\n\n## লাইনের অবস্থা (status.json; সময় = epoch সেকেন্ড)\n{json.dumps(status, ensure_ascii=False)[:7000]}"
           f"\n\n## শেষ রানের কারণ-লাইন\n{run_log()}\n\n## প্রজেক্টের সাম্প্রতিক নিয়ম (CLAUDE.md-র শুরু)\n{scrub(rules)}")
    contents = []
    for m in msgs[-10:]:
        role = "user" if m.get("role") == "user" else "model"
        ps = parts_of(m) if (role == "user" and m is msgs[-1]) else [{"text": str(m.get("text") or "")[:4000]}]
        if contents and contents[-1]["role"] == role:
            contents[-1]["parts"] += ps
        else:
            contents.append({"role": role, "parts": ps})
    while contents and contents[0]["role"] != "user":
        contents.pop(0)
    system = SYSTEM + "\n\n" + ctx
    text, model = gemini(contents, system)
    m = re.search(r"^\s*NEED:\s*(.+)$", text, re.M) if text else None
    if m:
        got = read_proj(re.split(r"[,\s]+", m.group(1).strip()))
        contents += [{"role": "model", "parts": [{"text": text}]}, {"role": "user", "parts": [{"text": "চাওয়া ফাইল:\n\n" + got + "\n\nএখন চূড়ান্ত উত্তর দাও (আর NEED নয়)।"}]}]
        t2, model2 = gemini(contents, system)
        text, model = (t2, model2) if t2 else ("ফাইল পড়ার পর উত্তর তৈরি করা যায়নি (" + model2 + ")।", model)
    if not text:
        text = f"উত্তর তৈরি করা যায়নি — Gemini সাড়া দেয়নি ({model})। একটু পরে আবার লিখুন।"
        model = ""
    out = {"n": n + 1, "role": "bot", "text": scrub(text)[:6000], "model": model, "t": time.time(), "re": n}
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = base64.b64decode(th["key"])
    nonce = os.urandom(12)
    blob = nonce + AESGCM(key).encrypt(nonce, json.dumps(out, ensure_ascii=False).encode(), None)
    od = Path("/tmp/chat_out"); od.mkdir(exist_ok=True)
    (od / f"{THREAD}-{n}.bin").write_bytes(blob)
    print(f"chat ✔ থ্রেড {THREAD} প্রশ্ন #{n} → {len(blob)} বাইট ({model or 'ব্যর্থ-বার্তা'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
