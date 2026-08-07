#!/bin/sh
# cleanup - Aria2 缓存清理(合并进"刷新"按钮)
# 安全规则:
#   - 先探测 aria2 RPC:aria2 在线才删 .aria2/.torrent(防止 aria2 挂掉时误删正在下载的断点文件)
#   - 在线时:正在下载(tellActive)的文件跳过;停止/失败的残留(.aria2+残缺本体)删除
#   - 空目录清理、重扫快照始终执行
echo "Content-Type: application/json"
echo ""
D=/mnt/mmcblk0p7/Aria2

# 1) 探测 aria2 + 收集活动文件
RPC=$(curl -s -m 3 http://127.0.0.1:6800/jsonrpc -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"aria2.tellActive","params":[]}' 2>/dev/null)
ARIA2_OK=0; ACTIVE=''
if echo "$RPC" | grep -q '"result"'; then
  ARIA2_OK=1
  ACTIVE=$(echo "$RPC" | grep -oE '"path":"[^"]*"' | sed 's/"path":"//;s/"$//')
fi
is_active(){ echo "$ACTIVE" | grep -Fq "$1"; }

# 2) 清理缓存(仅 aria2 在线时;计数供报告)
BEFORE=$(find "$D" -maxdepth 1 -type f \( -name '*.aria2' -o -name '*.torrent' \) 2>/dev/null | wc -l)
if [ "$ARIA2_OK" = "1" ]; then
  find "$D" -maxdepth 1 -type f -name '*.aria2' 2>/dev/null | while IFS= read -r a; do
    base="${a%.aria2}"
    is_active "$base" && continue
    [ -e "$base" ] && rm -f "$base"
    rm -f "$a"
  done
  find "$D" -maxdepth 1 -type f -name '*.torrent' -exec rm -f {} \; 2>/dev/null
fi
AFTER=$(find "$D" -maxdepth 1 -type f \( -name '*.aria2' -o -name '*.torrent' \) 2>/dev/null | wc -l)
REMOVED=$((BEFORE - AFTER))

# 3) 删除 Aria2 下空目录(残留父文件夹)
find "$D" -mindepth 1 -depth -type d 2>/dev/null | while IFS= read -r d; do
  rmdir "$d" 2>/dev/null
done

# 4) 重扫快照
/etc/video_scan.sh >/dev/null 2>&1

echo "{\"ok\":true,\"aria2\":$ARIA2_OK,\"removed\":$REMOVED}"
