#!/bin/sh
# 番剧库一键卸载(保留已下载的视频数据;残留配置自动清理)
echo "=== 番剧库 一键卸载 ==="

opkg remove luci-app-mediahub 2>/dev/null || true
opkg remove kwrt-mediahub 2>/dev/null || true

# prerm 已清理:cron(video_scan)、rc.local 的 8080 uhttpd、8080 进程
# 这里再兜底清一次
sed -i '/video_scan\.sh/d' /etc/crontabs/root 2>/dev/null
sed -i '/uhttpd.*8080/d' /etc/rc.local 2>/dev/null
pgrep -f 'uhttpd.*8080' >/dev/null 2>&1 && pkill -f 'uhttpd.*8080' 2>/dev/null || true

# 清理蜜柑缓存目录(可重新生成)
rm -rf /mnt/mmcblk0p7/.mikan-cache 2>/dev/null || true

# 清理 nginx 残留配置引用(避免 reload 报错)
rm -f /etc/nginx/conf.d/mediahub.locations 2>/dev/null || true
if command -v nginx >/dev/null 2>&1 && nginx -t -c /etc/nginx/uci.conf >/dev/null 2>&1; then
  nginx -s reload -c /etc/nginx/uci.conf 2>/dev/null || true
fi

echo "=== 卸载完成 ==="
echo "已下载视频保留在原来的下载目录,可手动删除;aria2 配置(下载目录)未被还原,如需恢复请自行修改。"
exit 0
