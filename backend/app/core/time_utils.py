from datetime import datetime, timezone, timedelta

SHANGHAI_TZ = timezone(timedelta(hours=8))


def shanghai_now() -> datetime:
    """获取当前上海时间"""
    return datetime.now(SHANGHAI_TZ)


def format_shanghai_iso(dt: datetime) -> str:
    """将 datetime 格式化为上海时间的 ISO 字符串

    说明：MySQL 的 DateTime 字段不存储时区信息，但写入和存储都在
    上海时间（UTC+8）下运行，因此存储的无时区值即为上海时间。
    修复前错误地将默认值（UTC+8的实际时间）视为 UTC 而再次偏移。
    """
    if dt is None:
        return ""
    if dt.tzinfo is None:
        # MySQL 读取的无时区 datetime 本身就是上海时间
        dt = dt.replace(tzinfo=SHANGHAI_TZ)
    shanghai_dt = dt.astimezone(SHANGHAI_TZ)
    return shanghai_dt.isoformat()


def format_shanghai_display(dt: datetime) -> str:
    """将 datetime 格式化为上海时间的显示字符串

    说明：MySQL 的 DateTime 字段不存储时区信息，但写入和存储都在
    上海时间（UTC+8）下运行，因此存储的无时区值即为上海时间。
    """
    if dt is None:
        return ""
    if dt.tzinfo is None:
        # MySQL 读取的无时区 datetime 本身就是上海时间
        dt = dt.replace(tzinfo=SHANGHAI_TZ)
    shanghai_dt = dt.astimezone(SHANGHAI_TZ)
    return shanghai_dt.strftime("%Y-%m-%d %H:%M:%S")
