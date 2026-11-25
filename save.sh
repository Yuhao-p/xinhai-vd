#!/usr/bin/env bash
# 把 data/ 的新資料commit並推到main；失敗會重試，最後失敗只發警告（下次存檔會一併推上去）
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add data
if ! git diff --cached --quiet; then
  git commit -q -m "VD $(date -u +%Y-%m-%dT%H:%MZ)"
fi
# 有尚未推上去的commit才推
if [ -n "$(git log origin/main..HEAD --oneline 2>/dev/null)" ] || ! git rev-parse -q --verify origin/main >/dev/null; then
  for i in 1 2 3 4 5; do
    if git pull -q --rebase origin main && git push -q origin HEAD:main; then
      echo "saved $(date -u +%H:%MZ)"; exit 0
    fi
    git rebase --abort >/dev/null 2>&1   # 萬一卡在rebase，先復原再重試
    sleep $((i * 5))
  done
  echo "::warning::save failed $(date -u +%H:%MZ); will retry at next save"
  exit 0
fi
