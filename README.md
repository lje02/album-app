# 1️⃣ 克隆项目
git clone https://github.com/lje02/tgdown-web.git
cd tgdown

需要telegram:
id
api


# 2️⃣ 运行一键部署脚本
bash install-enhanced.sh

# 3️⃣ 脚本会引导你：
#    ✅ 检测环境（OS、Python、Docker）
#    ✅ 选择部署方式（Docker/Supervisor/Systemd/本地）
#    ✅ 生成 .env 配置文件
#    ✅ 安装依赖
#    ✅ 启动 Bot

部署方式选择

1️⃣ Docker Compose      → 最简单，推荐新手
2️⃣ Supervisor          → 生产级，推荐服务器
3️⃣ Systemd             → Linux 系统，推荐开机自启
4️⃣ 本地运行            → 开发测试，推荐调试

git安装

sudo apt install git-all

git更新

git clone git://git.kernel.org/pub/scm/git/git.git
## 一键安装

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/lje02/tgdown-web/main/install-enhanced.sh)
