# Living Stream Agent - 直播脚本生成智能体

基于 OpenAI 兼容接口的直播脚本生成智能体系统。

## 功能特性

- 🎙️ 直播脚本生成（三步流程：生成 → 评估 → 优化）
- ⭐ 脚本质量评估
- ✨ 脚本订正优化
- 💬 普通对话
- 📁 文件上传解析（支持 .txt/.docx/.pdf/.xlsx）
- 🚫 违禁词过滤
- 📊 用户使用统计
- 👥 管理后台

## 技术栈

### 后端
- Python 3.11
- FastAPI
- SQLAlchemy + MySQL
- OpenAI SDK

### 前端
- React 19
- Vite 6
- React Router v7

## Docker 部署（推荐）

### 1. 配置环境变量

编辑 `.env` 文件，修改以下配置：

```env
# OpenAI 配置
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=http://host.docker.internal:8765/v1
OPENAI_MODEL=any

# MySQL 配置（默认即可）
MYSQL_PASSWORD=living_stream_2024
MYSQL_DATABASE=living_stream_agent
```

### 2. 构建并启动

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f app
```

### 3. 访问服务

- **前端**: http://localhost:5172/chat/
- **后端 API**: http://localhost:5172/chat/api/
- **管理后台**: http://localhost:5172/chat/login

### 4. 常用命令

```bash
# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看状态
docker-compose ps

# 进入容器
docker exec -it living-stream-app bash
```

## 本地开发

### 1. 安装依赖

```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
npm install
```

### 2. 初始化数据库

```bash
cd backend
python init_db.py
```

### 3. 启动服务

```bash
npm run dev:all
```

## 默认账号

- **管理员**: admin / admin123

## 项目结构

```
living-stream-agent/
├── .env                    # 配置文件
├── docker-compose.yml      # Docker 部署配置
├── Dockerfile              # Docker 构建文件
├── nginx.conf              # Nginx 配置
├── backend/                # 后端代码
│   ├── app/
│   │   ├── main.py         # FastAPI 入口
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── api/            # API 路由
│   │   └── services/       # 业务服务
│   └── requirements.txt
└── src/                    # 前端代码
    ├── main.jsx
    ├── App.jsx
    ├── api/
    ├── components/
    └── pages/
```

## API 接口

### 智能体接口
- `POST /chat/api/agent` - 直播话术生成智能体主端点
- `POST /chat/api/agent/generate` - 生成直播脚本
- `POST /chat/api/agent/score` - 脚本打分
- `POST /chat/api/agent/revise` - 脚本订正

### 对话管理
- `POST /chat/api/dialogs` - 创建对话
- `GET /chat/api/dialogs` - 获取对话列表
- `POST /chat/api/dialogs/message` - 保存消息

### 管理接口
- `POST /chat/api/admin/login` - 管理员登录
- `GET /chat/api/dialogs/stats/*` - 统计接口
- `GET/POST/PUT/DELETE /chat/api/forbidden-words` - 违禁词管理
