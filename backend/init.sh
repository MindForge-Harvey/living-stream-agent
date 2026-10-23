#!/bin/bash
set -euo pipefail
cd /app/backend

echo "Waiting for MySQL to be ready..."
mysql_ready=0
for i in $(seq 1 30); do
  if python -c "
import os
env = {}
with open('/app/.env', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, _, v = line.partition('=')
        env[k.strip()] = v.strip().strip('\"').strip(\"'\")
import pymysql
pymysql.connect(
    host=env.get('MYSQL_HOST', 'mysql'),
    port=int(env.get('MYSQL_PORT', '3306')),
    user=env.get('MYSQL_USER', 'root'),
    password=env.get('MYSQL_PASSWORD', 'living_stream_2024'),
    database=env.get('MYSQL_DATABASE', 'living_stream_agent'),
)" 2>/dev/null; then
    echo "MySQL is ready!"
    mysql_ready=1
    break
  fi
  echo "Attempt $i: MySQL not ready, waiting..."
  sleep 2
done
if [ "$mysql_ready" != "1" ]; then
  echo "MySQL is not ready after 30 attempts."
  exit 1
fi
python -m app.core.migrations
export SKIP_STARTUP_MIGRATIONS=1
python init_db.py
exec uvicorn app.main:app --host 0.0.0.0 --port 3001
