#!/bin/sh
# del - 删除视频库文件(替代已停用的 WebDAV DELETE)
# 用法:GET /del?path=<urlencoded 相对路径>(相对 /mnt/mmcblk0p7,如 Aria2/xxx.mkv)
# 安全:仅允许删 /mnt/mmcblk0p7 内,防 .. 穿越
echo "Content-Type: application/json"
echo ""
QS=${QUERY_STRING:-}
# URL 解码(%XX -> \xXX 由 printf %b 解析;+ 转空格)
P=$(printf '%b' "$(echo "$QS" | sed 's/^path=//; s/+/ /g; s/%/\\x/g')")
BASE=/mnt/mmcblk0p7
F="$BASE/$P"
case "$F" in
  "$BASE"/*) ;;
  *) echo '{"ok":false,"error":"bad path"}'; exit 0;;
esac
if [ -f "$F" ]; then
  rm -f "$F"
  # 连带删除 aria2 断点控制文件(下载残留)
  [ -e "$F.aria2" ] && rm -f "$F.aria2"
  echo '{"ok":true,"type":"file"}'
elif [ -d "$F" ]; then
  rm -rf "$F"
  echo '{"ok":true,"type":"dir"}'
else
  echo '{"ok":false,"error":"not found"}'
fi
