# AGENTS.md - 项目开发指南

## 项目概述

**Living Stream Agent** 是一个基于 OpenAI 兼容接口的直播脚本生成智能体系统。

## 技术栈

### 后端
- **语言**: Python 3.11
- **框架**: FastAPI
- **数据库**: MySQL 8.0 + SQLAlchemy
- **认证**: JWT (python-jose)
- **LLM**: OpenAI SDK (兼容接口)

### 前端
- **框架**: React 19
- **构建**: Vite 6
- **路由**: React Router v7
- **样式**: CSS Modules

## 项目结构

```
living-stream-agent/
├── backend/                    # 后端代码
│   ├── app/
│   │   ├── main.py            # FastAPI 入口
│   │   ├── core/              # 核心配置
│   │   │   ├── config.py      # 配置管理
│   │   │   ├── database.py    # 数据库连接
│   │   │   └── security.py    # JWT 认证
│   │   ├── models/            # 数据模型
│   │   ├── schemas/           # Pydantic 模式
│   │   ├── api/               # API 路由
│   │   │   ├── agent.py       # LLM 代理入口
│   │   │   ├── dialogs.py     # 对话管理
│   │   │   ├── auth.py        # 认证
│   │   │   ├── admin.py       # 管理后台
│   │   │   ├── forbidden_words.py  # 违禁词
│   │   │   └── memories.py    # 用户记忆
│   │   └── services/          # 业务服务
│   │       ├── llm_service.py           # OpenAI 调用
│   │       ├── forbidden_word_service.py # 违禁词服务
│   │       └── memory_service.py        # 用户记忆服务
│   ├── requirements.txt
│   └── init_db.py             # 数据库初始化
├── src/                        # 前端代码
│   ├── main.jsx               # React 入口
│   ├── App.jsx                # 主应用
│   ├── api/                   # API 调用
│   ├── components/            # UI 组件
│   └── pages/                 # 页面
├── .env                        # 环境变量
├── docker-compose.yml          # Docker 部署
└── package.json                # 前端依赖
```

## 开发规范

### 代码风格

#### Python
- 使用 4 空格缩进
- 遵循 PEP 8 规范
- 使用类型注解
- 函数和类使用 docstring

#### JavaScript/React
- 使用 2 空格缩进
- 使用 JSX 语法
- 组件使用函数式组件 + Hooks
- 样式使用 CSS Modules

### 命名规范

#### Python
- 文件名: `snake_case.py`
- 类名: `PascalCase`
- 函数名: `snake_case`
- 常量: `UPPER_SNAKE_CASE`

#### JavaScript
- 文件名: `camelCase.js` 或 `PascalCase.jsx`
- 组件名: `PascalCase`
- 函数名: `camelCase`
- CSS 类名: `camelCase` (CSS Modules 自动转换)

### API 设计

- RESTful 风格
- 前缀: `/chat/api/`
- 响应格式: JSON
- 流式响应: SSE (`text/event-stream`)

### 数据库

- ORM: SQLAlchemy
- 迁移: 手动管理（通过 `init_db.py`）
- 命名: 表名 `snake_case`，字段名 `snake_case`

## 常用命令

### 开发环境

```bash
# 安装后端依赖
cd backend && pip install -r requirements.txt

# 安装前端依赖
npm install

# 初始化数据库
cd backend && python init_db.py

# 启动开发服务
npm run dev:all
```

### Docker 部署

```bash
# 构建并启动
docker compose build
docker compose up -d

# 查看日志
docker compose logs -f app

# 停止服务
docker compose down
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | - |
| `OPENAI_BASE_URL` | OpenAI API 地址 | `http://host.docker.internal:8765/v1` |
| `OPENAI_MODEL` | 模型名称 | `Deepseek-V4-Flash` |
| `MYSQL_HOST` | MySQL 主机 | `mysql` |
| `MYSQL_PORT` | MySQL 端口 | `3306` |
| `MYSQL_USER` | MySQL 用户 | `root` |
| `MYSQL_PASSWORD` | MySQL 密码 | - |
| `MYSQL_DATABASE` | 数据库名 | `living_stream_agent` |
| `SECRET_KEY` | JWT 密钥 | 自动生成 |

## 数据库模型

### Admin (管理员)
- `id`: 主键
- `username`: 用户名（唯一）
- `hashed_password`: 密码哈希
- `is_active`: 是否启用

### Dialog (对话)
- `id`: 主键（UUID）
- `user_id`: 用户 ID
- `tool_id`: 工具 ID
- `tool_name`: 工具名称
- `title`: 对话标题
- `request_count`: 请求计数

### DialogMessage (对话消息)
- `id`: 主键
- `dialog_id`: 对话 ID（外键）
- `request_id`: 请求 ID
- `role`: 角色（user/assistant）
- `content`: 消息内容

### UserMemory (用户记忆)
- `id`: 主键
- `user_id`: 用户 ID（索引）
- `content`: 记忆内容
- `created_at` / `updated_at`: 时间戳

### ForbiddenWord (违禁词)
- `id`: 主键
- `word`: 违禁词
- `replacement`: 替换词

### PlatformUser (平台用户)
- `id`: 主键
- `platform_user_id`: 平台用户 ID（唯一）
- `lan_name`: 地市
- `region_name`: 区县
- `staff_code`: 工号
- `staff_name`: 姓名
- `staff_pos_type`: 岗位

## API 接口

### 智能体接口
- `POST /chat/api/agent` - 主端点（支持流式）
- `POST /chat/api/agent/generate` - 生成脚本
- `POST /chat/api/agent/score` - 脚本打分
- `POST /chat/api/agent/revise` - 脚本订正

### 对话管理
- `POST /chat/api/dialogs` - 创建对话
- `GET /chat/api/dialogs` - 获取对话列表
- `GET /chat/api/dialogs/{id}` - 获取对话详情
- `DELETE /chat/api/dialogs/{id}` - 删除对话
- `POST /chat/api/dialogs/message` - 保存消息
- `GET /chat/api/dialogs/{id}/messages` - 获取消息列表

### 统计接口
- `GET /chat/api/dialogs/stats/overview` - 总览统计
- `GET /chat/api/dialogs/stats/users` - 用户统计
- `GET /chat/api/dialogs/stats/users/export` - 导出 CSV
- `GET /chat/api/dialogs/stats/filters` - 筛选选项

### 管理接口
- `POST /chat/api/admin/login` - 管理员登录
- `POST /chat/api/admin/change-password` - 修改密码

### 违禁词接口
- `GET /chat/api/forbidden-words` - 获取所有
- `POST /chat/api/forbidden-words` - 创建
- `PUT /chat/api/forbidden-words/{id}` - 更新
- `DELETE /chat/api/forbidden-words/{id}` - 删除
- `POST /chat/api/forbidden-words/import` - Excel 导入
- `DELETE /chat/api/forbidden-words/batch/all` - 清空

### 记忆接口
- `GET /chat/api/memories?user_id=xxx` - 获取用户记忆
- `POST /chat/api/memories` - 创建记忆
- `PUT /chat/api/memories/{id}` - 更新记忆
- `DELETE /chat/api/memories/{id}` - 删除记忆

### 认证接口
- `POST /chat/api/auth/login` - 用户登录
- `GET /chat/api/auth/me` - 获取当前用户

## 智能体处理流程

### 核心流程
1. **上下文关联**：自动加载对话历史（最近20条消息）
2. **意图识别**：分析用户输入，判断意图
3. **文件解析**：如有上传文件，解析内容（支持 txt/docx/pdf/xlsx）
4. **记忆加载**：自动加载该用户的长期记忆注入 LLM context
5. **流式输出**：每一步都流式返回结果

### 支持的意图
- `generate_script` - 生成直播脚本（三步流程：生成→打分→订正）
- `score_script` - 脚本打分评价
- `revise_script` - 脚本订正优化
- `analyze_script` - 脚本结构分析
- `save_memory` - 保存用户长期记忆（用户明确要求记住/保存信息时触发）
- `general_chat` - 普通对话

### 直播脚本生成流程
1. **第一步：生成直播脚本** - 根据产品信息生成完整脚本
2. **第二步：脚本质量评估** - 从吸引力、逻辑性、感染力、专业性评分
3. **第三步：脚本优化订正** - 根据评估结果优化脚本

## 注意事项

1. **LLM 接口**: 所有大模型调用通过 OpenAI 兼容接口，不使用 scene_gateway
2. **违禁词过滤**: 在流式响应中实时过滤
3. **时区**: 使用上海时区 (UTC+8)
4. **文件上传**: 支持 .txt/.docx/.pdf/.xlsx，最大 10MB
5. **默认管理员**: admin / admin123
