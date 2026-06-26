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
        try:
            if os.path.exists(env_path):
                with open(env_path, "r") as f:
                    content = f.read()
                # 替换现有的 SECRET_KEY 行
                if "SECRET_KEY=" in content:
                    import re
                    content = re.sub(r'SECRET_KEY=.*', f'SECRET_KEY={key}', content)
                else:
                    # 在文件末尾添加
                    content = content.rstrip('\n') + f'\nSECRET_KEY={key}\n'
                with open(env_path, "w") as f:
                    f.write(content)
            else:
                # 创建 .env 文件
                with open(env_path, "w") as f:
                    f.write(f'SECRET_KEY={key}\n')
        except Exception:
            # 如果写入失败，至少在当前进程有效
            pass
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
