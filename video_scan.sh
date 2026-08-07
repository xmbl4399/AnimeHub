#!/bin/sh
# video_scan.sh — 扫描 /mnt/mmcblk0p7 生成 /www/videos.json(按 mtime 倒序)
# 规则:
#   - Aria2 目录(/mnt/mmcblk0p7/Aria2/):收录全部文件(含 .torrent/.aria2 中间文件,供管理)
#   - 其他目录:仅视频扩展名,且 >=1MB(过滤下载残留)
OUT=/www/videos.json
TMP=/tmp/videos.json.$$

{
  echo '['
  first=1
  find /mnt/mmcblk0p7 \( -path '/mnt/mmcblk0p7/Aria2/*' \
       -o -iname '*.mp4' -o -iname '*.mkv' -o -iname '*.webm' -o -iname '*.avi' \
       -o -iname '*.mov' -o -iname '*.ts' -o -iname '*.flv' -o -iname '*.m4v' \) \
       -type f -print 2>/dev/null | \
  while IFS= read -r f; do
    mt=$(stat -c %Y "$f" 2>/dev/null); sz=$(stat -c %s "$f" 2>/dev/null)
    [ -n "$mt" ] && [ -n "$sz" ] || continue
    # 大小过滤:仅对非 Aria2 目录要求 >=1MB
    case "$f" in /mnt/mmcblk0p7/Aria2/*) ;; *) [ "$sz" -ge 1048576 ] || continue ;; esac
    echo "$mt|$sz|${f#/mnt/mmcblk0p7/}"
  done | sort -rn -t'|' -k1 | \
  while IFS='|' read -r mt sz rel; do
    esc=$(printf '%s' "$rel" | sed 's/\\/\\\\/g; s/"/\\"/g')
    if [ $first -eq 1 ]; then first=0; else printf ','; fi
    printf '\n{"name":"%s","size":%s,"mtime":%s}' "$esc" "$sz" "$mt"
  done
  echo
  echo ']'
} > "$TMP" && mv "$TMP" "$OUT" && chmod 644 "$OUT"
echo "videos.json updated: $(wc -c < "$OUT") bytes"
