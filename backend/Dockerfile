# Backend Dockerfile
# Multi-stage build for optimized image size

# Stage 1: Builder
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04 as builder

# 환경 변수 설정
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3.10-dev \
    build-essential \
    curl \
    espeak-ng \
    ffmpeg \
    git \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Python 가상환경 생성
RUN python3 -m pip install --upgrade pip setuptools wheel

# 작업 디렉토리 설정
WORKDIR /app

# Python 패키지 설치
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Zonos 설치 (GitHub에서 직접 설치)
RUN pip3 install --no-cache-dir git+https://github.com/Zyphra/Zonos.git

# Stage 2: Runtime
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

# 환경 변수 설정
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/usr/local/bin:$PATH"

# 런타임 패키지만 설치
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    curl \
    espeak-ng \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 작업 디렉토리 설정
WORKDIR /app

# Builder 스테이지에서 Python 패키지 복사
COPY --from=builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 애플리케이션 코드 복사
COPY . .

# 업로드 디렉토리 생성
RUN mkdir -p uploads/speakers uploads/generated uploads/embeddings logs

# 비root 사용자 생성 및 권한 설정
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/api/system/health || exit 1

# 시작 스크립트 실행
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn"]
