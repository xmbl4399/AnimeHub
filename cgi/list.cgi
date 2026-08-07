#!/bin/sh
# list.cgi - 实时列出 /mnt/mmcblk0p7 下目录内容(文件夹视图实时显示,像文件管理器)
# GET ?path=<urlencoded 相对路径,空=根目录>
echo "Content-Type: application/json"
echo ""
QS=${QUERY_STRING:-}
# URL 解码(%XX + '+' 转空格)
P=$(printf '%b' "$(echo "$QS" | sed 's/^path=//; s/+/ /g; s/%/\\x/g')")
BASE=/mnt/mmcblk0p7
D="$BASE"
[ -n "$P" ] && D="$BASE/$P"
# 防目录穿越:仅允许 BASE 内
case "$D" in
  "$BASE"|"$BASE"/*) ;;
  *) echo '{"error":"bad path"}'; exit 0;;
esac
[ -d "$D" ] || { echo '{"error":"not a dir"}'; exit 0; }

{
  echo '{"dirs":['
  first=1
  for d in "$D"/*/; do
    [ -d "$d" ] || continue
    n=$(basename "$d")
    c=$(find "$d" -maxdepth 1 -type f 2>/dev/null | wc -l)
    mt=$(stat -c %Y "$d" 2>/dev/null)
    esc=$(printf '%s' "$n" | sed 's/\\/\\\\/g; s/"/\\"/g')
    [ $first -eq 1 ] || printf ','
    first=0
    printf '{"name":"%s","count":%s,"maxMt":%s}' "$esc" "$c" "$mt"
  done
  echo '],"files":['
  first=1
  for f in "$D"/*; do
    [ -f "$f" ] || continue
    rel="${f#$BASE/}"
    sz=$(stat -c %s "$f" 2>/dev/null); mt=$(stat -c %Y "$f" 2>/dev/null)
    # 视频标记(直接匹配完整路径,避免命令替换+tr 对中文路径的匹配问题)
    case "$f" in
      *.[Mm][Pp]4|*.[Mm][Kk][Vv]|*.[Ww][Ee][Bb][Mm]|*.[Aa][Vv][Ii]|*.[Mm][Oo][Vv]|*.[Tt][Ss]|*.[Ff][Ll][Vv]|*.[Mm]4[Vv]) v=1;;
      *) v=0;;
    esac
    esc=$(printf '%s' "$rel" | sed 's/\\/\\\\/g; s/"/\\"/g')
    [ $first -eq 1 ] || printf ','
    first=0
    printf '{"name":"%s","size":%s,"mtime":%s,"video":%s}' "$esc" "$sz" "$mt" "$v"
  done
  echo ']}'
}
