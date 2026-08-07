#!/bin/sh
# mediahub clear-cache:清空蜜柑 nginx 磁盘缓存(数据+封面),下次请求重新回源
CACHE=/mnt/mmcblk0p7/.mikan-cache
if [ -d "$CACHE" ]; then
  N=$(find "$CACHE" -type f 2>/dev/null | wc -l)
  find "$CACHE" -type f -exec rm -f {} \; 2>/dev/null
  echo "{\"ok\":true,\"cleared\":$N}"
else
  echo '{"ok":false,"error":"缓存目录不存在"}'
fi
exit 0
