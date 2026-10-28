FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先装依赖，利用镜像层缓存
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# SQLite 数据目录（由 compose 挂载卷持久化）
RUN mkdir -p /app/data

ENV HOST=0.0.0.0 \
    PORT=8000 \
    RELOAD=0 \
    DATABASE_URL=sqlite:///./data/app.db

EXPOSE 8000

CMD ["python", "main.py"]
