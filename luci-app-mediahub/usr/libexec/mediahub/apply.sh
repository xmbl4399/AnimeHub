#!/bin/sh
# mediahub apply:将 /etc/config/mediahub 的 dir(下载目录)/root(媒体根)全局应用到:
#   aria2 uci dir、video_scan.sh、nginx media.locations、cgi BASE
# 用法:apply.sh [--dry-run]  (--dry-run 只输出将做的改动,不实际修改)
DRY=0
[ "$1" = "--dry-run" ] && DRY=1

DIR=$(uci get mediahub.@main[0].dir 2>/dev/null)
ROOT=$(uci get mediahub.@main[0].root 2>/dev/null)
if [ -z "$DIR" ] || [ -z "$ROOT" ]; then
  echo '{"ok":false,"error":"mediahub dir/root 未配置"}'
  exit 1
fi

# 变更预览(JSON 字符串:换行转 \n,转义引号)
CH="ARIA2_DIR=$DIR
VIDEO_SCAN_ROOT=$ROOT
MEDIA_ALIAS=$ROOT/
CGI_BASE=$ROOT"
ESC=$(printf '%s' "$CH" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' '~' | sed 's/~/\\n/g')
echo "{\"dry_run\":$DRY,\"dir\":\"$DIR\",\"root\":\"$ROOT\",\"changes\":\"$ESC\"}"

# --- 0. 确保目录存在(缓存 + 下载目录,nginx proxy_cache_path 目录必须存在) ---
if [ $DRY -eq 0 ]; then
  mkdir -p "$ROOT/.mikan-cache" "$DIR" 2>/dev/null || true
fi

# --- 1. aria2 uci dir(并 commit) ---
if [ $DRY -eq 0 ]; then
  uci set aria2.@aria2[0].dir="$DIR" && uci commit aria2
fi

# --- 2. video_scan.sh:替换扫描根,再替换 Aria2 特例 ---
if [ $DRY -eq 0 ]; then
  sed -i "s|/mnt/mmcblk0p7|$ROOT|g; s|$ROOT/Aria2|$DIR|g" /etc/video_scan.sh
fi

# --- 3. nginx media.locations alias ---
if [ $DRY -eq 0 ]; then
  sed -i "s|alias /mnt/mmcblk0p7/|alias $ROOT/|g" /etc/nginx/conf.d/media.locations
  if nginx -t -c /etc/nginx/uci.conf >/dev/null 2>&1; then
    nginx -s reload -c /etc/nginx/uci.conf 2>/dev/null || /etc/init.d/nginx reload 2>/dev/null || true
  else
    echo '{"nginx_t":"failed"}'
  fi
fi

# --- 4. cgi BASE ---
if [ $DRY -eq 0 ]; then
  sed -i "s|^BASE=.*|BASE=$ROOT|" /www/cgi-bin/del
fi

# --- 5. 重启 aria2 使 dir 生效 ---
if [ $DRY -eq 0 ]; then
  /etc/init.d/aria2 restart 2>/dev/null || true
fi

# --- 6. 服务主开关:enabled=0 停用页面反代+定时重扫;=1 恢复(OpenClash 式即点即生效) ---
EN=$(uci get mediahub.@main[0].enabled 2>/dev/null)
[ -z "$EN" ] && EN=1
MH_LOCS="media bili bili-stream anime-redirect bgm mikan-proxy mikan-img hub-cache cleanup rescan video-del list prune"
if [ $DRY -eq 0 ]; then
  if [ "$EN" = "0" ]; then
    crontab -l 2>/dev/null | sed 's|^\(.*video_scan\.sh.*\)$|#\1|' | crontab -
    for L in $MH_LOCS; do
      [ -f /etc/nginx/conf.d/$L.locations ] && mv /etc/nginx/conf.d/$L.locations /etc/nginx/conf.d/$L.locations.off
    done
  else
    crontab -l 2>/dev/null | sed 's|^#\(.*video_scan\.sh.*\)$|\1|' | crontab -
    for L in $MH_LOCS; do
      [ -f /etc/nginx/conf.d/$L.locations.off ] && mv /etc/nginx/conf.d/$L.locations.off /etc/nginx/conf.d/$L.locations
    done
  fi
  if nginx -t -c /etc/nginx/uci.conf >/dev/null 2>&1; then
    /etc/init.d/nginx reload 2>/dev/null || true
  fi
fi

[ $DRY -eq 0 ] && echo '{"ok":true,"applied":true}'
exit 0
