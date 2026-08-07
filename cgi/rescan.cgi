#!/bin/sh
# rescan - 手动触发视频库重扫,返回 JSON
# 由 uhttpd(127.0.0.1:8080)提供,nginx /rescan 反代,供前端"刷新库"按钮调用
echo "Content-Type: application/json"
echo ""
if /etc/video_scan.sh >/dev/null 2>&1; then
  echo '{"ok":true,"ts":'"$(date +%s)"'}'
else
  echo '{"ok":false}'
fi
