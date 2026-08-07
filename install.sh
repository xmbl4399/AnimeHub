#!/bin/sh
# 番剧库一键安装脚本(路由器端执行,需 root;两个 ipk 需与本脚本同目录)
# 用法:sh install.sh [下载目录] [媒体根目录]
#   不传参数时自动检测存储分区;示例:sh install.sh /mnt/mmcblk0p7/Aria2 /mnt/mmcblk0p7
echo "=== 番剧库 一键安装 ==="

# [1/4] 依赖(aria2/nginx/luci,已装则跳过)
echo "[1/4] 安装依赖 ..."
opkg update >/dev/null 2>&1 || true
for p in aria2 luci-app-aria2 nginx luci-base; do
  opkg list-installed 2>/dev/null | grep -q "^$p " || opkg install "$p" || { echo "安装 $p 失败,请检查网络/软件源"; exit 1; }
done

# [2/4] 存储检测与目录准备
echo "[2/4] 检测存储 ..."
DEF=$(ls -d /mnt/mmcblk* /mnt/sd* 2>/dev/null | head -1)
ROOT=${2:-$DEF}
DIR=${1:-$ROOT/Aria2}
if [ -z "$ROOT" ]; then
  echo "未找到存储分区,请手动指定: sh install.sh /mnt/xxx/Aria2 /mnt/xxx"
  exit 1
fi
echo "媒体根: $ROOT"
echo "下载目录: $DIR"
mkdir -p "$DIR" "$ROOT/.mikan-cache" || { echo "创建目录失败,检查存储是否挂载/可写"; exit 1; }
if grep -q '^aria2:' /etc/passwd 2>/dev/null; then
  chown aria2:aria2 "$DIR" 2>/dev/null && echo "下载目录属主已设为 aria2"
fi

# [3/4] 安装 ipk
echo "[3/4] 安装 ipk ..."
opkg install ./kwrt-mediahub_1.0.0-1_all.ipk || { echo "安装 kwrt-mediahub 失败"; exit 1; }
opkg install ./luci-app-mediahub_1.0.0-1_all.ipk || { echo "安装 luci-app-mediahub 失败"; exit 1; }

# [4/4] 写入默认路径(之后可在 LuCI「番剧库」页修改)
echo "[4/4] 写入默认路径 ..."
uci set mediahub.@main[0].dir="$DIR"
uci set mediahub.@main[0].root="$ROOT"
uci commit mediahub

IP=$(uci get network.lan.ipaddr 2>/dev/null | cut -d/ -f1)
echo "=== 安装完成 ==="
echo "下一步:"
echo "  1. 打开 LuCI → 服务 → 番剧库,确认下载目录/媒体根,点「立即应用」"
echo "  2. 打开 http://${IP:-<路由器IP>}/hub.html 使用"
echo "  3. 若 FileBrowser 密码不是 admin,在「番剧库」页填写"
exit 0
