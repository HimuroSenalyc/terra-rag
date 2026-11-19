#!/usr/bin/env bash
# 图形化封装：选择章节范围 → 输入问题 → 显示答案
set -u

source /home/player/emb-venv/bin/activate
export ASK_PY=/home/player/ask.py

# ---------- 1. 选范围 ----------
RANGE=$(zenity --list \
  --title="方舟剧情检索" \
  --text="选择检索范围" \
  --radiolist \
  --column="" --column="范围" \
  TRUE  "主线 1~4 章（防剧透）" \
  FALSE "主线 1~8 章" \
  FALSE "主线 1~12 章" \
  FALSE "主线（全部）" \
  FALSE "活动 / 密录" \
  FALSE "全量（剧透警告）" \
  --width=420 --height=320 2>/dev/null)

[ -z "$RANGE" ] && exit 0

case "$RANGE" in
  "主线 1~4 章（防剧透）") export MODE=main; export MAX_MAIN=4 ;;
  "主线 1~8 章")           export MODE=main; export MAX_MAIN=8 ;;
  "主线 1~12 章")          export MODE=main; export MAX_MAIN=12 ;;
  "主线（全部）")          export MODE=main; export MAX_MAIN=99 ;;
  "活动 / 密录")           export MODE=event ;;
  "全量（剧透警告）")      export MODE=all ;;
  *) exit 0 ;;
esac

# ---------- 2. 输入问题 ----------
Q=$(zenity --entry \
  --title="方舟剧情检索 · $RANGE" \
  --text="问什么？" \
  --width=600 2>/dev/null)

[ -z "$Q" ] && exit 0

# ---------- 3. 跑 ----------
OUT=$(python3 "$ASK_PY" "$Q" 2>&1)

# ---------- 4. 显示结果 ----------
echo "$OUT" | zenity --text-info \
  --title="结果：$Q ｜ $RANGE" \
  --width=1000 --height=750 \
  --font="monospace 11" 2>/dev/null
