```angular2html
ssh -i menghan_visualization.pem ubuntu@3.1.83.180

```


```angular2html
sudo apt update && sudo apt upgrade -y

# 安装 Docker
sudo apt install -y docker.io

# 安装 Docker Compose v2（使用 plugin 方式）
sudo apt install -y docker-compose-plugin

# 启动 Docker 服务
sudo systemctl enable docker
sudo systemctl start docker

# 测试版本
docker --version
docker compose version

```

```angular2html
ssh-keygen -t rsa -b 4096 -C "jeffrey-qin@outlook.com"
cat ~/.ssh/id_rsa.pub

ssh -T git@github.com
```


```angular2html
# 创建 docker 用户组（如尚未存在）
sudo groupadd docker

# 将当前用户添加到 docker 组
sudo usermod -aG docker $USER

# 让变更立即生效
newgrp docker

```
```angular2html
sudo apt install -y git

# 拉取你的仓库（替换为你自己的 repo）
git clone https://github.com/your-username/your-repo.git

cd your-repo

```


```angular2html
sudo docker compose up --build -d
```

```angular2html
sudo docker ps
sudo docker compose down
sudo docker compose build
sudo docker compose build --no cache
```


```angular2html
sudo docker logs visualizationbackendproject-visualization-1
```