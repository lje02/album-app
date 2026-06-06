#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  Telegram 下载机器人  —  傻瓜一键安装 / 卸载脚本
#  用法:
#    安装:  bash setup.sh
#    卸载:  bash setup.sh --uninstall
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

# ── 颜色 ──────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; exit 1; }

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$INSTALL_DIR/.env"
COMPOSE_FILE="$INSTALL_DIR/docker-compose.yml"
SERVICE_NAME="tg_downloader"

# ══════════════════════════════════════════════════════════════
#  卸载模式
# ══════════════════════════════════════════════════════════════
if [[ "${1:-}" == "--uninstall" ]]; then
    echo
    echo -e "${RED}${BOLD}  ⚠️  即将卸载 Telegram 下载机器人${RESET}"
    echo -e "  安装目录: ${INSTALL_DIR}"
    echo
    read -rp "  确认卸载？将停止容器并删除镜像 (y/N): " confirm
    [[ "${confirm,,}" == "y" ]] || { echo "已取消。"; exit 0; }

    echo
    info "停止并删除容器..."
    if [[ -f "$COMPOSE_FILE" ]]; then
        docker compose -f "$COMPOSE_FILE" down --rmi local --volumes 2>/dev/null || true
    else
        docker rm -f "$SERVICE_NAME" 2>/dev/null || true
    fi

    echo
    read -rp "  是否同时删除所有下载文件和数据库？(y/N): " del_data
    if [[ "${del_data,,}" == "y" ]]; then
        rm -rf "$INSTALL_DIR/downloads" "$INSTALL_DIR/session" \
               "$INSTALL_DIR/tg_downloader.db" 2>/dev/null || true
        success "下载文件和数据库已删除。"
    else
        warn "下载文件保留在 $INSTALL_DIR/downloads"
    fi

    rm -f "$COMPOSE_FILE" "$INSTALL_DIR/Dockerfile" \
          "$INSTALL_DIR/requirements.txt" 2>/dev/null || true

    success "卸载完成！"
    echo
    read -rp "  是否删除配置文件 .env？(y/N): " del_env
    [[ "${del_env,,}" == "y" ]] && rm -f "$ENV_FILE" && success ".env 已删除。"
    echo
    exit 0
fi

# ══════════════════════════════════════════════════════════════
#  安装流程
# ══════════════════════════════════════════════════════════════
clear
echo -e "${BOLD}${CYAN}"
echo "  ████████╗ ██████╗     ██████╗  ██████╗ ████████╗"
echo "     ██╔══╝██╔════╝     ██╔══██╗██╔═══██╗╚══██╔══╝"
echo "     ██║   ██║  ███╗    ██████╔╝██║   ██║   ██║   "
echo "     ██║   ██║   ██║    ██╔══██╗██║   ██║   ██║   "
echo "     ██║   ╚██████╔╝    ██████╔╝╚██████╔╝   ██║   "
echo "     ╚═╝    ╚═════╝     ╚═════╝  ╚═════╝    ╚═╝   "
echo -e "${RESET}"
echo -e "  ${BOLD}Telegram 自动下载机器人  —  一键安装向导${RESET}"
echo -e "  ─────────────────────────────────────────────"
echo

# ── 检查 Docker ───────────────────────────────────────────────
info "检查 Docker 环境..."
command -v docker &>/dev/null      || error "未检测到 Docker，请先安装 Docker。"
docker compose version &>/dev/null || error "未检测到 docker compose 插件，请升级 Docker。"
success "Docker 环境正常。"
echo

# ══════════════════════════════════════════════════════════════
#  交互式参数收集
# ══════════════════════════════════════════════════════════════
echo -e "${BOLD}  📋 请填写以下参数（必填项不能为空）${RESET}"
echo -e "  获取 API_ID / API_HASH → https://my.telegram.org"
echo -e "  获取 BOT_TOKEN         → 与 @BotFather 对话"
echo

prompt_required() {
    local var_name="$1" prompt="$2" value=""
    while [[ -z "$value" ]]; do
        read -rp "  ${BOLD}${prompt}${RESET}: " value
        [[ -z "$value" ]] && echo -e "  ${RED}⚠ 此项不能为空，请重新输入${RESET}"
    done
    eval "$var_name='$value'"
}

prompt_optional() {
    local var_name="$1" prompt="$2" default="$3"
    read -rp "  ${prompt} [默认: ${default}]: " value
    eval "$var_name='${value:-$default}'"
}

prompt_required  IN_API_ID       "API_ID      (纯数字)"
prompt_required  IN_API_HASH     "API_HASH    (32位字符串)"
prompt_required  IN_BOT_TOKEN    "BOT_TOKEN   (xxx:yyy 格式)"
prompt_required  IN_ALLOWED      "ALLOWED_USERS (你的 Telegram 用户 ID，多个用逗号分隔)"

echo
echo -e "  ${BOLD}── 可选配置 ──────────────────────────────────────${RESET}"
prompt_optional  IN_DOWNLOAD_ROOT  "下载保存路径 (容器内)" "/app/downloads"
prompt_optional  IN_CONCURRENT     "最大同时下载数"         "3"
prompt_optional  IN_BY_DATE        "按日期归档子目录 (true/false)" "true"
prompt_optional  IN_PAGE_SIZE      "文件列表每页条数"        "8"

echo

# ── 验证 API_ID 是纯数字 ──────────────────────────────────────
[[ "$IN_API_ID" =~ ^[0-9]+$ ]] || error "API_ID 必须是纯数字，实际输入：$IN_API_ID"

# ══════════════════════════════════════════════════════════════
#  生成配置文件
# ══════════════════════════════════════════════════════════════
info "生成 .env 配置文件..."
cat > "$ENV_FILE" <<EOF
# ── 必填 ──────────────────────────────────────────────────────
API_ID=${IN_API_ID}
API_HASH=${IN_API_HASH}
BOT_TOKEN=${IN_BOT_TOKEN}
ALLOWED_USERS=${IN_ALLOWED}

# ── 可选 ──────────────────────────────────────────────────────
DOWNLOAD_ROOT=${IN_DOWNLOAD_ROOT}
CONCURRENT_DOWNLOADS=${IN_CONCURRENT}
ORGANIZE_BY_DATE=${IN_BY_DATE}
PAGE_SIZE=${IN_PAGE_SIZE}
PROGRESS_UPDATE_SEC=2.0
DB_PATH=/app/tg_downloader.db
EOF
success ".env 已生成。"

# ── 生成 Dockerfile ───────────────────────────────────────────
info "生成 Dockerfile..."
cat > "$INSTALL_DIR/Dockerfile" <<'DOCKERFILE'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p downloads session

CMD ["python", "bot.py"]
DOCKERFILE

# ── 生成 requirements.txt（若不存在）────────────────────────
if [[ ! -f "$INSTALL_DIR/requirements.txt" ]]; then
    info "生成 requirements.txt..."
    cat > "$INSTALL_DIR/requirements.txt" <<'REQ'
pyrogram==2.0.106
tgcrypto
python-dotenv
REQ
fi

# ── 生成 docker-compose.yml ───────────────────────────────────
info "生成 docker-compose.yml..."
cat > "$COMPOSE_FILE" <<YAML
version: "3.9"

services:
  ${SERVICE_NAME}:
    build: .
    container_name: ${SERVICE_NAME}
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./downloads:/app/downloads
      - ./session:/app/session
      - ./tg_downloader.db:/app/tg_downloader.db
YAML

# ── 创建必要目录 / 文件 ───────────────────────────────────────
mkdir -p "$INSTALL_DIR/downloads" "$INSTALL_DIR/session"
touch "$INSTALL_DIR/tg_downloader.db"
success "目录结构已创建。"

# ══════════════════════════════════════════════════════════════
#  构建并启动
# ══════════════════════════════════════════════════════════════
echo
info "构建 Docker 镜像（首次可能需要 1-3 分钟）..."
docker compose -f "$COMPOSE_FILE" build

echo
info "启动机器人容器..."
docker compose -f "$COMPOSE_FILE" up -d

echo
success "🎉  机器人已成功启动！"
echo
echo -e "  ${BOLD}── 常用命令 ─────────────────────────────────────────────${RESET}"
echo -e "  查看日志:    ${CYAN}docker compose logs -f ${SERVICE_NAME}${RESET}"
echo -e "  停止机器人:  ${CYAN}docker compose stop ${SERVICE_NAME}${RESET}"
echo -e "  重启机器人:  ${CYAN}docker compose restart ${SERVICE_NAME}${RESET}"
echo -e "  卸载机器人:  ${CYAN}bash setup.sh --uninstall${RESET}"
echo -e "  ─────────────────────────────────────────────────────────"
echo -e "  下载文件保存在: ${BOLD}$INSTALL_DIR/downloads/${RESET}"
echo
