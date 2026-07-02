from datetime import datetime, timezone, timedelta

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base

# 上海时区 (UTC+8)
SHANGHAI_TZ = timezone(timedelta(hours=8))

def utc_now():
    """获取当前时间（上海时区 UTC+8）"""
    return datetime.now(SHANGHAI_TZ)


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True)
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superadmin = Column(Boolean, default=False)
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
    dialog_id = Column(String(50), ForeignKey("dialogs.id"), index=True)
    request_id = Column(String(50), index=True)
    role = Column(String(20))
    content = Column(Text)
    metadata_json = Column(Text, nullable=True)  # 存储文件内容等元数据
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


class ScriptVersion(Base):
    """脚本版本历史"""
    __tablename__ = "script_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dialog_id = Column(String(50), ForeignKey("dialogs.id"), index=True)
    request_id = Column(String(50), index=True)
    version_type = Column(String(20))  # generated/scored/revised
    content = Column(Text)
    score_data = Column(Text, nullable=True)  # 打分数据（JSON格式）
    created_at = Column(DateTime, default=utc_now)

    dialog = relationship("Dialog")


class ScriptTemplate(Base):
    """脚本模板"""
    __tablename__ = "script_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), default="custom")  # preset/custom
    product_type = Column(String(100), nullable=True)  # 产品类型
    template_content = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    user_id = Column(String(100), nullable=True, index=True)  # NULL=全局(管理员创建), 有值=用户私有
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class ScoringConfig(Base):
    """打分配置"""
    __tablename__ = "scoring_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)  # 配置名称
    dimensions = Column(JSON, nullable=False)  # 评分维度配置
    prompt_template = Column(Text, nullable=False)  # 打分提示模板
    is_default = Column(Boolean, default=False)  # 是否默认配置
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
