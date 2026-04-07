# 部署指南

## 镜像构建

```bash
# 构建 x86 架构镜像
docker buildx build --platform linux/amd64 --no-cache -t mugame-mubo:20260407_0140-x86 -f Dockerfile .

# 导出 tar 文件
docker save mugame-mubo:20260407_0140-x86 -o mugame-mubo-20260407_0140-x86.tar
```

## 服务器部署

### 1. 停止旧容器

```bash
docker stop mugame
docker rm mugame
```

### 2. 加载新镜像

```bash
docker load < mugame-mubo-20260407_0140-x86.tar
```

### 3. 启动容器

```bash
docker run -d --name mugame -p 5212:5212 mugame-mubo:20260407_0140-x86
```

### 4. 验证运行

```bash
docker ps
curl http://localhost:5212/game/bo/api/get-maps
```

## OpenResty / Nginx 配置

在反向代理配置中添加静态文件路径：

```nginx
location /static/ {
    proxy_pass http://127.0.0.1:5212;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}

location /game/bo {
    proxy_pass http://127.0.0.1:5212;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header REMOTE-HOST $remote_addr;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $http_connection;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Port $server_port;
    proxy_http_version 1.1;
    add_header X-Cache $upstream_cache_status;
    proxy_ssl_server_name off;
    proxy_ssl_name $proxy_host;
}
```

重载配置：

```bash
# OpenResty
openresty -t
openresty -s reload

# Nginx
nginx -t
nginx -s reload
```

## 数据库说明

地图数据已打包在镜像 `/app/instance/game_data.db`，无需额外配置。

如需更新地图，执行 SQL：

```sql
INSERT INTO map (name, display_name, width, height, data) VALUES ('map_name', '显示名称', 8, 8, '{"grid":[]}');
```

然后重新构建镜像。

## 常见问题

### 502 Gateway
检查容器是否正常运行：
```bash
docker logs mugame
docker ps
```

### 只有一个地图
确认部署的是最新镜像版本，检查 API 返回：
```bash
curl http://localhost:5212/game/bo/api/get-maps
```

### 静态文件 404
确认 OpenResty/Nginx 配置了 `/static/` 路径代理。
