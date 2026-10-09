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
  echo "采集服务在跑；最近 3 次可达探测："
  tail -3 data/logs/heartbeat.log 2>/dev/null | cut -c1-80 | sed 's/^/  /'
  if curl -s -o /dev/null -m 15 https://www.cloudflare.com/cdn-cgi/trace; then echo "  本机此刻上网正常（某一轮写着「外网不通」= 那一小时本机网络断过，该轮已自动不记账，不用处理）"
  else echo "  ⚠ 本机此刻连不上外网——这是本机网络问题，不是站点问题；连续 3 轮以上才需要告诉 Eric 检查网络/代理"; fi
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
