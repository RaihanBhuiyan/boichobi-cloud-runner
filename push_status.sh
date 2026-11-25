#!/usr/bin/env bash
# status.json → `status` ব্রাঞ্চ (একটাই কমিট, জোর-পুশ: ইতিহাস জমে না)। ব্যর্থ হলেও লাইন থামে না।
set -u
python "$GITHUB_WORKSPACE/status.py" > /tmp/status.json 2>/dev/null || { echo "status: স্টেট-ঘর পড়া যায়নি"; exit 0; }
[ -s /tmp/status.json ] || { echo "status: খালি"; exit 0; }
d=$(mktemp -d); cd "$d" || exit 0
git init -q && git checkout -q -b status
cp /tmp/status.json status.json
git add status.json
git -c user.name="cloud-assistant" -c user.email="41898282+github-actions[bot]@users.noreply.github.com" commit -qm "status $(date -u +%FT%TZ)"
if git push -qf "https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" status >/dev/null 2>&1; then echo "status ✔ ($(wc -c < status.json) বাইট)"; else echo "status: পুশ যায়নি"; fi
