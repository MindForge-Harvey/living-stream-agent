"""
数据库初始化脚本
用于创建数据库表和默认管理员账号
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import engine, Base, SessionLocal
from app.core.security import get_password_hash
from app.models.models import Admin, User


def init_database():
    """初始化数据库"""
    print("正在创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成")

    # 创建默认管理员
    db = SessionLocal()
    try:
        admin = db.query(Admin).filter(Admin.username == "admin").first()
        if not admin:
            print("正在创建默认管理员账号...")
            admin = Admin(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                is_active=True
            )
            db.add(admin)
            db.commit()
            print("默认管理员创建完成 (用户名: admin, 密码: admin123)")
        else:
            print("管理员账号已存在，跳过创建")
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
    print("数据库初始化完成！")
