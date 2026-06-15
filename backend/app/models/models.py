from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


def utc_now():
    """获取当前 UTC 时间"""
    return datetime.now(timezone.utc)


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True)
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)


class User(Base):
    __tablename__ = "users"

    id = Column(String(50), primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    lan_name = Column(String(100), default="")
    region_name = Column(String(100), default="")
    staff_code = Column(String(100), default="")
    staff_name = Column(String(100), default="")
    staff_pos_type = Column(String(100), default="")
    created_at = Column(DateTime, default=utc_now)


class Dialog(Base):
    __tablename__ = "dialogs"

    id = Column(String(50), primary_key=True, index=True)
    user_id = Column(String(100), index=True)
    tool_id = Column(String(100), index=True)
    tool_name = Column(String(200))
    title = Column(String(500), default="新对话")
    request_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class DialogMessage(Base):
    __tablename__ = "dialog_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dialog_id = Column(String(50), ForeignKey("dialogs.id"))
    request_id = Column(String(50), index=True)
    role = Column(String(20))
    content = Column(Text)
    created_at = Column(DateTime, default=utc_now)

    dialog = relationship("Dialog")


class ForbiddenWord(Base):
    __tablename__ = "forbidden_words"

    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String(200), index=True)
    replacement = Column(String(200), default="***")
    level = Column(String(20), default="multi")  # single=单字, multi=多字
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class UserMemory(Base):
    """用户长期记忆"""
    __tablename__ = "user_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), index=True, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class PlatformUser(Base):
    """平台用户信息"""
    __tablename__ = "platform_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform_user_id = Column(String(100), unique=True, index=True)
    lan_name = Column(String(100), default="")
    region_name = Column(String(100), default="")
    staff_code = Column(String(100), default="")
    staff_name = Column(String(100), default="")
    staff_pos_type = Column(String(100), default="")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
