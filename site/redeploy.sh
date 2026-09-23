#!/bin/zsh
# 手动补部署：修好构建问题后跑这个。只做 导出 → 构建 → 英文镜像 → 措辞自检 → 部署，不重抓数据。
# 记进 daily_refresh.log（和每日刷新同一格式），health_check.py 据此判定今天已上线。
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/bin:$PATH"; export SINAN_THEME=coast
LOG=data/logs/daily_refresh.log
ts() { date "+%Y-%m-%d %H:%M:%S"; }
{
  echo "===== $(ts) 开始 ===== 手动补部署"
  /usr/bin/python3 site/about_pages.py 24 | tail -1
  /usr/bin/python3 site/export_media.py | tail -1 && /usr/bin/python3 site/export_data.py | tail -1
  /usr/bin/python3 site/pull_reports.py | tail -1
  /usr/bin/python3 site/build_v5.py > data/logs/.build_out 2>&1; rc=$?; tail -30 data/logs/.build_out
  [ $rc -eq 0 ] || { echo "构建失败，放弃部署"; echo "===== $(ts) 结束 ====="; exit 1; }
  /usr/bin/python3 site/i18n_apply.py site/dist https://compute.sinanlab.com | tail -1
  if /usr/bin/python3 site/wording_gate.py; then
    npx wrangler pages deploy site/dist --project-name sinan-compute --commit-dirty=true 2>&1 | grep -Ei "complete|error" | tail -1
  else
    echo "措辞自检未通过，未部署"
  fi
  echo "===== $(ts) 结束 ====="
} 2>&1 | tee -a "$LOG"
