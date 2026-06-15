from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


# 用户相关
class UserLogin(BaseModel):
    user_id: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# 违禁词相关
class ForbiddenWordCreate(BaseModel):
    word: str
    replacement: Optional[str] = "***"


class ForbiddenWordUpdate(BaseModel):
    word: Optional[str] = None
    replacement: Optional[str] = None


class ForbiddenWordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    word: str
    replacement: str
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")


class ForbiddenWordImportItem(BaseModel):
    word: str
    replacement: str
