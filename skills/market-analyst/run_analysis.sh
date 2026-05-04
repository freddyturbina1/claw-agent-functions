#!/bin/bash
# Market Analyst - Hourly runner
# Collects news → sends to Claude for analysis → outputs Telegram message

SKILL_DIR="$HOME/.openclaw/workspace/skills/market-analyst"
LOG="$SKILL_DIR/run.log"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG"

# Step 1: Collect news
echo "[1/2] Collecting news..." >> "$LOG"
RESULT=$(python3 "$SKILL_DIR/market_analyst.py" 2>>"$LOG")

if [ $? -ne 0 ] || [ -z "$RESULT" ]; then
    echo "ERROR: Failed to collect news" >> "$LOG"
    exit 1
fi

STATUS=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status','error'))")
if [ "$STATUS" = "no_new_articles" ]; then
    echo "No new articles, skipping." >> "$LOG"
    exit 0
fi

ARTICLES_COUNT=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('articles_count',0))")
ARTICLES_TEXT=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('articles_text',''))")
echo "Collected $ARTICLES_COUNT articles" >> "$LOG"

# Step 2: Output for cron (OpenClaw will handle Claude analysis)
echo "$RESULT" > "$SKILL_DIR/latest_news.json"
echo "Done. Articles saved to latest_news.json" >> "$LOG"
