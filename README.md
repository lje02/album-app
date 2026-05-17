git 安装
sudo apt update && sudo apt install git

克隆仓库
git clone https://github.com/lje02/photo-album.git

cd photo-album

bash install.sh



photo-album/
├── src/
│   ├── App.jsx        # 主应用（localStorage 替代 window.storage）
│   └── main.jsx
├── index.html
├── vite.config.js
├── package.json
├── install.sh         # 一键安装脚本 ← 核心
├── .gitignore
└── README.md
