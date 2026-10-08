#!/bin/bash
# 会话存档
# 把 Claude 的完整对话记录 + 工作区记忆备份到 _private/（该目录已被 .gitignore 排除，不会上传）
# 用法：bash ~/Documents/备考日程/backup.sh

DEST="$(cd "$(dirname "$0")" && pwd)"
OUT="$DEST/_private"
mkdir -p "$OUT"

SS="$HOME/Library/Application Support/CherryStudio"

echo "=== 备份对话记录 ==="
n=0
for f in "$SS/.claude/projects"/*dkrs1cdeh*/*.jsonl; do
  [ -f "$f" ] || continue
  cp "$f" "$OUT/transcript-$(basename "$f")"
  printf "  %-50s %s\n" "$(basename "$f")" "$(du -h "$f" | cut -f1)"
  n=$((n+1))
done
[ "$n" -eq 0 ] && echo "  （没找到对话记录）"

echo ""
echo "=== 备份工作区记忆 ==="
M="$SS/Data/Agents/dkrs1cdeh/memory"
for name in JOURNAL.jsonl FACT.md; do
  if [ -f "$M/$name" ]; then
    cp "$M/$name" "$OUT/$name"
    printf "  %-50s %s\n" "$name" "$(du -h "$M/$name" | cut -f1)"
  else
    printf "  %-50s （还没生成）\n" "$name"
  fi
done

echo ""
echo "=== 存档目录 ==="
echo "  $OUT"
ls -lah "$OUT" | tail -n +2 | awk '{printf "    %-12s %s\n", $5, $NF}'

echo ""
echo "提示：这个目录不会进 git。想异地备份的话，把整个 _private 文件夹拖进 iCloud 就行。"
