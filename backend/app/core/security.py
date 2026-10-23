from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码，支持 bcrypt 和旧 SHA256 格式（向后兼容）"""
    try:
        if hashed_password.startswith("$2"):
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
    except Exception:
        pass
    # 向后兼容旧的 SHA256 格式
    sha256_hash = hashlib.sha256(plain_password.encode()).hexdigest()
    return sha256_hash == hashed_password


def get_password_hash(password: str) -> str:
    """生成密码哈希（使用 bcrypt）"""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("密码过长，bcrypt 最多支持 72 bytes")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 中未包含用户信息",
        )
    if user_id.startswith("admin:") or user_id.startswith("super_admin:"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的用户 Token",
        )
    return {"user_id": user_id}
