# SQM v7.0.0-alpha — Docker 이미지
# ===================================
# 사용법:
#   docker build -t sqm-api .
#   docker run -p 8000:8000 -v sqm_data:/app/data sqm-api

FROM python:3.12-slim

LABEL maintainer="SQM Inventory <admin@sqm.co.kr>"
LABEL version="7.0.0-alpha"
LABEL description="SQM 재고관리 시스템 REST API"

# 시스템 패키지
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리
WORKDIR /app

# 의존성 먼저 (캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드
COPY . .

# 데이터 디렉토리
RUN mkdir -p /app/data/db /app/data/audit /app/data/backups

# 환경변수
ENV PYTHONUNBUFFERED=1
ENV SQM_JWT_SECRET=change-this-in-production
ENV SQM_TOKEN_EXPIRY=86400
ENV SQM_RATE_LIMIT=120/minute

# 포트
EXPOSE 8000

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# 실행
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
