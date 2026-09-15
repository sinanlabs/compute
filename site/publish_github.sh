#!/bin/zsh
# 每日：把公开数据文件提交到公开仓库 sinanlabs/compute；每月 1 日：把上月月报发成 GitHub Release。
cd "$(dirname "$0")/.."
TODAY=$(TZ=Asia/Shanghai date +%F)
git add site/reports site/rank site/weekly site/price_index.json site/tokref.json site/gpu.json docs/METHOD.md 2>/dev/null
if ! git diff --cached --quiet; then
  git commit -q -m "data: $TODAY 每日测量数据（司南榜 / 周报 / 月报 / 价格指数 / 算力账本）" && git push -q origin main && echo "GitHub：数据已提交 $TODAY"
else
  echo "GitHub：数据无变化"
fi
if [ "$(TZ=Asia/Shanghai date +%d)" = "01" ]; then
  M=$(TZ=Asia/Shanghai date -v-1d +%Y-%m 2>/dev/null || TZ=Asia/Shanghai date -d "yesterday" +%Y-%m)
  if [ -f "site/reports/$M.json" ] && ! gh release view "report-$M" >/dev/null 2>&1; then
    gh release create "report-$M" "site/reports/$M.json" --title "中国模型 API 中转市场月报 · $M" \
      --notes "司南实验室月报 $M（定稿）。网页版：https://compute.sinanlab.com/report/$M · 口径：https://compute.sinanlab.com/method · 引用：司南实验室，《中国模型 API 中转市场月报 · $M》，https://compute.sinanlab.com/report/$M" \
      && echo "GitHub：Release report-$M 已发布"
  fi
fi
