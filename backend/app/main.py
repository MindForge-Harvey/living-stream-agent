import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.migrations import run_migrations
from app.api import auth, agent, admin, dialogs, forbidden_words, memories, super_admin, templates, export, scoring_configs, suggested_questions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info(f"应用启动: {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"OpenAI 配置: base_url={settings.OPENAI_BASE_URL}, model={settings.OPENAI_MODEL}")
    if os.getenv("SKIP_STARTUP_MIGRATIONS") == "1":
        logger.info("启动迁移已由容器入口执行，跳过 FastAPI lifespan 迁移")
    else:
        run_migrations()
    yield
    logger.info("应用关闭")


# 创建应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

@app.middleware("http")
async def chat_cors_middleware(request: Request, call_next):
    """仅对 /chat 路径启用 CORS 白名单限制。"""
    if not request.url.path.startswith("/chat"):
        return await call_next(request)

    origin = request.headers.get("origin")
    is_preflight = (
        request.method == "OPTIONS"
        and "access-control-request-method" in request.headers
    )

    if is_preflight:
        response = Response(status_code=204 if origin in settings.CORS_ORIGINS else 400)
    else:
        response = await call_next(request)

    if origin in settings.CORS_ORIGINS:
        requested_headers = request.headers.get("access-control-request-headers")
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"
        response.headers["Access-Control-Allow-Headers"] = requested_headers or "Authorization, Content-Type"
        response.headers["Vary"] = "Origin"

    return response

# 注册路由
app.include_router(auth.router, prefix="/chat/api")
app.include_router(admin.router, prefix="/chat/api")
app.include_router(dialogs.router, prefix="/chat/api")
app.include_router(dialogs.admin_router, prefix="/chat/api")
app.include_router(agent.router, prefix="/chat/api")
app.include_router(forbidden_words.router, prefix="/chat")
app.include_router(memories.router, prefix="/chat/api")
app.include_router(super_admin.router, prefix="/api")
app.include_router(templates.router, prefix="/chat/api")
app.include_router(export.router, prefix="/chat/api")
app.include_router(scoring_configs.router, prefix="/chat/api")
app.include_router(suggested_questions.router, prefix="/chat/api")


@app.get("/chat/api/health")
async def health():
    """健康检查"""
    from app.services.llm_service import llm_service
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "llm": {
            "available": llm_service.is_available(),
        },
    }


# 静态文件服务（生产环境）
_STATIC_EXTENSIONS = {
    ".js", ".mjs", ".css", ".map", ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".otf", ".pdf",
}

dist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "dist")
if os.path.exists(dist_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")
    app.mount("/chat/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets_chat")

    @app.get("/chat/login")
    async def removed_admin_login():
        """普通管理员登录页已删除。"""
        raise HTTPException(status_code=404, detail="Not Found")

    @app.get("/chat/{full_path:path}")
    async def serve_chat_spa(full_path: str):
        """SPA 路由回退。"""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        file_path = os.path.join(dist_path, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        # 带静态资源扩展名的请求在文件不存在时应返回真正的 404，
        # 否则浏览器对 <script type="module"> 收到 text/html 会触发 MIME 报错。
        if os.path.splitext(full_path)[1].lower() in _STATIC_EXTENSIONS:
            raise HTTPException(status_code=404, detail="Not Found")
        # 普通前端路由回退到 index.html，且禁用缓存，避免旧 index.html 引用过期资源。
        return FileResponse(
            os.path.join(dist_path, "index.html"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

    @app.get("/superlogin")
    async def serve_superlogin():
        """超级管理员登录页面。"""
        return FileResponse(
            os.path.join(dist_path, "index.html"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

    @app.get("/superconfig")
    async def serve_superconfig():
        """超级管理员配置页面。"""
        return FileResponse(
            os.path.join(dist_path, "index.html"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

    @app.get("/")
    async def serve_root():
        """根路径。"""
        return FileResponse(
            os.path.join(dist_path, "index.html"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
