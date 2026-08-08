#!/bin/sh
# bili.cgi:B 站弹幕源代理(SPI cookie 管理 + 搜索/弹幕转发)
# 浏览器无法自定义 Cookie 头,B 站搜索接口需要 buvid cookie → 由路由器 curl 统一管理 cookie jar
# action=search&kw=xxx → B 站搜索 JSON(原样)
# action=pagelist&bvid=xxx → 分P 列表 JSON(解析分P 对应集数用)
# action=dm&cid=xxx → 直接按 cid 拉弹幕 XML
# action=dm&bvid=xxx&page=N → pagelist 拿 cid → 弹幕 XML
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
CID=$(q cid)
[ -z "$PG" ] && PG=1
case "$A" in
  spi)
    echo "Content-Type: application/json; charset=utf-8"
    echo ""
    curl -s -m 10 'https://api.bilibili.com/x/frontend/finger/spi' -H "User-Agent: $UA" -c "$JAR"
    ;;
  search)
    ensure_cookie
    echo "Content-Type: application/json; charset=utf-8"
    echo ""
    # 结果缓存 10 分钟(同一关键词不重复搜索,减少风控触发面)
    CACHE=/tmp/bili-srcache
    mkdir -p "$CACHE" 2>/dev/null
    H=$(printf '%s' "$KW" | md5sum | cut -d' ' -f1)
    CF="$CACHE/$H.json"
    TS="$CACHE/$H.ts"
    if [ -f "$CF" ] && [ -f "$TS" ] && [ $(( $(date +%s) - $(cat "$TS" 2>/dev/null) )) -lt 600 ]; then
      cat "$CF"
      exit 0
    fi
    # 搜索:B 站对搜索接口间歇风控(HTML 出错页),失败自动重试最多 3 次
    R=""
    i=0
    while [ $i -lt 3 ]; do
      i=$((i+1))
      R=$(curl -s --compressed -m 15 "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=$KW" \
        -H "User-Agent: $UA" -H 'Referer: https://www.bilibili.com/' -b "$JAR" -c "$JAR")
      if printf '%s' "$R" | head -c 1 | grep -q '{'; then
        printf '%s' "$R" > "$CF" 2>/dev/null
        date +%s > "$TS" 2>/dev/null
        printf '%s' "$R"
        exit 0
      fi
      [ $i -lt 3 ] && sleep 2
    done
    printf '%s' "$R"
    ;;
  pagelist)
    ensure_cookie
    if [ -z "$BV" ]; then
      echo "Content-Type: text/plain"; echo "Status: 400 Bad Request"; echo ""; echo "need bvid"; exit 1
    fi
    echo "Content-Type: application/json; charset=utf-8"
    echo ""
    curl -s --compressed -m 10 "https://api.bilibili.com/x/player/pagelist?bvid=$BV" -H "User-Agent: $UA" -b "$JAR" -c "$JAR"
    ;;
  dm)
    ensure_cookie
    if [ -z "$CID" ]; then
      if [ -z "$BV" ]; then
        echo "Content-Type: text/plain"; echo "Status: 400 Bad Request"; echo ""; echo "need cid or bvid"; exit 1
      fi
      # pagelist → cid(第 PG 个分P)
      PL=$(curl -s --compressed -m 10 "https://api.bilibili.com/x/player/pagelist?bvid=$BV" -H "User-Agent: $UA" -b "$JAR" -c "$JAR")
      CID=$(echo "$PL" | grep -oE '"cid":[0-9]*' | sed -n "${PG}p" | grep -oE '[0-9]*')
      [ -z "$CID" ] && CID=$(echo "$PL" | grep -oE '"cid":[0-9]*' | head -1 | grep -oE '[0-9]*')
    fi
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
