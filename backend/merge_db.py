"""
MySQL 数据合并脚本
使用方式:
  python merge_db.py --target-host 目标库IP --target-pass 目标库密码 [--source-host 源库IP]

默认源库为本地 localhost:3308 (docker映射端口)
"""

import argparse
import pymysql
from pymysql.cursors import DictCursor

TARGET_DB = "living_stream_agent"
SOURCE_DB = "living_stream_agent"

# 表合并顺序（先导无外键依赖的表）
TABLES = [
    "platform_users",        # 仅依赖自身（platform_user_id 唯一）
    "users",                 # String 主键，无需自增处理
    "admins",                # username 唯一
    "forbidden_words",       # 无外键
    "suggested_questions",   # 无外键
    "scoring_configs",       # 无外键
    "user_memories",         # 无外键
    "dictations",            # 如果有
    "dialogs",               # String 主键，无冲突
    "dialog_messages",       # 依赖 dialogs
    "script_versions",       # 依赖 dialogs
    "script_templates",      # 无外键（user_id 只是逻辑关联）
]


def get_connection(host, port, user, password, database):
    return pymysql.connect(
        host=host, port=port, user=user, password=password,
        database=database, charset="utf8mb4", cursorclass=DictCursor,
    )


def get_max_ids(cursor, table, id_column="id"):
    cursor.execute(f"SELECT MAX({id_column}) AS max_id FROM {table}")
    row = cursor.fetchone()
    return (row["max_id"] or 0) if row else 0


def merge_table(src_cursor, tgt_cursor, table, id_offset, id_column="id"):
    src_cursor.execute(f"SELECT * FROM {table}")
    rows = src_cursor.fetchall()
    if not rows:
        print(f"  [{table}] 源库无数据，跳过")
        return 0

    inserted = 0
    skipped = 0

    for row in rows:
        columns = list(row.keys())
        placeholders = ", ".join(["%s"] * len(columns))

        # 获取目标库现有主键
        src_id = row[id_column]

        if id_offset > 0 and id_column in row:
            # 自增 ID 表 -- 检查冲突
            tgt_cursor.execute(f"SELECT 1 FROM {table} WHERE {id_column} = %s", (src_id,))
            if tgt_cursor.fetchone():
                # 冲突：跳过（原始数据已存在）
                skipped += 1
                continue

        # 处理唯一键冲突
        if table == "platform_users":
            tgt_cursor.execute("SELECT 1 FROM platform_users WHERE platform_user_id = %s", (row["platform_user_id"],))
            if tgt_cursor.fetchone():
                skipped += 1
                continue
        elif table == "users":
            tgt_cursor.execute("SELECT 1 FROM users WHERE id = %s", (row["id"],))
            if tgt_cursor.fetchone():
                skipped += 1
                continue
        elif table == "admins":
            tgt_cursor.execute("SELECT 1 FROM admins WHERE username = %s", (row["username"],))
            if tgt_cursor.fetchone():
                skipped += 1
                continue
        elif table == "dialogs":
            tgt_cursor.execute("SELECT 1 FROM dialogs WHERE id = %s", (row["id"],))
            if tgt_cursor.fetchone():
                skipped += 1
                continue

        # 插入数据
        values = [row[col] for col in columns]
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        try:
            tgt_cursor.execute(sql, values)
            inserted += 1
        except pymysql.err.IntegrityError as e:
            print(f"  [{table}] 跳过冲突行 id={row.get(id_column, '?')}: {e}")
            skipped += 1

    return inserted, skipped


def main():
    parser = argparse.ArgumentParser(description="MySQL 数据合并工具")
    parser.add_argument("--source-host", default="127.0.0.1", help="源 MySQL 主机（默认 127.0.0.1）")
    parser.add_argument("--source-port", type=int, default=3308, help="源 MySQL 端口（默认 3308）")
    parser.add_argument("--source-user", default="root", help="源 MySQL 用户（默认 root）")
    parser.add_argument("--source-pass", default="living_stream_2024", help="源 MySQL 密码")
    parser.add_argument("--target-host", required=True, help="目标 MySQL 主机")
    parser.add_argument("--target-port", type=int, default=3306, help="目标 MySQL 端口（默认 3306）")
    parser.add_argument("--target-user", default="root", help="目标 MySQL 用户（默认 root）")
    parser.add_argument("--target-pass", required=True, help="目标 MySQL 密码")
    args = parser.parse_args()

    print("=" * 60)
    print(f"源库:   {args.source_host}:{args.source_port}/{SOURCE_DB}")
    print(f"目标库: {args.target_host}:{args.target_port}/{TARGET_DB}")
    print("=" * 60)

    src_conn = get_connection(args.source_host, args.source_port, args.source_user, args.source_pass, SOURCE_DB)
    tgt_conn = get_connection(args.target_host, args.target_port, args.target_user, args.target_pass, TARGET_DB)

    src_cursor = src_conn.cursor()
    tgt_cursor = tgt_conn.cursor()

    print("\n开始合并数据...\n")

    for table in TABLES:
        print(f"[{table}] ...", end=" ", flush=True)
        try:
            result = merge_table(src_cursor, tgt_cursor, table)
            if result:
                inserted, skipped = result
                print(f"插入 {inserted} 行, 跳过 {skipped} 行")
            tgt_conn.commit()
        except Exception as e:
            tgt_conn.rollback()
            print(f"出错: {e}")

    src_cursor.close()
    tgt_cursor.close()
    src_conn.close()
    tgt_conn.close()

    print("\n合并完成！")


if __name__ == "__main__":
    main()
