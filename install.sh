#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  Telegram 下载机器人 · 增强版 v3.1 · 一键部署脚本
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

# ── 颜色 & 输出工具 ───────────────────────────────────────────
R='\033[0;31m' G='\033[0;32m' Y='\033[0;33m'
B='\033[0;34m' C='\033[0;36m' W='\033[1;37m' N='\033[0m'
BOLD='\033[1m'

ok()   { echo -e "${G}  ✔  ${N}$*"; }
info() { echo -e "${B}  ℹ  ${N}$*"; }
warn() { echo -e "${Y}  ⚠  ${N}$*"; }
err()  { echo -e "${R}  ✘  ${N}$*" >&2; }
die()  { err "$*"; exit 1; }
sep()  { echo -e "${B}──────────────────────────────────────────────────${N}"; }

# ── 横幅 ─────────────────────────────────────────────────────
clear
echo -e "${C}${BOLD}"
cat << 'BANNER'
  ╔════════════════════════════════════════════════════════╗
  ║   Telegram 下载机器人 · 增强版 v3.1                    ║
  ║   Bot + Web 管理 + 在线播放 · 一键部署                ║
  ╚════════════════════════════════════════════════════════╝
BANNER
echo -e "${N}"
sep

# ── 脚本位置 & 安装目录 ───────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$SCRIPT_DIR"

# ── 全局变量 ─────────────────────────────────────────────────
PYTHON=""
VENV_DIR="$INSTALL_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"
SUDO=""
RUN_BOT=true
RUN_WEB=true

# ═══════════════════════════════════════════════════════════════
#  STEP 1 · 检测环境
# ═══════════════════════════════════════════════════════════════
echo -e "\n${W}${BOLD}[1/7] 环境检测${N}"
sep

# ── 检测操作系统 ──────────────────────────────────────────────
detect_os() {
  if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macos"; return
  fi
  if [[ -f /etc/os-release ]]; then
    source /etc/os-release
    case "${ID:-}" in
      ubuntu|debian|linuxmint|pop)              echo "debian"  ;;
      centos|rhel|fedora|rocky|almalinux)       echo "redhat"  ;;
      arch|manjaro|endeavouros)                 echo "arch"    ;;
      *)                                        echo "unknown" ;;
    esac
  else
    echo "unknown"
  fi
}

OS=$(detect_os)
info "操作系统：$(uname -s) / 发行版：$OS"

# ── 权限检测 ──────────────────────────────────────────────────
if [[ $EUID -eq 0 ]]; then
  info "以 root 身份运行"
else
  info "以普通用户运行（sudo 将按需调用）"
  command -v sudo &>/dev/null && SUDO="sudo"
fi

# ── 检测 Docker ────────────────────────────────────────────
has_docker=false
if command -v docker &>/dev/null && command -v docker-compose &>/dev/null; then
  ok "已安装 Docker 和 Docker Compose"
  has_docker=true
else
  warn "未安装 Docker，将使用本地 Python 运行"
fi

# ── 检测 FFmpeg（可选，用于视频缩略图） ──────────────────────
has_ffmpeg=false
if command -v ffmpeg &>/dev/null && command -v ffprobe &>/dev/null; then
  ok "已安装 FFmpeg（支持视频缩略图）"
  has_ffmpeg=true
else
  warn "未安装 FFmpeg（可选，用于生成视频缩略图）"
fi

# ── Python 版本检测 ────────────────────────────────────────
find_python() {
  for cmd in python3.11 python3.10 python3.9 python3 python; do
    command -v "$cmd" &>/dev/null || continue
    read -r major minor < <("$cmd" -c "import sys; v=sys.version_info; print(v.major, v.minor)" 2>/dev/null) || continue
    if (( major > 3 || ( major == 3 && minor >= 9 ) )); then
      echo "$cmd"; return 0
    fi
  done
  return 1
}

if PYTHON=$(find_python); then
  py_ver=$("$PYTHON" -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}.{v.micro}')")
  ok "Python $py_ver"
else
  die "Python 3.9+ 未找到，请先安装"
fi

# ═══════════════════════════════════════════════════════════════
#  STEP 2 · 选择启动方式
# ═══════════════════════════════════════════════════════════════
echo -e "\n${W}${BOLD}[2/7] 选择启动方式${N}"
sep
echo -e "\n  ${Y}您要启动什么？${N}"
echo -e "  ${C}1${N}  Bot + Web（推荐，完整功能）"
echo -e "  ${C}2${N}  仅启动 Bot（只下载功能）"
echo -e "  ${C}3${N}  仅启动 Web（只管理功能）\n"

read -rp "  请选择 [1/2/3]: " COMPONENT_CHOICE

case "$COMPONENT_CHOICE" in
  1) RUN_BOT=true; RUN_WEB=true ;;
  2) RUN_BOT=true; RUN_WEB=false ;;
  3) RUN_BOT=false; RUN_WEB=true ;;
  *) die "无效选择" ;;
esac

if [[ "$RUN_BOT" == true ]] && [[ "$RUN_WEB" == true ]]; then
  ok "启动模式：Bot + Web（完整）"
elif [[ "$RUN_BOT" == true ]]; then
  ok "启动模式：仅 Bot（后台下载）"
else
  ok "启动模式：仅 Web（文件管理）"
fi

# ═══════════════════════════════════════════════════════════════
#  STEP 3 · 选择部署方式
# ═══════════════════════════════════════════════════════════════
echo -e "\n${W}${BOLD}[3/7] 选择部署方式${N}"
sep
echo -e "\n  ${Y}选择部署方式：${N}"
[[ "$has_docker" == true ]] && echo -e "  ${C}1${N}  Docker Compose（推荐，最简单）"
echo -e "  ${C}2${N}  本地运行（简单快速）"
echo -e "  ${C}3${N}  Supervisor（生产环境）"
echo -e "  ${C}4${N}  Systemd（Linux 系统）\n"

read -rp "  请选择 [1/2/3/4]: " DEPLOY_METHOD

case "$DEPLOY_METHOD" in
  1)
    if [[ "$has_docker" != true ]]; then
      warn "Docker 未安装，无法使用此方法"
      exit 1
    fi
    DEPLOY_TYPE="docker"
    ;;
  2) DEPLOY_TYPE="local" ;;
  3) DEPLOY_TYPE="supervisor" ;;
  4) DEPLOY_TYPE="systemd" ;;
  *) die "无效选择" ;;
esac

ok "部署方式：$DEPLOY_TYPE"

# ═══════════════════════════════════════════════════════════════
#  STEP 4 · 配置文件
# ═══════════════════════════════════════════════════════════════
echo -e "\n${W}${BOLD}[4/7] 配置文件${N}"
sep

if [[ ! -f "$INSTALL_DIR/.env" ]]; then
  info "生成 .env 配置文件"
  bash "$INSTALL_DIR/gen-env.sh"
  warn "请编辑 .env 文件，填写必要信息"
  read -rp "  编辑完成后按 Enter 继续..."
else
  ok ".env 文件已存在"
  read -rp "  是否重新生成？ [y/N]: " REGEN
  if [[ "$REGEN" == "y" ]]; then
    bash "$INSTALL_DIR/gen-env.sh"
    read -rp "  编辑完成后按 Enter 继续..."
  fi
fi

# ═══════════════════════════════════════════════════════════════
#  STEP 5 · 安装依赖
# ═══════════════════════════════════════════════════════════════
if [[ "$DEPLOY_TYPE" != "docker" ]]; then
  echo -e "\n${W}${BOLD}[5/7] 安装 Python 依赖${N}"
  sep

  if [[ ! -d "$VENV_DIR" ]]; then
    info "创建虚拟环境"
    "$PYTHON" -m venv "$VENV_DIR"
    ok "虚拟环境已创建"
  fi

  source "$VENV_DIR/bin/activate"
  "$VENV_PIP" install --upgrade pip -q

  info "安装依赖包"
  "$VENV_PIP" install -r "$INSTALL_DIR/requirements-enhanced.txt" -q

  ok "依赖安装完成"
else
  echo -e "\n${W}${BOLD}[5/7] Docker 准备${N}"
  sep
  ok "Docker 自动管理依赖"
fi

# ═══════════════════════════════════════════════════════════════
#  STEP 6 · FFmpeg 检查
# ═══════════════════════════════════════════════════════════════
if [[ "$RUN_WEB" == true ]]; then
  echo -e "\n${W}${BOLD}[6/7] 可选依赖检查${N}"
  sep
  
  if [[ "$has_ffmpeg" == false ]]; then
    warn "未安装 FFmpeg（用于视频缩略图和获取时长）"
    echo -e "\n  ${Y}是否安装 FFmpeg？${N} [y/N]"
    read -rp "  " INSTALL_FFMPEG
    
    if [[ "$INSTALL_FFMPEG" == "y" ]]; then
      case "$OS" in
        debian)
          info "执行: sudo apt-get install ffmpeg"
          $SUDO apt-get update && $SUDO apt-get install -y ffmpeg || warn "安装失败"
          ;;
        redhat)
          info "执行: sudo yum install ffmpeg"
          $SUDO yum install -y ffmpeg || warn "安装失败"
          ;;
        arch)
          info "执行: sudo pacman -S ffmpeg"
          $SUDO pacman -S --noconfirm ffmpeg || warn "安装失败"
          ;;
        macos)
          if command -v brew &>/dev/null; then
            info "执行: brew install ffmpeg"
            brew install ffmpeg || warn "安装失败"
          else
            warn "请先安装 Homebrew，然后运行: brew install ffmpeg"
          fi
          ;;
      esac
    fi
  fi
else
  echo -e "\n${W}${BOLD}[6/7] 部署配置${N}"
  sep
fi

# ════════��══════════════════════════════════════════════════════
#  STEP 7 · 生成启动脚本
# ═══════════════════════════════════════════════════════════════
echo -e "\n${W}${BOLD}[7/7] 部署完成${N}"
sep

case "$DEPLOY_TYPE" in
  docker)
    ok "Docker 部署已准备"
    echo -e "\n  ${W}启动命令：${N}"
    echo -e "  ${C}docker-compose up -d${N}"
    echo -e "\n  ${W}查看日志：${N}"
    echo -e "  ${C}docker-compose logs -f${N}"
    echo -e "\n  ${W}停止服务：${N}"
    echo -e "  ${C}docker-compose down${N}"
    ;;

  local)
    ok "本地部署已准备"
    echo -e "\n  ${W}启动 Bot 和 Web：${N}"
    echo -e "  ${C}source venv/bin/activate${N}"
    echo -e "  ${C}python bot-enhanced.py &${N}"
    echo -e "  ${C}python web_api.py${N}"
    
    if [[ "$RUN_BOT" == true ]] && [[ "$RUN_WEB" == true ]]; then
      echo -e "\n  ${W}或使用一键启动脚本：${N}"
      cat > "$INSTALL_DIR/start.sh" << 'SCRIPT'
#!/bin/bash
source venv/bin/activate
echo "🤖 启动 Bot..."
nohup python bot-enhanced.py > logs/bot.log 2>&1 &
BOT_PID=$!
echo "✅ Bot 已启动 (PID: $BOT_PID)"

sleep 2

echo "🌐 启动 Web 服务..."
nohup python web_api.py > logs/web.log 2>&1 &
WEB_PID=$!
echo "✅ Web 已启动 (PID: $WEB_PID)"

echo ""
echo "📝 日志文件："
echo "  Bot: logs/bot.log"
echo "  Web: logs/web.log"
echo ""
echo "🔗 访问地址："
echo "  Web 管理: http://localhost:5000"
SCRIPT
      chmod +x "$INSTALL_DIR/start.sh"
      echo -e "  ${C}bash start.sh${N}"
    fi
    ;;

  supervisor)
    ok "Supervisor 配置已生成"
    echo -e "\n  ${W}后续步骤：${N}"
    echo -e "  ${C}sudo supervisorctl reread${N}"
    echo -e "  ${C}sudo supervisorctl update${N}"
    echo -e "  ${C}sudo supervisorctl start all${N}"
    echo -e "  ${C}sudo supervisorctl status${N}"
    ;;

  systemd)
    ok "Systemd 配置已生成"
    echo -e "\n  ${W}后续步骤：${N}"
    echo -e "  ${C}sudo systemctl daemon-reload${N}"
    echo -e "  ${C}sudo systemctl enable tg-downloader${N}"
    echo -e "  ${C}sudo systemctl start tg-downloader${N}"
    echo -e "  ${C}sudo systemctl status tg-downloader${N}"
    ;;
esac

# ── 最后提示 ──────────────────────────────────────────────
sep
echo -e "\n  ${G}${BOLD}✨ 部署完成！${N}\n"

if [[ "$RUN_WEB" == true ]]; then
  echo -e "  ${W}📝 配置文件：${N}${C}$INSTALL_DIR/.env${N}"
  echo -e "  ${W}🌐 Web 管理：${N}${C}http://localhost:5000${N}"
  echo -e "  ${W}📁 默认密码：${N}${C}admin（在 .env 中修改）${N}"
  echo -e ""
fi

if [[ "$RUN_BOT" == true ]]; then
  echo -e "  ${W}💬 Telegram Bot：${N}${C}发送 /start 查看菜单${N}"
  echo -e ""
fi

echo -e "  ${Y}功能列表：${N}"
if [[ "$RUN_BOT" == true ]]; then
  echo -e "  ✅ Telegram 自动下载"
  echo -e "  ✅ 文件管理"
  echo -e "  ✅ 搜索和过滤"
fi
if [[ "$RUN_WEB" == true ]]; then
  echo -e "  ✅ Web 管理界面"
  echo -e "  ✅ 在线播放视频/音频/图片"
  echo -e "  ✅ 文件搜索和统计"
  echo -e "  ✅ 支持所有下载目录中的文件"
fi

echo -e ""
echo -e "  ${Y}快速开始：${N}"
echo -e "  1️⃣  编辑 .env（填写 Telegram API 信息）"
echo -e "  2️⃣  启动服务"
echo -e "  3️⃣  打开浏览器访问 http://localhost:5000"
echo -e "  4️⃣  在 Telegram 中使用 Bot\n"
