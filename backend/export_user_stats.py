"""
用户使用统计 CSV 导出脚本（直接连数据库，复用 .env 配置）。

通过数据库导出，等价于接口 GET /chat/api/admin/conversations/stats/users/export，
无需依赖后端服务运行，也无需管理员登录 token。复用后端同一套查询逻辑（.env 配置）。

用法示例：
    # 导出全部（按对话数降序）
    python export_user_stats.py

    # 带上筛选 / 排序参数
    python export_user_stats.py --keyword 张 --lan-name 榆林 --sort-by totalRequests --sort-order desc

    # 指定输出文件
    python export_user_stats.py -o /tmp/user_usage_stats.csv

参数说明与后端接口一致：
    --keyword      搜索关键词（姓名/工号/用户ID）
    --lan-name     地市筛选
    --region-name  区县筛选
    --staff-pos-type 岗位筛选
    --sort-by      排序字段：dialogCount/totalRequests/firstUsed/lastUsed/staffName/lanName/regionName
    --sort-order   升序/降序：asc/desc（默认 desc）
"""

import sys
import os
import argparse
import logging

# 添加项目根目录到 Python 路径，使 `from app...` 导入可用
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import csv
import io

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.time_utils import format_shanghai_display
from app.api.dialogs import _build_user_stats_query, _apply_user_stats_sort

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def resolve_db_host(default_host: str) -> str:
    """解析数据库主机。

    .env 中默认为 host.docker.internal（容器内访问宿主机共享库用），
    但本脚本通常在宿主机直接运行，此时应回退到 127.0.0.1。
    """
    if default_host in ("host.docker.internal", "localhost", "127.0.0.1"):
        return "127.0.0.1"
    return default_host


def main():
    parser = argparse.ArgumentParser(
        description="用户使用统计 CSV 导出（直接连数据库，复用 .env 配置）"
    )
    parser.add_argument("--keyword", default=None, help="搜索关键词（姓名/工号/用户ID）")
    parser.add_argument("--lan-name", default=None, help="地市筛选")
    parser.add_argument("--region-name", default=None, help="区县筛选")
    parser.add_argument("--staff-pos-type", default=None, help="岗位筛选")
    parser.add_argument("--sort-by", default=None, help="排序字段: dialogCount/totalRequests/firstUsed/lastUsed/staffName/lanName/regionName")
    parser.add_argument("--sort-order", default="desc", help="排序方向: asc/desc（默认 desc）")
    parser.add_argument("--db-host", default=None, help="数据库主机（默认取 .env 的 MYSQL_HOST，宿主机运行时自动回退 127.0.0.1）")
    parser.add_argument("-o", "--output", default=None, help="输出文件路径（默认 用户使用统计_时间戳.csv）")
    args = parser.parse_args()

    db_host = args.db_host or resolve_db_host(settings.MYSQL_HOST)
    db_url = (
        f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}"
        f"@{db_host}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
        f"?charset=utf8mb4"
    )
    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        # 复用后端接口相同的查询逻辑，保证与接口统计口径一致
        query, stats_subq = _build_user_stats_query(
            db,
            keyword=args.keyword,
            lan_name=args.lan_name,
            region_name=args.region_name,
            staff_pos_type=args.staff_pos_type,
        )
        query = _apply_user_stats_sort(query, stats_subq, args.sort_by, args.sort_order)
        rows = query.all()
    finally:
        db.close()

    out = io.StringIO()
    out.write("\ufeff")  # BOM，便于 Excel 正确识别 UTF-8
    writer = csv.writer(out)
    writer.writerow(["用户ID", "姓名", "工号", "岗位", "地市", "区县", "对话数", "请求数", "首次使用", "最近使用"])
    for row in rows:
        writer.writerow([
            row.user_id,
            row.staff_name or "",
            row.staff_code or "",
            row.staff_pos_type or "",
            row.lan_name or "",
            row.region_name or "",
            row.dialog_count,
            row.total_requests or 0,
            format_shanghai_display(row.first_used) if row.first_used else "",
            format_shanghai_display(row.last_used) if row.last_used else "",
        ])
    text = out.getvalue()

    # 未指定输出文件时，使用与接口一致的中文文件名
    filename = args.output
    if not filename:
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"用户使用统计_{timestamp}.csv"

    with open(filename, "w", encoding="utf-8", newline="") as f:
        f.write(text)

    logger.info("已导出 %d 行到: %s", len(rows), filename)


if __name__ == "__main__":
    main()
