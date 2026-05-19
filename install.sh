#!/bin/bash
set -e

# ----- 配置（可修改） -----
GITHUB_REPO="https://github.com/你的用户名/album-app.git"   # 👈 改成你的仓库地址
INSTALL_DIR="/opt/album-app"
NODE_VERSION="18"
SERVICE_NAME="album-app"

# ----- 颜色输出 -----
RED='\033[0;31m'; GREEN='\033[0;32m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ----- 检查 root -----
if [ "$EUID" -ne 0 ]; then error "请使用 root 权限运行：sudo bash install.sh"; fi

# ----- 安装 Node.js（如需要） -----
if ! command -v node &>/dev/null; then
  info "正在安装 Node.js ${NODE_VERSION}..."
  curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash -
  apt-get install -y nodejs
fi

# ----- 克隆/更新项目 -----
if [ -d "$INSTALL_DIR" ]; then
  info "项目目录已存在，执行更新..."
  cd "$INSTALL_DIR"
  git pull
else
  info "克隆项目到 ${INSTALL_DIR} ..."
  git clone "$GITHUB_REPO" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

# ----- 安装依赖 -----
info "安装 npm 依赖..."
npm install --production
mkdir -p uploads

# ----- 创建 systemd 服务 -----
cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Album App
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=/usr/bin/node ${INSTALL_DIR}/server.js
Restart=on-failure
RestartSec=10
Environment=PORT=3000

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}

# ----- 完成提示 -----
IP=$(hostname -I | awk '{print $1}')
info "✅ 安装完成！"
info "访问地址：http://${IP}:3000"
info "默认管理员密码：admin123"
info "查看日志：journalctl -u ${SERVICE_NAME} -f"
