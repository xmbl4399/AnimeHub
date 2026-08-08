#!/bin/sh
# sub.cgi:内封字幕探测/提取(ffmpeg)
# action=probe → JSON 字幕轨列表;action=get&i=N → WebVTT 字幕内容
ROOT=$(uci get mediahub.@main[0].root 2>/dev/null)
[ -z "$ROOT" ] && ROOT=/mnt/mmcblk0p7
q() { printf '%s' "$QUERY_STRING" | tr '&' '\n' | grep "^$1=" | head -1 | cut -d= -f2-; }
dec() { printf '%b' "$(printf '%s' "$1" | sed 's/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g; s/+/ /g')"; }
P=$(dec "$(q path)")
A=$(q action)
I=$(q i)
[ -z "$I" ] && I=0
# 安全:仅允许 ROOT 下的相对路径
case "$P" in
  /*|*".."*) echo "Content-Type: text/plain"; echo "Status: 400 Bad Request"; echo ""; echo "bad path"; exit 1;;
esac
F="$ROOT/$P"
[ -f "$F" ] || { echo "Content-Type: text/plain"; echo "Status: 404 Not Found"; echo ""; echo "not found"; exit 1; }
if [ "$A" = "probe" ]; then
  echo "Content-Type: application/json; charset=utf-8"
  echo ""
  ffprobe -v error -select_streams s -show_entries stream=index,codec_name:stream_tags=language,title -of json "$F" 2>/dev/null
  exit 0
fi
# WebVTT(浏览器 <track> 标准格式,SRT 直接转)
echo "Content-Type: text/vtt; charset=utf-8"
echo ""
ffmpeg -v error -i "$F" -map "0:$I" -f webvtt - 2>/dev/null
