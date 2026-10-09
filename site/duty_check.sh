#!/bin/zsh
# 来信值班的固定第一步（定时任务「司南来信值班」每轮只跑这一条就能看到全部情况）：
#   ① 后台采集服务在不在跑（launchd com.sinanlab.pipeline），不在就拉起来（绝不用 nohup）
#   ② 部署健康（health_check.py）
#   ③ 分拣并打印待处理来信（inbox_duty.py show）
# 这条命令在项目 .claude/settings.local.json 里放行，值班无人值守时不会卡在权限弹窗上。
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
echo "【后台】"
st=$(launchctl print gui/$(id -u)/com.sinanlab.pipeline 2>/dev/null | grep -E "^\s*state =" | head -1 | tr -d ' \t')
if [ "$st" = "state=running" ]; then
  echo "采集服务在跑；最近一次可达探测：$(tail -1 data/logs/heartbeat.log 2>/dev/null | cut -c1-60)"
else
  echo "采集服务不在跑（${st:-未注册}），正在拉起……"
  launchctl kickstart -k gui/$(id -u)/com.sinanlab.pipeline 2>&1 | tail -2
  sleep 5
  launchctl print gui/$(id -u)/com.sinanlab.pipeline 2>/dev/null | grep -E "^\s*state =" | head -1
fi
echo "\n【部署健康】"
/usr/bin/python3 site/health_check.py; hc=$?
echo "health_exit=$hc"
echo "\n【来信】"
/usr/bin/python3 site/inbox_duty.py show
