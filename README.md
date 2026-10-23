# Living Stream Agent

直播脚本生成智能体，后端使用 FastAPI，前端使用 React/Vite，数据库使用外部共享 MySQL。

## 技术栈

- **后端**: Python 3.11 + FastAPI + SQLAlchemy，JWT 认证
- **前端**: React 19 + Vite + React Router v7 + CSS Modules
- **LLM**: OpenAI 兼容接口
- **数据库**: MySQL 8.0（外部共享库）

## 项目结构

```
living-stream-agent/
├── backend/                  # 后端代码
├── src/                      # 前端代码（Vite -> dist）
├── deploy/                   # 数据库迁移 SQL（Dockerfile 构建时复制）
│   └── migrations/           # 表结构迁移脚本
├── .env                      # 唯一配置源（gitignore）
├── .env.example              # 配置模板
├── docker-compose.yml        # 唯一编排文件
├── Dockerfile                # 后端镜像
├── Dockerfile.frontend       # 前端镜像（nginx）
├── nginx.conf                # 前端反代配置
└── start                     # 容器启动脚本
```

## 数据库

应用连接**外部共享 MySQL**，连接参数在 `.env` 中配置：

| 变量 | 示例 |
|------|------|
| `MYSQL_HOST` | `host.docker.internal`（容器内访问宿主机共享库） |
| `MYSQL_PORT` | `3307` |
| `MYSQL_USER` | `living_stream_agent` |
| `MYSQL_PASSWORD` | 共享库密码 |
| `MYSQL_DATABASE` | `living_stream_agent` |

> 容器内无法通过 `127.0.0.1` 访问宿主机，需使用 `host.docker.internal`。

表结构升级在容器启动时自动执行（`backend/app/core/migrations.py` + `deploy/migrations/*.sql`）。

## 部署启动

### 开发/本地（重新构建并启动）

```bash
./start              # 重建镜像并启动
./start --no-build   # 跳过前端构建
./start --clean      # 停止旧容器再启动
```

### 直接使用 docker compose

```bash
# 首次或代码变更后构建
docker compose up -d --build

# 仅启动已有镜像
docker compose up -d

# 移除旧孤儿容器
docker compose up -d --remove-orphans
```

## 配置

配置集中在项目根目录 `.env`（已 gitignore，不提交）。首次部署复制模板：

```bash
cp .env.example .env
vi .env
```

至少需要配置：

```env
OPENAI_API_KEY=你的模型密钥
OPENAI_BASE_URL=你的模型接口地址
OPENAI_MODEL=你的模型名称
MYSQL_HOST=共享库地址
MYSQL_PORT=共享库端口
MYSQL_USER=共享库用户
MYSQL_PASSWORD=共享库密码
MYSQL_DATABASE=living_stream_agent
PLATFORM_ENTRY_TOKEN=平台入口 Token
SUPER_ADMIN_INITIAL_PASSWORD=首次创建超级管理员密码
```

## 数据库表结构

表结构升级会在容器启动时自动执行。新增表结构变更时，把 SQL 放到：

```text
deploy/migrations/00X_xxx.sql
```

然后重新构建并启动即可。

## 访问地址

- 主页面：`http://localhost:5172/chat/`
- 超级管理员：`http://localhost:5172/chat/#/superlogin`

## 常用命令

```bash
docker compose ps
docker compose logs -f backend
docker compose restart
docker compose down
```
