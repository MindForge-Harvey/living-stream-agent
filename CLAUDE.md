# CLAUDE.md

## 项目简介

直播脚本生成智能体系统，使用 FastAPI + React + MySQL + OpenAI 兼容接口。

## 启动方式（Docker）

```bash
# 完整启动（首次或代码变更后）
cd /Users/chengzhang/PycharmProjects/living-stream-agent
docker compose down && docker compose build app && docker compose up -d

# 查看日志
docker compose logs -f app

# 停止服务
docker compose down

# 仅重启（无代码变更）
docker compose restart
```

## 访问地址

- 前端: http://localhost:5173/chat/
- 测试登录: http://localhost:5173/chat/test/login
- 管理后台: http://localhost:5173/chat/login
- 后端 API: http://localhost:5173/chat/api/

## 默认账号

- 管理员: admin / admin123

## 端口说明

| 服务 | 容器端口 | 宿主机端口 |
|------|----------|------------|
| MySQL | 3306 | 3308 |
| App | 3001 | - |
| Nginx | 80 | 5173 |

## 关键配置 (.env)

```
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=http://host.docker.internal:8765/v1
OPENAI_MODEL=Deepseek-V4-Flash
MYSQL_PASSWORD=your-mysql-password
```

## 代码规范

- Python: PEP8, 4空格缩进, snake_case
- JavaScript: 2空格缩进, PascalCase 组件名
- CSS: CSS Modules, camelCase 类名
- API: RESTful, 前缀 `/chat/api/`

## 核心文件

| 文件 | 说明 |
|------|------|
| `backend/app/main.py` | FastAPI 入口 |
| `backend/app/services/llm_service.py` | LLM 调用服务 |
| `backend/app/api/agent.py` | 智能体 API |
| `backend/app/api/dialogs.py` | 对话管理 |
| `src/App.jsx` | 前端主应用 |
| `src/api/index.js` | API 调用 |

## 数据库

- MySQL 8.0, 使用 SQLAlchemy ORM
- 表名: admins, dialogs, dialog_messages, forbidden_words, platform_users

## 智能体能力

| 能力 | 说明 |
|------|------|
| generate_script | 生成直播脚本（三步：生成→打分→订正） |
| score_script | 脚本打分评价 |
| revise_script | 脚本订正优化 |
| analyze_script | 脚本结构分析 |
| general_chat | 普通对话 |

## 注意事项

1. 不使用 scene_gateway，所有 LLM 调用走 OpenAI 兼容接口
2. 违禁词在流式响应中实时过滤
3. 时区使用 Asia/Shanghai (UTC+8)
4. 修改代码后需要重新构建: `docker compose down && docker compose build app && docker compose up -d`
