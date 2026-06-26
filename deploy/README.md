# 部署说明

## 文件清单

```
deploy/
├── images.tar.gz          # App 镜像
├── database.sql           # 数据库初始化脚本（需手动执行）
├── docker-compose.yml     # 只包含 App 服务
├── .env.example           # 环境变量模板
├── deploy.sh              # 部署脚本
└── README.md              # 本文档
```

## 前置条件

- 服务器已安装 Docker 和 Docker Compose
- 服务器上已有 MySQL 8.0 数据库

## 部署步骤

### 1. 初始化数据库

在 MySQL 中执行 `database.sql` 创建数据库和表：

```bash
# 方式一：命令行执行
mysql -u root -p < database.sql

# 方式二：登录 MySQL 后执行
mysql -u root -p
source /path/to/database.sql
```

### 2. 上传文件到服务器

```bash
scp -r deploy/ user@server:/opt/living-stream-agent/
```

### 3. 登录服务器

```bash
ssh user@server
cd /opt/living-stream-agent
```

### 4. 加载镜像

```bash
docker load -i images.tar.gz
```

### 5. 配置环境变量

```bash
cp .env.example .env
vi .env
```

修改以下配置：
```env
# OpenAI 配置
OPENAI_API_KEY=sk-xxxxx
OPENAI_BASE_URL=https://api.openai.com/v1  # 或其他兼容接口
OPENAI_MODEL=gpt-4o-mini  # 或其他模型

# MySQL 配置（外部数据库）
MYSQL_HOST=192.168.1.100  # MySQL 服务器 IP
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=living_stream_agent
```

### 6. 启动服务

```bash
docker compose up -d
```

### 7. 检查状态

```bash
docker compose ps
docker compose logs -f
```

## 访问地址

- **主页面**: http://服务器IP:5172/chat/
- **管理后台**: http://服务器IP:5172/chat/login

## 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin123 | admin123 |
| 超级管理员 | admin | admin |

## 常用命令

```bash
# 查看日志
docker compose logs -f

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 进入容器
docker compose exec app bash
```

## 配置 Nginx 反向代理（可选）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5172;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 数据备份

```bash
# 备份数据库
mysqldump -u root -p living_stream_agent > backup_$(date +%Y%m%d).sql

# 恢复数据库
mysql -u root -p living_stream_agent < backup.sql
```

## 常见问题

### 1. 无法连接数据库

检查 `.env` 中的 MySQL 配置，确保：
- `MYSQL_HOST` 可以从 Docker 容器访问
- MySQL 用户有远程访问权限
- 防火墙允许 3306 端口

### 2. Docker 容器内无法访问宿主机 MySQL

使用 `host.docker.internal` 或宿主机 IP：
```env
MYSQL_HOST=host.docker.internal
```

或使用宿主机实际 IP：
```env
MYSQL_HOST=192.168.1.100
```

### 3. OpenAI API 调用失败

检查 API 配置，确保：
- API Key 正确
- API 地址可访问
- 模型名称正确
