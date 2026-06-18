import os
import secrets
from pydantic_settings import BaseSettings


def get_secret_key() -> str:
    """获取或生成 SECRET_KEY"""
    import os
    key = os.environ.get("SECRET_KEY", "")
    if not key or key == "your-secret-key-change-in-production":
        key = secrets.token_hex(32)
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                content = f.read()
            if "SECRET_KEY=your-secret-key-change-in-production" in content:
                content = content.replace(
                    "SECRET_KEY=your-secret-key-change-in-production",
                    f"SECRET_KEY={key}"
                )
                with open(env_path, "w") as f:
                    f.write(content)
            elif "SECRET_KEY=\n" in content:
                content = content.replace("SECRET_KEY=\n", f"SECRET_KEY={key}\n")
                with open(env_path, "w") as f:
                    f.write(content)
    return key


def build_mysql_url(settings: 'Settings') -> str:
    """构建 MySQL 连接 URL"""
    return (
        f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}"
        f"@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
        f"?charset=utf8mb4"
    )


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "living-stream-agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # MySQL 配置
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "living_stream_agent"

    # JWT 配置
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24小时

    # OpenAI 配置
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "http://localhost:8765/v1"
    OPENAI_MODEL: str = "any"

    # CORS 配置
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]

    # 部署配置
    REDIRECT_URL: str = "/chat/test/login"
    ENABLE_TEST_PLATFORM: bool = True

    @property
    def DATABASE_URL(self) -> str:
        return build_mysql_url(self)

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
        env_file_encoding = 'utf-8'
        extra = 'ignore'


settings = Settings()

# 如果 SECRET_KEY 为空，使用生成的密钥
if not settings.SECRET_KEY:
    settings.SECRET_KEY = get_secret_key()
