#!/usr/bin/env bash

# ====================================================================
# 配置区域（根据实际情况修改）
# ====================================================================
REPO_URL="https://github.com/lje02/album-app"  # 替换为你的 GitHub 仓库地址
APP_DIR="/opt/public-album"
PORT="8000"
DOMAIN="64.69.40.150"  # 替换为你的域名，若无域名可填公网 IP

# 字体颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_err() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# 权限检查
[[ $EUID -ne 0 ]] && log_err "请使用 root 用户或通过 sudo 运行此脚本！"

# --- 1. 安装系统依赖 ---
log_info "正在更新系统并安装必要组件..."
if command -v apt-get &> /dev/null; then
    apt-get update -y && apt-get install -y git python3 python3-pip python3-venv nginx curl
elif command -v dnf &> /dev/null; then
    dnf install -y git python3 python3-pip nginx curl
else
    log_err "未识别的包管理器，请手动安装 git, python3, nginx"
fi

# --- 2. 拉取/更新代码 ---
if [ -d "$APP_DIR/.git" ]; then
    log_info "目标目录已存在，正在拉取最新代码..."
    cd "$APP_DIR" && git pull || log_err "代码更新失败"
else
    log_info "正在克隆 GitHub 仓库..."
    rm -rf "$APP_DIR"
    git clone "$REPO_URL" "$APP_DIR" || log_err "仓库克隆失败，请检查 URL 是否正确或仓库是否公开"
    cd "$APP_DIR" || exit 1
fi

# 检查文件完整性
[[ ! -f "app.py" || ! -f "index.html" ]] && log_err "仓库中未找到 app.py 或 index.html，请检查仓库结构"

# --- 3. 配置 Python 虚拟环境 ---
log_info "正在配置 Python 虚拟环境及依赖..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn python-multipart httpx || log_err "Python 依赖安装失败"
deactivate

# --- 4. 配置 Systemd 守护进程 ---
log_info "正在配置 Systemd 守护服务..."
cat <<EOF > /etc/systemd/system/public-album.service
[Unit]
Description=Public Album Backend Service
After=network.target

[Service]
User=root
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/uvicorn app:app --host 127.0.0.1 --port $PORT
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable public-album.service
systemctl restart public-album.service || log_err "后端服务启动失败"

# --- 5. 配置 Nginx 反向代理 ---
log_info "正在配置 Nginx..."
NGINX_CONF="/etc/nginx/sites-available/public-album"
[[ ! -d "/etc/nginx/sites-available" ]] && NGINX_CONF="/etc/nginx/conf.d/public-album.conf"

cat <<EOF > "$NGINX_CONF"
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# 如果是 Ubuntu/Debian，创建软链接
if [ -d "/etc/nginx/sites-enabled" ] && [ ! -f "/etc/nginx/sites-enabled/public-album" ]; then
    ln -s "/etc/nginx/sites-available/public-album" "/etc/nginx/sites-enabled/"
    # 移除默认配置防冲突
    rm -f /etc/nginx/sites-enabled/default
fi

nginx -t &> /dev/null || log_err "Nginx 配置语法错误，请检查"
systemctl enable nginx
systemctl restart nginx

# --- 6. 部署完成 ---
echo -e "\n=================================================="
log_info "相册程序部署成功！"
echo -e "访问地址: http://$DOMAIN"
echo -e "管理入口: http://$DOMAIN/#/admin  (默认密码: admin123)"
echo -e "程序目录: $APP_DIR"
echo -e "=================================================="
