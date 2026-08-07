#!/bin/sh
# prune - 删除 Aria2 目录下的空目录(删除视频文件后的残留父文件夹)
# 仅处理 /mnt/mmcblk0p7/Aria2/ 内的子目录,不影响其他目录
echo "Content-Type: application/json"
echo ""
D=/mnt/mmcblk0p7/Aria2
# -depth 从最深层开始,rmdir 只删空目录;保留 Aria2 本身
find "$D" -mindepth 1 -depth -type d 2>/dev/null | while IFS= read -r d; do
  rmdir "$d" 2>/dev/null
done
echo '{"ok":true}'
