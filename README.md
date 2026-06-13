# 📦 Telegram 下载机器人 - 一键部署

只需三行命令，全程交互式引导，无需手动编辑任何文件。

---

## ⚙️ 系统要求

- Docker 20.10+（含 `docker compose` 插件）
- Git
- Linux / macOS / WSL2

没装 Docker？一键安装：
```bash
curl -fsSL https://get.docker.com | sh
```

git安装:

sudo apt install git-all

git更新:

git clone git://git.kernel.org/pub/scm/git/git.git

python3安装:

apt update && apt install python3.11-venv -y

---

## 🚀 安装（三步完成）

```bash
# 1. 克隆仓库
git clone https://github.com/lje02/tg_download.git
cd tg_download

https://github.com/你的用户名/你的仓库名.git
cd 你的仓库名

# 2. 给脚本加执行权限
chmod +x setup.sh

# 3. 运行安装向导
bash setup.sh
```

脚本会依次询问：

| 提示 | 说明 | 必填 |
|---|---|---|
| API_ID | 从 https://my.telegram.org 获取 | ✅ |
| API_HASH | 同上 | ✅ |
| BOT_TOKEN | 与 @BotFather 对话获取 | ✅ |
| ALLOWED_USERS | 你的 Telegram 用户 ID（多个用逗号分隔） | ✅ |
| 下载保存路径 | 容器内路径，默认 `/app/downloads` | 可选 |
| 最大同时下载数 | 默认 3 | 可选 |
| 按日期归档 | true / false，默认 true | 可选 |
| 每页条数 | 文件列表分页，默认 8 | 可选 |

填完后自动构建镜像并启动，全程无需手动操作。

> 💡 **不知道自己的用户 ID？**  
> 在 Telegram 搜索 `@userinfobot`，发送任意消息，它会回复你的 ID。

---

## 🛑 卸载

```bash
bash setup.sh --uninstall
```

卸载流程会询问：
1. 是否确认卸载（停止并删除容器 + 镜像）
2. 是否同时删除下载文件和数据库（可单独保留）
3. 是否删除 `.env` 配置文件（可保留，下次安装直接复用）

---

## 🔧 安装后常用命令

```bash
查看日志:

docker compose -f /root/tg_download/docker-compose.yml logs -f

停止:

docker compose -f /root/tg_download/docker-compose.yml stop

重启:

docker compose -f /root/tg_download/docker-compose.yml restart

卸载:

bash setup.sh --uninstall

# 修改参数（如换 Bot Token）
# 1. 直接编辑 .env 文件
# 2. 重启生效：docker compose restart tg_download
```

---

## 📁 仓库文件说明

```
./
├── bot.py              ← 机器人主程序
├── setup.sh            ← 一键安装/卸载脚本
├── requirements.txt    ← Python 依赖（setup.sh 会自动生成，也可提前放好）
├── .gitignore          ← 已屏蔽 .env / session / downloads 等敏感目录
└── README.md           ← 本文件
```

以下文件由 `setup.sh` **自动生成**，无需手动创建：

```
.env  /  Dockerfile  /  docker-compose.yml  /  downloads/  /  session/
```

---

## ❓ 常见问题

**Q: 克隆后提示 `bot.py not found`？**  
A: 确认仓库里包含 `bot.py`，且你在正确目录下运行脚本。

**Q: 构建时卡在下载 Python 镜像？**  
A: 网络问题，可配置 Docker 镜像加速器后重试：
```bash
# 编辑 /etc/docker/daemon.json，添加：
{ "registry-mirrors": ["https://docker.mirrors.ustc.edu.cn"] }
sudo systemctl restart docker
```

**Q: 机器人没有回应？**  
A: 用 `docker compose logs -f tg_download` 查看报错，常见原因是 Token 填错或用户 ID 不在白名单。
