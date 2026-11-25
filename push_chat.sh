#!/usr/bin/env bash
# এনক্রিপ্ট-করা চ্যাট-উত্তর → `chat` ব্রাঞ্চ (r/<thread>-<n>.bin)। ৩০০-র বেশি জমলে ব্রাঞ্চ নতুন করে শুরু।
set -u
ls /tmp/chat_out/*.bin >/dev/null 2>&1 || { echo "chat: পাঠানোর কিছু নেই"; exit 0; }
url="https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
d=$(mktemp -d)
if git clone -q --depth 1 -b chat "$url" "$d" 2>/dev/null && [ "$(ls "$d/r" 2>/dev/null | wc -l)" -lt 300 ]; then cd "$d"; else rm -rf "$d"; d=$(mktemp -d); cd "$d"; git init -q; git checkout -q -b chat; fi
mkdir -p r && cp /tmp/chat_out/*.bin r/ && git add r
git -c user.name="cloud-assistant" -c user.email="41898282+github-actions[bot]@users.noreply.github.com" commit -qm "chat $(date -u +%FT%TZ)"
if git push -qf "$url" chat >/dev/null 2>&1; then echo "chat ✔ পাঠানো"; else echo "chat: পুশ যায়নি"; exit 1; fi
