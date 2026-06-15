import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, agent, admin, dialogs, forbidden_words

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info(f"应用启动: {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"OpenAI 配置: base_url={settings.OPENAI_BASE_URL}, model={settings.OPENAI_MODEL}")
    yield
    logger.info("应用关闭")


# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/chat/api")
app.include_router(admin.router, prefix="/chat/api")
app.include_router(dialogs.router, prefix="/chat/api")
app.include_router(agent.router, prefix="/chat/api")
app.include_router(forbidden_words.router, prefix="/chat")


@app.get("/chat/api/health")
async def health():
    """健康检查"""
    from app.services.llm_service import llm_service
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "llm": {
            "available": llm_service.is_available(),
            "base_url": settings.OPENAI_BASE_URL,
            "model": settings.OPENAI_MODEL,
        },
    }


@app.get("/chat/api/config")
async def get_config():
    """获取前端配置"""
    return {
        "redirectUrl": settings.REDIRECT_URL,
        "enableTestPlatform": settings.ENABLE_TEST_PLATFORM,
    }


# 静态文件服务（生产环境）
import os
# dist 目录在项目根目录下
dist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "dist")
if os.path.exists(dist_path):
    app.mount("/chat/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")

    @app.get("/chat/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA 路由回退"""
        if full_path.startswith("api/"):
            return None
        file_path = os.path.join(dist_path, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(dist_path, "index.html"))
