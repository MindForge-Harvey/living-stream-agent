"""Database schema migration runner.

This module is intentionally small and dependency-light so it can run both
from the Docker entrypoint and during normal FastAPI startup.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pymysql
from pymysql.constants import CLIENT

from app.core.config import settings
from app.core.database import Base, engine
from app.models import models  # noqa: F401 - registers SQLAlchemy models

logger = logging.getLogger(__name__)

MIGRATIONS_TABLE = "schema_migrations"
LOCK_NAME = "living_stream_agent_schema_migrations"


def ensure_model_tables() -> None:
    """Create missing tables from SQLAlchemy models.

    SQLAlchemy does not alter existing tables, so migrations still own schema
    changes. This only makes first-time deployments work before migration SQL
    references existing tables.
    """
    Base.metadata.create_all(bind=engine)


def get_migrations_dir() -> Path | None:
    """Resolve the migrations directory for Docker and local development."""
    configured = os.getenv("MIGRATIONS_DIR")
    candidates = []
    if configured:
        candidates.append(Path(configured))

    current = Path(__file__).resolve()
    candidates.extend(
        [
            Path("/app/migrations"),
            current.parents[3] / "deploy" / "migrations",
            Path.cwd() / "migrations",
            Path.cwd().parent / "deploy" / "migrations",
        ]
    )

    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def get_connection():
    """Open a raw MySQL connection that can execute multi-statement SQL files."""
    return pymysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DATABASE,
        charset="utf8mb4",
        autocommit=False,
        client_flag=CLIENT.MULTI_STATEMENTS,
    )


def execute_sql_file(cursor, path: Path) -> None:
    """Execute a SQL file and consume all result sets."""
    sql = path.read_text(encoding="utf-8").strip()
    if not sql:
        return

    cursor.execute(sql)
    while cursor.nextset():
        pass


def ensure_migrations_table(cursor) -> None:
    """Create the migration bookkeeping table if it does not exist."""
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{MIGRATIONS_TABLE}` (
          `version` varchar(100) NOT NULL,
          `description` varchar(255) NOT NULL,
          `applied_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (`version`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )


def acquire_lock(cursor) -> None:
    """Acquire a database-level lock so only one app instance migrates."""
    cursor.execute("SELECT GET_LOCK(%s, 30)", (LOCK_NAME,))
    locked = cursor.fetchone()[0]
    if locked != 1:
        raise RuntimeError("Timed out waiting for database migration lock")


def release_lock(cursor) -> None:
    """Release the migration lock."""
    cursor.execute("SELECT RELEASE_LOCK(%s)", (LOCK_NAME,))


def is_applied(cursor, version: str) -> bool:
    """Return whether a migration version has already been applied."""
    cursor.execute(
        f"SELECT COUNT(*) FROM `{MIGRATIONS_TABLE}` WHERE `version` = %s",
        (version,),
    )
    return cursor.fetchone()[0] > 0


def mark_applied(cursor, version: str) -> None:
    """Record a successfully applied migration."""
    cursor.execute(
        f"""
        INSERT INTO `{MIGRATIONS_TABLE}` (`version`, `description`)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE `description` = VALUES(`description`)
        """,
        (version, version),
    )


def run_migrations() -> None:
    """Create missing tables and apply pending SQL migrations."""
    ensure_model_tables()

    migrations_dir = get_migrations_dir()
    if migrations_dir is None:
        logger.info("No migrations directory found; skipped schema migrations")
        return

    migration_files = sorted(migrations_dir.glob("*.sql"))
    if not migration_files:
        logger.info("No SQL migrations found in %s", migrations_dir)
        return

    logger.info("Running database migrations from %s", migrations_dir)

    conn = get_connection()
    lock_acquired = False
    try:
        with conn.cursor() as cursor:
            acquire_lock(cursor)
            lock_acquired = True
            ensure_migrations_table(cursor)
            conn.commit()

            for migration_file in migration_files:
                version = migration_file.stem
                if version == "001_schema_migrations":
                    mark_applied(cursor, version)
                    conn.commit()
                    continue

                if is_applied(cursor, version):
                    logger.info("Skipping applied migration: %s", version)
                    continue

                logger.info("Applying migration: %s", version)
                execute_sql_file(cursor, migration_file)
                mark_applied(cursor, version)
                conn.commit()
                logger.info("Applied migration: %s", version)
    except Exception:
        conn.rollback()
        logger.exception("Database migration failed")
        raise
    finally:
        if lock_acquired:
            try:
                with conn.cursor() as cursor:
                    release_lock(cursor)
                conn.commit()
            except Exception:
                logger.exception("Failed to release migration lock")
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migrations()
    print("数据库迁移检查完成")
