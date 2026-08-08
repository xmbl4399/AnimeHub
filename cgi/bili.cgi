#!/bin/sh
# bili.cgi:B 站弹幕源代理(SPI cookie 管理 + 搜索/弹幕转发)
# 浏览器无法自定义 Cookie 头,B 站搜索接口需要 buvid cookie → 由路由器 curl 统一管理 cookie jar
# action=search&kw=xxx → B 站搜索 JSON(原样)
# action=dm&bvid=xxx&page=N → pagelist 拿 cid → 弹幕 XML(原样)
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
JAR=/tmp/bili-cookie.txt
q() { printf '%s' "$QUERY_STRING" | tr '&' '\n' | grep "^$1=" | head -1 | cut -d= -f2-; }
dec() { printf '%b' "$(printf '%s' "$1" | sed 's/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g; s/+/ /g')"; }
ensure_cookie() {
  [ -s "$JAR" ] && return 0
  curl -s -m 10 'https://api.bilibili.com/x/frontend/finger/spi' -H "User-Agent: $UA" -c "$JAR" >/dev/null 2>&1
}
A=$(q action)
KW=$(dec "$(q kw)")
BV=$(q bvid)
PG=$(q page)
[ -z "$PG" ] && PG=1
case "$A" in
  search)
    ensure_cookie
    echo "Content-Type: application/json; charset=utf-8"
    echo ""
    curl -s --compressed -m 15 "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=$KW" \
      -H "User-Agent: $UA" -H 'Referer: https://www.bilibili.com/' -b "$JAR" -c "$JAR"
    ;;
  dm)
    ensure_cookie
    if [ -z "$BV" ]; then
      echo "Content-Type: text/plain"; echo "Status: 400 Bad Request"; echo ""; echo "need bvid"; exit 1
    fi
    # pagelist → cid(第 PG 个分P)
    PL=$(curl -s --compressed -m 10 "https://api.bilibili.com/x/player/pagelist?bvid=$BV" -H "User-Agent: $UA" -b "$JAR" -c "$JAR")
    CID=$(echo "$PL" | grep -oE '"cid":[0-9]*' | sed -n "${PG}p" | grep -oE '[0-9]*')
    [ -z "$CID" ] && CID=$(echo "$PL" | grep -oE '"cid":[0-9]*' | head -1 | grep -oE '[0-9]*')
    if [ -z "$CID" ]; then
      echo "Content-Type: text/plain"; echo "Status: 404 Not Found"; echo ""; echo "no cid"; exit 1
    fi
    echo "Content-Type: application/xml; charset=utf-8"
    echo ""
    curl -s --compressed -m 15 "https://api.bilibili.com/x/v1/dm/list.so?oid=$CID" -H "User-Agent: $UA" -b "$JAR" -c "$JAR"
    ;;
  *)
    echo "Content-Type: text/plain"; echo "Status: 400 Bad Request"; echo ""; echo "unknown action"; exit 1;;
esac
