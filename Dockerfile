FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    default-mysql-client \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/
COPY deploy/migrations/ ./migrations/

# Copy init script
COPY backend/init.sh /app/init.sh
RUN chmod +x /app/init.sh

EXPOSE 3001

CMD ["/app/init.sh"]
