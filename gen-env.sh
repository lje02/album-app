#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  Telegram 下载机器人 · 配置模板生成脚本
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

# ── 生成随机强密码 ──
generate_random_password() {
    # 生成 16 位随机密码（包含大小写字母、数字、特殊字符）
    openssl rand -base64 12 | tr -d "=+/" | cut -c1-16
}

# ── 生成 SHA256 哈希 ──
generate_password_hash() {
    echo -n "$1" | sha256sum | awk '{print $1}'
}

# ── 如果 .env 已存在，备份后退出 ──
if [[ -f "$ENV_FILE" ]]; then
    BACKUP_FILE="${ENV_FILE}.example.$(date +%Y%m%d%H%M%S)"
    cp "$ENV_FILE" "$BACKUP_FILE"
    echo "⚠️  .env 已存在，已备份为 $BACKUP_FILE"
    exit 0
fi

# ── 生成随机密码和 JWT Secret ──
WEB_PASSWORD=$(generate_random_password)
WEB_PASSWORD_HASH=$(generate_password_hash "$WEB_PASSWORD")
JWT_SECRET=$(openssl rand -base64 32)

# ── 生成 .env 模板 ──
cat > "$ENV_FILE" << EOF
# ═══════════════════════════════════════════════════════════════
#  Telegram 自动下载机器人 · 配置文件 v3.1 Enhanced
# ═══════════════════════════════════════════════════════════════

# ── Telegram API 凭据（必填）────────────────────────────────
# 获取地址：https://my.telegram.org/apps（登录后创建 App）
API_ID=YOUR_API_ID
API_HASH=YOUR_API_HASH

# ── Bot Token（必填）──────────────────────────────────────
# 获取方式：在 Telegram 找 @BotFather → /newbot
BOT_TOKEN=YOUR_BOT_TOKEN

# ── 下载配置────────────────────────────────────────────────
# 下载文件保存的根目录
DOWNLOAD_ROOT=./downloads

# 是否按日期（YYYY-MM-DD）子目录归档
ORGANIZE_BY_DATE=true

# 日志目录
LOG_DIR=./logs

# ── 用户白名单────────────────────────────────────────────────
# 留空 = 所有人可用；多个 ID 用逗号分隔
# 获取自己的 user_id：在 Telegram 找 @userinfobot 发任意消息
ALLOWED_USERS=

# ── 进度显示────────────────────────────────────────────────
# 下载进度更新间隔（秒）
PROGRESS_UPDATE_SEC=2.0

# ── 分页配置────────────────────────────────────────────────
# 浏览文件时每页显示的条数
PAGE_SIZE=8

# ── 数据库配置──────────────────────────────────────────────
# SQLite 数据库路径
DB_PATH=./tg_downloader.db

# ════════════════════════════════════════════���═══════════════
#  Web 管理界面配置
# ════════════════════════════════════════════════════════════

# Web 服务端口
WEB_PORT=5000

# Web 管理界面密码
# ⚠️  重要：请修改为自己的密码！默认密码已随机生成
WEB_PASSWORD=$WEB_PASSWORD

# JWT 密钥（用于生成会话令牌）
# ⚠️  重要：生成环境请更改此值
JWT_SECRET=$JWT_SECRET

# 是否启用 HTTPS（生产环境推荐）
# DEBUG=false

# ════════════════════════════════════════════════════════════
#  性能优化配置
# ════════════════════════════════════════════════════════════

# 并发下载数（同时下载的最大文件数）
# 设置太高会导致内存占用过大；建议 1-5
CONCURRENT_DOWNLOADS=3

# 单个下载超时时间（秒）
DOWNLOAD_TIMEOUT_SEC=3600

# 下载失败最大重试次数
# 使用指数退避（2^n 秒）重试间隔
MAX_RETRIES=3

# 重试退避基数
# 重���间隔 = RETRY_BACKOFF_BASE ^ 重试次数
RETRY_BACKOFF_BASE=2.0

# 最小可用磁盘空间（MB）
# 低于此值时停止下载
MIN_FREE_SPACE_MB=100

# 内存使用率警告阈值（%）
# 超过此值时在菜单中显示警告
MEMORY_WARN_PERCENT=80

# 数据库备份保留天数（0=禁用）
# 自动备份数据库，保留 N*7 天的备份
DB_BACKUP_DAYS=1

# 自动清理过期文件（天数，0=禁用）
# 删除超过 N 天未修改的下载文件
CLEANUP_OLD_FILES_DAYS=0

# ════════════════════════════════════════════════════════════
#  ⚠️  安全建议
# ════════════════════════════════════════════════════════════
# 1. 请修改 WEB_PASSWORD 为你自己的强密码
#    或使用密码哈希验证（更安全）
#
# 2. 生成密码哈希：
#    echo -n "your-password" | sha256sum
#    然后将哈希值填写到 WEB_PASSWORD_HASH
#
# 3. 修改 JWT_SECRET 为随机值（已自动生成）
#
# 4. 生产环境建议：
#    • 使用 HTTPS
#    • 启用防火墙，限制 Web 端口访问
#    • 定期修改密码
#    • 启用日志审计
#
# ════════════════════════════════════════════════════════════
#  使用说明
# ════════════════════════════════════════════════════════════
# Web 管理界面：http://localhost:5000
# 默认用户名：无（仅需要密码）
# 默认密码：$WEB_PASSWORD
#
# 修改密码步骤：
# 1. 编辑 .env 文件，修改 WEB_PASSWORD
# 2. 重启 Web 服务
#    或者
# 1. 使用密码哈希验证
# 2. 生成密码哈希：echo -n "newpass" | sha256sum
# 3. 更新 WEB_PASSWORD_HASH
# 4. 删除或注释掉 WEB_PASSWORD
#
# ════════════════════════════════════════════════════════════
EOF

chmod 600 "$ENV_FILE"

echo ""
echo "✅ .env 模板已生成：$ENV_FILE"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔐 Web 管理界面凭证"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📍 地址：http://localhost:5000"
echo "🔑 密码：$WEB_PASSWORD"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  请妥善保管此密码，或修改为你自己的强密码"
echo ""
echo "📋 下一步："
echo "  1. 编辑 .env 文件"
echo "  2. 填写 API_ID、API_HASH、BOT_TOKEN（必填）"
echo "  3. 修改 WEB_PASSWORD 为你自己的密码（可选）"
echo "  4. 启动服务"
echo ""
