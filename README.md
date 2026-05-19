git 安装
sudo apt update && sudo apt install git

# 运行这一行
curl -L -o deploy.sh https://raw.githubusercontent.com/lje02/album-app/refs/heads/main/deploy.sh



# 1. 赋予执行权限
chmod +x deploy.sh

# 2. 运行脚本开始部署
./deploy.sh




curl -o- https://raw.githubusercontent.com/lje02/album-app/main/install.sh | sudo bash
