#!/bin/zsh
# 幂等：确保 D1 上的索引存在。由 run_forever.sh 每小时调用一次；索引已存在时几乎不耗读取额度。
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/bin:$PATH"
out=$(npx wrangler d1 execute sinan-users --remote --json --command "CREATE INDEX IF NOT EXISTS idx_events_name_day ON events(name, day)" 2>&1)
if echo "$out" | grep -q '"success": true'; then echo "$(date '+%F %T') d1 indexes ok" >> data/logs/d1_indexes.log; else echo "$(date '+%F %T') d1 index failed: $(echo "$out" | grep -o 'text": "[^"]*' | tail -1 | cut -c1-160)" >> data/logs/d1_indexes.log; fi
# Robo 众测两张表（幂等；额度用尽当天会失败，次小时自动重试）
out2=$(npx wrangler d1 execute sinan-users --remote --file users/migrations/009_robo_crowd.sql 2>&1)
if echo "$out2" | grep -q '"success": true\|Executed'; then echo "$(date '+%F %T') migration 009 ok" >> data/logs/d1_indexes.log; else echo "$(date '+%F %T') migration 009 failed: $(echo "$out2" | grep -o 'text": "[^"]*' | tail -1 | cut -c1-120)" >> data/logs/d1_indexes.log; fi
