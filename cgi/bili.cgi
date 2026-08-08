#!/bin/sh
# bili.cgi:B 站代理(SPI cookie 管理 + 扫码登录令牌缓存 + 搜索/弹幕/播放地址转发)
# action=search&kw=xxx → 搜索 JSON | action=pagelist&bvid=xxx → 分P JSON
# action=dm&cid=xxx | action=dm&bvid=xxx&page=N → 弹幕 XML
# action=playurl&bvid=&cid=&page=N → 播放地址 JSON(wbi 签名)
# action=login_status → nav 接口(是否已登录/用户名)
# action=qrcode_gen → 二维码生成 | action=qrcode_poll&qrcode_key=xxx → 轮询登录结果
# 登录成功后 SESSDATA 等持久化到 /etc/bili-login.txt(重启保留),后续请求自动带登录态
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
JAR=/tmp/bili-cookie.txt          # SPI 游客 cookie(临时)
LGN=/etc/bili-login.txt           # 登录令牌(持久化)
CKB=/tmp/bili-cook.txt            # 每次请求合并的 cookie
q() { printf '%s' "$QUERY_STRING" | tr '&' '\n' | grep "^$1=" | head -1 | cut -d= -f2-; }
dec() { printf '%b' "$(printf '%s' "$1" | sed 's/%\([0-9A-Fa-f][0-9A-Fa-f]\)/\\x\1/g; s/+/ /g')"; }
ensure_cookie() {
  [ -s "$JAR" ] && return 0
  curl -s -m 10 'https://api.bilibili.com/x/frontend/finger/spi' -H "User-Agent: $UA" -c "$JAR" >/dev/null 2>&1
}
# 合并 SPI + 登录 cookie 到 CKB(请求统一用 -b "$CKB" -c "$JAR")
COOK() {
  : > "$CKB"
  [ -s "$JAR" ] && cat "$JAR" >> "$CKB"
  [ -s "$LGN" ] && cat "$LGN" >> "$CKB"
}
A=$(q action)
KW=$(dec "$(q kw)")
BV=$(q bvid)
PG=$(q page)
CID=$(q cid)
QKEY=$(q qrcode_key)
[ -z "$PG" ] && PG=1
# wbi 签名(nav 接口拿 img/sub key → mixin → md5);playurl 必须带 wbi 否则流地址无效
wbi_sign() {
  COOK
  NAV=$(curl -s --compressed -m 10 'https://api.bilibili.com/x/web-interface/nav' -H "User-Agent: $UA" -H 'Referer: https://www.bilibili.com/' -b "$CKB" -c "$JAR")
  IMG=$(echo "$NAV" | grep -oE '"img_url":"[^"]*"' | head -1 | sed 's/.*\///; s/\.png".*//')
  SUB=$(echo "$NAV" | grep -oE '"sub_url":"[^"]*"' | head -1 | sed 's/.*\///; s/\.png".*//')
  MIXIN=$(printf '%s%s' "$IMG" "$SUB" | cut -c1-32)
  WTS=$(date +%s)
  QUERY="$1&wts=$WTS"
  WRID=$(printf '%s%s' "$QUERY" "$MIXIN" | md5sum | cut -d' ' -f1)
  echo "$QUERY&w_rid=$WRID"
}
case "$A" in
  spi)
    echo "Content-Type: application/json; charset=utf-8"
    echo ""
    curl -s -m 10 'https://api.bilibili.com/x/frontend/finger/spi' -H "User-Agent: $UA" -c "$JAR"
    ;;
  login_status)
    ensure_cookie
    COOK
    echo "Content-Type: application/json; charset=utf-8"
    echo ""
    curl -s --compressed -m 10 'https://api.bilibili.com/x/web-interface/nav' -H "User-Agent: $UA" -H 'Referer: https://www.bilibili.com/' -b "$CKB" -c "$JAR"
    ;;
  qrcode_gen)
    ensure_cookie
    echo "Content-Type: application/json; charset=utf-8"
    echo ""
    curl -s --compressed -m 10 'https://passport.bilibili.com/x/passport-login/web/qrcode/generate' -H "User-Agent: $UA" -b "$JAR" -c "$JAR"
    ;;
  qrcode_poll)
    ensure_cookie
    if [ -z "$QKEY" ]; then
      echo "Content-Type: text/plain"; echo "Status: 400 Bad Request"; echo ""; echo "need qrcode_key"; exit 1
    fi
    BODY=$(curl -s --compressed -m 10 "https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key=$QKEY" -H "User-Agent: $UA" -b "$JAR" -c "$JAR")
    # code=0 登录成功:从累积的 JAR 中提取登录令牌写入持久文件(去旧换新)
    CODE=$(printf '%s' "$BODY" | grep -oE '"code":[0-9-]*' | head -1 | grep -oE '[0-9-]*')
    if [ "$CODE" = "0" ]; then
      rm -f "$LGN"
      grep -E '\bSESSDATA\b' "$JAR" | tail -1 >> "$LGN" 2>/dev/null
      grep -E '\bDedeUserID\b' "$JAR" | tail -1 >> "$LGN" 2>/dev/null
      grep -E '\bbili_jct\b' "$JAR" | tail -1 >> "$LGN" 2>/dev/null
    fi
    echo "Content-Type: application/json; charset=utf-8"
    echo ""
    printf '%s' "$BODY"
    ;;
  logout)
    rm -f "$LGN"
    echo "Content-Type: text/plain; charset=utf-8"
    echo ""
    echo "ok"
    ;;
  search)
    ensure_cookie
    COOK
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
    # 搜索:B 站对搜索接口间歇风控(HTML 出错页);16 秒窗口内持续重试,成功即返回
    R=""
    END=$(( $(date +%s) + 16 ))
    while [ $(date +%s) -lt $END ]; do
      R=$(curl -s --compressed -m 5 "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=$KW" \
        -H "User-Agent: $UA" -H 'Referer: https://www.bilibili.com/' -b "$CKB" -c "$JAR")
      if printf '%s' "$R" | head -c 1 | grep -q '{'; then
        printf '%s' "$R" > "$CF" 2>/dev/null
        date +%s > "$TS" 2>/dev/null
        printf '%s' "$R"
        exit 0
      fi
      sleep 2
    done
    printf '%s' "$R"
    ;;
  pagelist)
    ensure_cookie
    COOK
    if [ -z "$BV" ]; then
      echo "Content-Type: text/plain"; echo "Status: 400 Bad Request"; echo ""; echo "need bvid"; exit 1
    fi
    echo "Content-Type: application/json; charset=utf-8"
    echo ""
    curl -s --compressed -m 10 "https://api.bilibili.com/x/player/pagelist?bvid=$BV" -H "User-Agent: $UA" -b "$CKB" -c "$JAR"
    ;;
  playurl)
    ensure_cookie
    if [ -z "$CID" ]; then
      if [ -z "$BV" ]; then
        echo "Content-Type: text/plain"; echo "Status: 400 Bad Request"; echo ""; echo "need cid or bvid"; exit 1
      fi
      PL=$(curl -s --compressed -m 10 "https://api.bilibili.com/x/player/pagelist?bvid=$BV" -H "User-Agent: $UA" -b "$CKB" -c "$JAR")
      CID=$(echo "$PL" | grep -oE '"cid":[0-9]*' | sed -n "${PG}p" | grep -oE '[0-9]*')
      [ -z "$CID" ] && CID=$(echo "$PL" | grep -oE '"cid":[0-9]*' | head -1 | grep -oE '[0-9]*')
    fi
    if [ -z "$CID" ]; then
      echo "Content-Type: text/plain"; echo "Status: 404 Not Found"; echo ""; echo "no cid"; exit 1
    fi
    # 参数按 key 排序(bvid<cid<fnval<qn)供 wbi 签名;fmt=mp4 → fnval=0(durl 单文件),默认 dash
    FMT=$(q fmt)
    if [ "$FMT" = "mp4" ]; then QS="bvid=$BV&cid=$CID&fnval=0&qn=64"; else QS="bvid=$BV&cid=$CID&fnval=16&qn=64"; fi
    SIGNED=$(wbi_sign "$QS")
    echo "Content-Type: application/json; charset=utf-8"
    echo ""
    curl -s --compressed -m 10 "https://api.bilibili.com/x/player/playurl?$SIGNED" -H "User-Agent: $UA" -H 'Referer: https://www.bilibili.com/' -b "$CKB" -c "$JAR"
    ;;
  rangetest)
    echo "Content-Type: text/plain"
    echo ""
    echo "HTTP_RANGE=[$HTTP_RANGE]"
    echo "QUERY=[$QUERY_STRING]"
    ;;
  stream)
    LOG=/tmp/bili-stream.log
    echo "$(date '+%m-%d %H:%M:%S') REQ bvid=$BV cid=${CID:-?} rng=$(q rng) ua=${HTTP_USER_AGENT:0:40} ip=${REMOTE_ADDR:-?}" >> "$LOG" 2>/dev/null
    ensure_cookie
    if [ -z "$CID" ]; then
      if [ -z "$BV" ]; then
        echo "Content-Type: text/plain"; echo "Status: 400 Bad Request"; echo ""; echo "need cid or bvid"; exit 1
      fi
      PL=$(curl -s --compressed -m 10 "https://api.bilibili.com/x/player/pagelist?bvid=$BV" -H "User-Agent: $UA" -b "$CKB" -c "$JAR")
      CID=$(echo "$PL" | grep -oE '"cid":[0-9]*' | sed -n "${PG}p" | grep -oE '[0-9]*')
      [ -z "$CID" ] && CID=$(echo "$PL" | grep -oE '"cid":[0-9]*' | head -1 | grep -oE '[0-9]*')
    fi
    if [ -z "$CID" ]; then
      echo "Content-Type: text/plain"; echo "Status: 404 Not Found"; echo ""; echo "no cid"; exit 1
    fi
    # playurl(登录态 + wbi)拿 durl 直链 → curl 伪造 bilibili Referer 流式转发
    QS="bvid=$BV&cid=$CID&fnval=0&qn=64"
    SIGNED=$(wbi_sign "$QS")
    PR=$(curl -s --compressed -m 10 "https://api.bilibili.com/x/player/playurl?$SIGNED" -H "User-Agent: $UA" -H 'Referer: https://www.bilibili.com/' -b "$CKB" -c "$JAR")
    U=$(printf '%s' "$PR" | grep -oE '"url":"[^"]*' | head -1 | sed 's/"url":"//; s/\\u0026/\&/g')
    echo "$(date '+%H:%M:%S') PLAYURL pr_code=$(printf '%s' "$PR" | grep -oE '"code":[0-9-]*' | head -1 | grep -oE '[0-9-]*') url=${U:0:70}" >> "$LOG" 2>/dev/null
    if [ -z "$U" ]; then
      echo "Content-Type: text/plain"; echo "Status: 404 Not Found"; echo ""; echo "no stream url"; exit 1
    fi
    # 探测上游响应头(-r 0-0)拿 Content-Type / 总长度
    HD=/tmp/bili-hdr.txt
    curl -s -o /dev/null -m 15 -D "$HD" -r 0-0 "$U" -H "User-Agent: $UA" -H 'Referer: https://www.bilibili.com/' -b "$CKB"
    echo "$(date '+%H:%M:%S') PROBE $(grep -iE '^HTTP/|^Content-Type:|^Content-Range:|^Content-Length:' "$HD" | tr '\n' ' ' | tr -d '\r' | cut -c1-160)" >> "$LOG" 2>/dev/null
    CT=$(grep -i '^Content-Type:' "$HD" | head -1 | tr -d '\r' | sed 's/^[Cc]ontent-[Tt]ype: *//')
    CTL=$(grep -i '^Content-Range:' "$HD" | head -1 | tr -d '\r' | sed 's/.*bytes [0-9]*-[0-9]*\///')
    [ -z "$CTL" ] && CTL=$(grep -i '^Content-Length:' "$HD" | head -1 | tr -d '\r' | sed 's/^[Cc]ontent-[Ll]ength: *//')
    [ -z "$CT" ] && CT="video/mp4"
    ROPT=""
    # Range:优先取 nginx 传入的 rng 参数(uhttpd 不把 Range 头转 HTTP_RANGE),fallback HTTP_RANGE
    RNG=$(q rng)
    [ -z "$RNG" ] && RNG="$HTTP_RANGE"
    if [ -n "$RNG" ]; then
      # 总长度(探测 Content-Range 或 Content-Length)
      TOTAL=$(grep -i '^Content-Range:' "$HD" | head -1 | tr -d '\r' | sed 's/.*bytes [0-9]*-[0-9]*\///')
      [ -z "$TOTAL" ] && TOTAL=$CTL
      [ -z "$TOTAL" ] && TOTAL=0
      # 解析 bytes=start-end / bytes=start-
      RSTART=$(printf '%s' "$RNG" | sed 's/^[Bb]ytes=//; s/-.*//')
      REND=$(printf '%s' "$RNG" | sed 's/^[Bb]ytes=[0-9]*-//')
      case "$REND" in *[!0-9]*|'') REND="" ;; esac
      if [ -z "$REND" ] || [ "$REND" -ge "$TOTAL" ]; then
        # open-ended 或 end 超界:返回 start 到文件末尾
        CLEN=$(( TOTAL - RSTART ))
        [ "$CLEN" -lt 0 ] && CLEN=0
        REND=$(( TOTAL - 1 ))
        ROPT="-r ${RSTART}-"
      else
        CLEN=$(( REND - RSTART + 1 ))
        [ "$CLEN" -lt 0 ] && CLEN=0
        ROPT="-r ${RSTART}-${REND}"
      fi
      echo "Status: 206 Partial Content"
      echo "Content-Range: bytes $RSTART-$REND/$TOTAL"
      echo "Content-Length: $CLEN"
    else
      [ -n "$CTL" ] && echo "Content-Length: $CTL"
    fi
    echo "Content-Type: $CT"
    echo "Accept-Ranges: bytes"
    echo ""
    curl -s $ROPT "$U" -H "User-Agent: $UA" -H 'Referer: https://www.bilibili.com/' -b "$CKB"
    RC=$?
    echo "$(date '+%H:%M:%S') FWD rc=$RC clen=${CLEN:-$CTL}" >> "$LOG" 2>/dev/null
    exit 0
    ;;
  dm)
    ensure_cookie
    COOK
    if [ -z "$CID" ]; then
      if [ -z "$BV" ]; then
        echo "Content-Type: text/plain"; echo "Status: 400 Bad Request"; echo ""; echo "need cid or bvid"; exit 1
      fi
      # pagelist → cid(第 PG 个分P)
      PL=$(curl -s --compressed -m 10 "https://api.bilibili.com/x/player/pagelist?bvid=$BV" -H "User-Agent: $UA" -b "$CKB" -c "$JAR")
      CID=$(echo "$PL" | grep -oE '"cid":[0-9]*' | sed -n "${PG}p" | grep -oE '[0-9]*')
      [ -z "$CID" ] && CID=$(echo "$PL" | grep -oE '"cid":[0-9]*' | head -1 | grep -oE '[0-9]*')
    fi
    if [ -z "$CID" ]; then
      echo "Content-Type: text/plain"; echo "Status: 404 Not Found"; echo ""; echo "no cid"; exit 1
    fi
    echo "Content-Type: application/xml; charset=utf-8"
    echo ""
    curl -s --compressed -m 15 "https://api.bilibili.com/x/v1/dm/list.so?oid=$CID" -H "User-Agent: $UA" -b "$CKB" -c "$JAR"
    ;;
  *)
    echo "Content-Type: text/plain"; echo "Status: 400 Bad Request"; echo ""; echo "unknown action"; exit 1;;
esac
