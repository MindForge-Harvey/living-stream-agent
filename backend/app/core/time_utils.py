from datetime import datetime, timezone, timedelta

SHANGHAI_TZ = timezone(timedelta(hours=8))


def shanghai_now() -> datetime:
    """获取当前上海时间"""
    return datetime.now(SHANGHAI_TZ)


def format_shanghai_iso(dt: datetime) -> str:
    """将 datetime 格式化为上海时间的 ISO 字符串"""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    shanghai_dt = dt.astimezone(SHANGHAI_TZ)
    return shanghai_dt.isoformat()


def format_shanghai_display(dt: datetime) -> str:
    """将 datetime 格式化为上海时间的显示字符串"""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    shanghai_dt = dt.astimezone(SHANGHAI_TZ)
    return shanghai_dt.strftime("%Y-%m-%d %H:%M:%S")
