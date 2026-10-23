# Code Review 与前端功能测试报告

生成时间：2026-07-07 00:20（Asia/Shanghai）

## 结论

- 本次 review 未发现会阻断当前测试登录、主聊天、对话、记忆、模板、版本、导出等核心功能的明显代码错误。
- `npm run build`、测试前端 `npm run build` 均通过。
- `http://localhost:5174/test/login` 已验证可通过 `postMessage` 登录并进入 `http://localhost:5172/chat/`。
- 后端接口鉴权、平台固定 token 校验、未授权拦截、主要功能接口冒烟均通过。
- 发现 1 个建议优化项：`/chat/` 读取本地缓存 token 时未主动调用 `/chat/api/auth/me` 复验，过期 token 会等到后续接口请求时才暴露。

## Review 范围

- 正式前端入口：`src/main.jsx`
- 主聊天页面：`src/App.jsx`
- 前端 API 封装：`src/api/index.js`
- 测试前端入口：`living-stream-agent-test/src/main.jsx`
- 登录认证接口：`backend/app/api/auth.py`
- 权限与 token：`backend/app/core/security.py`
- 限流逻辑：`backend/app/core/rate_limit.py`
- 静态路由与 CORS：`backend/app/main.py`
- 模板、记忆、对话、导出相关接口与页面交互

## 代码审查结果

### 通过项

- `living-stream-agent-test/src/main.jsx:23` 正确发送 `PLATFORM_LOGIN`，且包含固定 `platformToken`。
- `living-stream-agent-test/src/main.jsx:36` 使用隐藏 iframe 打开正式 `/chat/` 接收 `postMessage`，登录成功后当前窗口跳转到正式页面。
- `src/main.jsx:58` 正式 `/chat/` 监听 `PLATFORM_LOGIN`，并在收到消息后调用后端换取正式 JWT。
- `backend/app/api/auth.py:102` 使用 `secrets.compare_digest` 校验固定 `PLATFORM_ENTRY_TOKEN`，未把 token 暴露在 URL。
- `src/main.jsx:60` 至 `src/main.jsx:87` 已实现 ACK/SUCCESS/FAILED 回传，测试前端不会再无限刷请求。
- `src/api/index.js:260` 导出接口前端字段为 `dialog_id`，与后端 `ExportRequest` 一致。

### 建议优化项

- `src/main.jsx:98` 读取 `localStorage.userInfo` 后只检查 `platformToken` 是否存在，没有主动调用 `/chat/api/auth/me` 验证 token 是否过期或无效。
- 影响：过期 token 下用户可能先看到聊天界面，随后列表/发送等接口返回 401/403，体验上不够“入口即校验”。
- 建议：进入 `/chat/` 时若存在本地 token，先调用 `/chat/api/auth/me`；成功再进入 App，失败则清除缓存并显示“请先从平台登录”。

## 构建测试

| 测试项 | 命令 | 结果 |
|---|---|---|
| 正式前端构建 | `npm run build` | 通过 |
| 测试前端构建 | `cd living-stream-agent-test && npm run build` | 通过 |
| Docker 服务状态 | `docker compose ps` | app/mysql/nginx 运行中 |

## 接口测试

| 测试项 | 结果 | 说明 |
|---|---|---|
| 健康检查 | 通过 | `GET /chat/api/health` 返回 200 |
| 未授权访问 | 通过 | `GET /chat/api/conversations` 无 token 返回 403 |
| 错误平台 token | 通过 | `POST /chat/api/auth/test-token` 返回 401 |
| 固定平台 token | 通过 | 返回 200 且签发 JWT |
| 创建对话 | 通过 | `POST /chat/api/conversations` 返回对话 ID |
| 对话列表 | 通过 | `GET /chat/api/conversations?pageSize=5` 返回列表 |
| 保存消息 | 通过 | `POST /chat/api/conversations/message` 返回 200 |
| 查询消息 | 通过 | `GET /chat/api/conversations/{id}/messages` 返回消息 |
| 记忆增删改查 | 通过 | create/list/update/delete 均返回 200 |
| 模板列表 | 通过 | public/mine 均返回 200 |
| 用户模板增删改 | 通过 | create/update/delete 均返回 200 |
| 版本历史 | 通过 | `GET /chat/api/assistant/versions/{id}` 返回 200 |
| TXT 导出 | 通过 | `POST /chat/api/export` 返回 200 |

## 浏览器功能测试

| 页面/功能 | 结果 | 说明 |
|---|---|---|
| 测试登录页打开 | 通过 | `http://localhost:5174/test/login` 正常显示用户 ID、姓名、登录按钮 |
| 测试登录跳转 | 通过 | 输入用户 ID 后进入 `http://localhost:5172/chat/` |
| `postMessage` 登录 | 通过 | 后端日志显示 `platform_token` 成功，未出现重复刷 429 |
| 主聊天页加载 | 通过 | 显示用户信息、连接状态、模板/记忆/清空等按钮 |
| 新建对话 | 通过 | 新建后显示欢迎消息和当前对话 |
| 发送消息 | 通过 | 消息成功发送，流式响应完成，无前端控制台错误 |
| 记忆抽屉打开 | 通过 | 抽屉打开并加载当前用户记忆 |
| 新增记忆 | 通过 | 显示“记忆已添加”toast |
| 删除记忆确认框 | 通过 | 点击删除后出现浏览器原生 confirm |

## 测试限制

- 浏览器自动化在接受记忆删除的原生 `confirm` 弹窗时，控制插件出现超时；该问题发生在浏览器控制层，不是应用接口错误。
- 已通过接口层补测记忆删除，`DELETE /chat/api/memories/{id}` 返回 200。
- 管理后台完整 CRUD 未做破坏性深测，只确认普通用户未显示后台入口；管理员权限相关建议后续使用专门测试账号覆盖。

## 容器日志检查

- `docker compose logs --tail=200 app` 未发现 Python 异常堆栈。
- 测试期间预期内 401/403/422：
  - 401：错误平台 token 测试。
  - 403：未授权接口访问测试。
  - 422：第一次接口冒烟时使用了错误测试字段，随后按前端实际字段重测通过。

## 建议后续动作

1. 增加本地缓存 token 的入口复验逻辑，避免过期 token 先进入页面。
2. 为测试前端和正式前端的 `postMessage` 登录链路增加 Playwright/E2E 测试。
3. 为管理员后台准备独立测试账号，覆盖违禁词、模板、统计导出等管理功能。
