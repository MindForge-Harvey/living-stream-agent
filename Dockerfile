FROM python:3.11-slim
WORKDIR /app

# Install Python dependencies
ARG PIP_INDEX_URL=https://pypi.org/simple
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
