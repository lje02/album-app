#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; exit 1; }
title()   { echo -e "\n${BOLD}${CYAN}  ── $* ──${RESET}"; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

prompt_required() {
    local var_name="$1" prompt="$2" value=""
    while [[ -z "$value" ]]; do
        read -rp "  ${BOLD}${prompt}${RESET}: " value
        [[ -z "$value" ]] && echo -e "  ${RED}⚠ 此项不能为空，请重新输入${RESET}"
    done
    printf -v "$var_name" '%s' "$value"
}

prompt_optional() {
    local var_name="$1" prompt="$2" default="$3" value=""
    read -rp "  ${prompt} [默认: ${default}]: " value
    printf -v "$var_name" '%s' "${value:-$default}"
}

check_docker() {
    info "检查 Docker 环境..."
    command -v docker &>/dev/null      || error "未检测到 Docker，请先安装：curl -fsSL https://get.docker.com | sh"
    docker compose version &>/dev/null || error "未检测到 docker compose 插件，请升级 Docker。"
    success "Docker 环境正常。"
}

write_dockerfile() {
    local dir="$1"
    cat > "$dir/Dockerfile" <<'DOCKERFILE'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
DOCKERFILE
}

start_bot() {
    local dir="$1" service="$2" display_name="$3"
    echo
    info "构建 Docker 镜像（首次约需 1-2 分钟）..."
    docker compose -f "$dir/docker-compose.yml" build
    info "启动容器..."
    docker compose -f "$dir/docker-compose.yml" up -d
    echo
    success "🎉  ${display_name} 已成功启动！"
    echo
    echo -e "  ${BOLD}── 常用命令 ──────────────────────────────────────────────${RESET}"
    echo -e "  查看日志:   ${CYAN}docker compose -f ${dir}/docker-compose.yml logs -f${RESET}"
    echo -e "  停止:       ${CYAN}docker compose -f ${dir}/docker-compose.yml stop${RESET}"
    echo -e "  重启:       ${CYAN}docker compose -f ${dir}/docker-compose.yml restart${RESET}"
    echo -e "  卸载:       ${CYAN}bash setup.sh --uninstall${RESET}"
    echo -e "  ─────────────────────────────────────────────────────────"
}

show_banner() {
    clear
    echo -e "${BOLD}${CYAN}"
    echo "  ████████╗ ██████╗     ██████╗  ██████╗ ████████╗"
    echo "     ██╔══╝██╔════╝     ██╔══██╗██╔═══██╗╚══██╔══╝"
    echo "     ██║   ██║  ███╗    ██████╔╝██║   ██║   ██║   "
    echo "     ██║   ██║   ██║    ██╔══██╗██║   ██║   ██║   "
    echo "     ██║   ╚██████╔╝    ██████╔╝╚██████╔╝   ██║   "
    echo "     ╚═╝    ╚═════╝     ╚═════╝  ╚═════╝    ╚═╝   "
    echo -e "${RESET}"
    echo -e "  ${BOLD}Telegram 下载机器人  —  一键安装向导${RESET}"
    echo -e "  ─────────────────────────────────────────────"
    echo
}

# ══════════════════════════════════════════════════════════════
#  卸载流程
# ══════════════════════════════════════════════════════════════
do_uninstall() {
    show_banner
    echo -e "${RED}${BOLD}  ⚠️  卸载向导${RESET}"
    echo

    local dir="$ROOT_DIR"

    if [[ ! -f "$dir/docker-compose.yml" ]]; then
        warn "未检测到已安装的机器人。"
        exit 0
    fi

    echo -e "  ${RED}卸载: 📥 下载机器人${RESET}"
    read -rp "  确认？(y/N): " confirm
    [[ "${confirm,,}" == "y" ]] || { warn "已取消。"; exit 0; }

    docker compose -f "$dir/docker-compose.yml" down --rmi local 2>/dev/null || true

    read -rp "  删除数据文件（下载目录/数据库）？(y/N): " del_data
    if [[ "${del_data,,}" == "y" ]]; then
        rm -rf "$dir/downloads" "$dir/session" "$dir"/*.db 2>/dev/null || true
        success "数据已删除。"
    fi

    rm -f "$dir/docker-compose.yml" "$dir/Dockerfile" 2>/dev/null || true

    read -rp "  删除配置文件 .env？(y/N): " del_env
    [[ "${del_env,,}" == "y" ]] && rm -f "$dir/.env" && success "配置已删除。"

    success "卸载完成。"
    echo
    exit 0
}

# ══════════════════════════════════════════════════════════════
#  安装：下载机器人
# ══════════════════════════════════════════════════════════════
install_downloader() {
    local dir="$ROOT_DIR"

    title "配置下载机器人参数"
    echo -e "  获取 API_ID / API_HASH → ${CYAN}https://my.telegram.org${RESET}"
    echo -e "  获取 BOT_TOKEN         → 与 ${CYAN}@BotFather${RESET} 对话"
    echo

    local IN_API_ID IN_API_HASH IN_BOT_TOKEN IN_ALLOWED
    local IN_CONCURRENT IN_BY_DATE IN_PAGE_SIZE
    prompt_required IN_API_ID    "API_ID      (纯数字)"
    prompt_required IN_API_HASH  "API_HASH    (32位字符串)"
    prompt_required IN_BOT_TOKEN "BOT_TOKEN   (xxx:yyy 格式)"
    prompt_required IN_ALLOWED   "ALLOWED_USERS (用户ID，多个用逗号分隔)"

    echo
    title "可选配置（直接回车使用默认值）"
    prompt_optional IN_CONCURRENT "最大同时下载数"               "3"
    prompt_optional IN_BY_DATE    "按日期归档子目录 (true/false)" "true"
    prompt_optional IN_PAGE_SIZE  "文件列表每页条数"              "8"

    [[ "$IN_API_ID" =~ ^[0-9]+$ ]] || error "API_ID 必须是纯数字"

    cat > "$dir/.env" <<EOF
API_ID=${IN_API_ID}
API_HASH=${IN_API_HASH}
BOT_TOKEN=${IN_BOT_TOKEN}
ALLOWED_USERS=${IN_ALLOWED}
DOWNLOAD_ROOT=/app/downloads
CONCURRENT_DOWNLOADS=${IN_CONCURRENT}
ORGANIZE_BY_DATE=${IN_BY_DATE}
PAGE_SIZE=${IN_PAGE_SIZE}
PROGRESS_UPDATE_SEC=2.0
DB_PATH=/app/tg_downloader.db
EOF

    [[ -f "$dir/bot.py" ]] || error "找不到 bot.py，请确认文件在脚本执行目录下。"

    # 【修复 2.2】补全写入 requirements.txt 的依赖库
    cat > "$dir/requirements.txt" <<'REQ'
pyrogram==2.0.106
tgcrypto
python-dotenv
aiohttp
beautifulsoup4
REQ

    write_dockerfile "$dir"

    cat > "$dir/docker-compose.yml" <<YAML
services:
  tg_downloader:
    build: .
    container_name: tg_downloader
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./downloads:/app/downloads
      - ./session:/app/session
      - ./tg_downloader.db:/app/tg_downloader.db
YAML

    mkdir -p "$dir/downloads" "$dir/session"
    touch "$dir/tg_downloader.db"

    start_bot "$dir" "tg_downloader" "📥 下载机器人"
    echo -e "  下载文件保存在: ${BOLD}$dir/downloads/${RESET}"
    echo
}

# ══════════════════════════════════════════════════════════════
#  主入口
# ══════════════════════════════════════════════════════════════
[[ "${1:-}" == "--uninstall" ]] && do_uninstall

show_banner
check_docker

install_downloader
