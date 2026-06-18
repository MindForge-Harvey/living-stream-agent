# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Python runtime
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy frontend build to backend dist folder
COPY --from=frontend-build /app/dist/ ./dist/

# Create init script
RUN echo '#!/bin/bash\n\
cd /app/backend\n\
echo "Waiting for MySQL to be ready..."\n\
for i in $(seq 1 30); do\n\
  if python -c "import pymysql; pymysql.connect(host='\''mysql'\'', port=3306, user='\''root'\'', password='\''${MYSQL_PASSWORD:-living_stream_2024}'\'')" 2>/dev/null; then\n\
    echo "MySQL is ready!"\n\
    break\n\
  fi\n\
  echo "Attempt $i: MySQL not ready, waiting..."\n\
  sleep 2\n\
done\n\
python -c "from app.core.database import engine, Base; from app.models import models; Base.metadata.create_all(bind=engine); print(\"Database tables created.\")"\n\
python init_db.py\n\
exec uvicorn app.main:app --host 0.0.0.0 --port 3001\n\
' > /app/init.sh && chmod +x /app/init.sh

EXPOSE 3001

CMD ["/app/init.sh"]
