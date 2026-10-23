# Living Stream Agent

直播脚本生成智能体，后端使用 FastAPI，前端使用 React/Vite，数据库使用外部共享 MySQL。

## 阿里云与门户 CAS

阿里云使用 `docker-compose.server.yml` 的 `backend` 和 `frontend` 两个服务，容器为 `living-stream-backend`、`living-stream-frontend`，不发布宿主机端口。数据库复用 `proxy-tier` 上已有的 `my-mysql`，单独建立 `living_stream_agent` 数据库与同名受限账号，数据沿用共享 MySQL 的 `/root/work_project/news/mysql_data` 持久化目录。服务目录为 `/root/work_project/living-stream-agent`。编排中的 `mysql` 服务仅供需要自建数据库的其他环境使用；对应 `living-stream-agent_mysql-data` 卷不能在升级时删除。

公网入口为 `https://www.agent-show.com/living-stream-agent/chat/`。设置 `APP_ENV=production`、`APP_PUBLIC_URL=https://www.agent-show.com/living-stream-agent`、`PORTAL_AUTH_URL=http://portal-auth:8080`、`MYSQL_HOST=my-mysql`、`MYSQL_PORT=3306`，并在服务器生成独立数据库和 JWT/管理员密码，配置云端模型；不上传本机开发 `.env`。生产关闭 `LOCAL_DEV_LOGIN`，也不开放原平台 Token 登录。

认证复用现有门户的 CAS 会话，不复制门户签名密钥。浏览器未登录时经 `/api/auth/login` 使用门户原有 CAS 回调，登录后返回直播话术；无需新增 CAS 回调白名单。每次业务请求由后端向门户验证 Cookie，资源归属取验证后的稳定 uid；旧账号请求头、跨账号会话/导出和管理员身份不匹配均拒绝。写请求要求同源 Origin 和 `X-Living-Stream-Request: 1`。认证故障返回 503，前端保留草稿并重试；退出和账号切换会重新校验身份并清理旧账号状态。

发布前运行 `PYTHONPATH=backend .venv/bin/python -m unittest discover -s backend/tests -v`、`npm run build -- --base=/living-stream-agent/chat/` 和 `docker compose -f docker-compose.server.yml config --quiet`，提交并推送后再打包源码。阿里云发布命令为 `docker compose -f docker-compose.server.yml up -d --no-deps --build backend frontend`，不启动备用 MySQL 容器。后端健康后如仅重建后端，应执行 `docker compose -f docker-compose.server.yml restart frontend` 刷新 nginx 的上游地址。构建配置可设置 `PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple`。外层 nginx 的精确路由片段见 `deploy/outer-nginx.conf`，加入现有 TLS server 后从门户目录执行 `docker compose restart nginx`；homepage 的 `VITE_LIVE_SCRIPT_URL` 指向上述应用入口。

已有部署更新前刷新 `/root/work_project/codex-backups/codex-living-stream-agent-backup.tar.gz`，保留服务器 `.env` 与数据卷；门户和 nginx 使用对应的单份滚动备份。首次部署没有旧源码可备份。回滚恢复源码并重建容器，不能覆盖 `.env` 或删除数据库卷。健康检查为 `/living-stream-agent/chat/api/health`，未登录业务 API 返回 JSON 401，页面跳转门户登录。

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

### 本机开发（macOS）

本地配置使用独立 MySQL 容器、项目内 Python 虚拟环境和 Vite，不占用其他项目的 5173 端口。

```bash
cd /Users/harvey/PyProjects/living-stream-agent
# 首次安装依赖（本机已完成）
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
npm ci

# 确保 Docker Desktop 已启动，再运行
./start-local
./stop-local  # 停止本项目服务，保留数据库数据卷
```

本机 `.env` 已配置随机数据库密码、JWT 密钥、平台入口 Token 和超级管理员密码，并已被 Git 忽略。新环境先复制 `.env.example`，配置 `MYSQL_HOST=127.0.0.1`、`MYSQL_PORT=3308`、独立的数据库账号与密码、`MYSQL_ROOT_PASSWORD`、`SECRET_KEY`、`PLATFORM_ENTRY_TOKEN` 和 `SUPER_ADMIN_INITIAL_PASSWORD`。

- 本地测试入口：<http://127.0.0.1:5172/__local/login>。需要 `.env` 中 `LOCAL_DEV_LOGIN=true`；仅接受本机请求，由开发服务器调用原有平台认证接口签发用户 JWT。此入口不会进入生产构建。
- 超级管理员：<http://127.0.0.1:5172/chat/#/superlogin>，账号 `admin`，密码见 `.env` 的 `SUPER_ADMIN_INITIAL_PASSWORD`。
- 本机测试用户 `local-harvey` 已绑定普通管理员，可从聊天页进入管理后台。
- 后端健康检查：<http://127.0.0.1:3001/chat/api/health>。
- 日志和进程信息：`.local/backend.log`、`.local/frontend.log`、`.local/*.pid`。
- 数据库：`compose.local.yml` 的 `mysql_data` 数据卷，映射本机 `127.0.0.1:3308`。使用 `docker compose -f compose.local.yml logs mysql` 排查数据库问题。

本机当前接入阿里云 `qwen3.8-flash`，复用 `harness-wiki/backend/.env` 中已有的 `LLM_BASE_URL`、`LLM_MODEL` 和 `LLM_API_KEY`，分别写入本项目 `.env` 的 `OPENAI_BASE_URL`、`OPENAI_MODEL` 和 `OPENAI_API_KEY`。同时设置 `OPENAI_ENABLE_THINKING=false`，对应源项目的 `LLM_REASONING_EFFORT=off`，用于缩短话术任务等待时间。密钥仅保存在本机被 Git 忽略的配置中；复制后两项目独立读取配置，源项目密钥变更时需同步更新本项目。原本地模型配置备份在 `.local/.env.before-cloud`。

若要切回 LM Studio，将这三个字段改为 `http://127.0.0.1:1234/v1`、`deepseek-r1-distill-qwen-7b` 和 `lm-studio`（本地服务占位值），删除 `OPENAI_ENABLE_THINKING` 配置，并在 LM Studio 启动服务、加载模型。模型配置变更后执行 `./stop-local && ./start-local`。

首次启动通过当前 ORM 模型创建新库，初始化模板、打分配置和推荐问题。仓库未提供历史 SQL 迁移，因此本地保留空迁移目录；现有生产数据库升级仍需对应迁移文件。`deploy/database.sql` 是历史数据导出，本地启动不会导入。

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
