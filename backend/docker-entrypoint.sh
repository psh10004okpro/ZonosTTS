#!/bin/bash
set -e

echo "🚀 Starting Zonos TTS API..."

# 환경 변수 출력 (디버깅용)
echo "Environment: ${ENV:-development}"
echo "Device: ${DEVICE:-cpu}"
echo "Redis Host: ${REDIS_HOST:-redis}"

# Redis 연결 대기
if [ "${REDIS_ENABLED}" = "true" ]; then
    echo "⏳ Waiting for Redis..."
    max_attempts=30
    attempt=0

    while ! nc -z ${REDIS_HOST:-redis} ${REDIS_PORT:-6379}; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            echo "❌ Redis connection timeout!"
            exit 1
        fi
        echo "  Attempt $attempt/$max_attempts: Redis not ready yet..."
        sleep 2
    done

    echo "✓ Redis is ready!"
fi

# 데이터베이스 마이그레이션 실행 (백엔드만)
if [ "$1" = "uvicorn" ] || [ "$1" = "fastapi" ]; then
    echo "📊 Running database migrations..."
    python3 migrations/001_add_indexes.py || echo "⚠ Migration skipped (may already be applied)"
    echo "✓ Database ready!"
fi

# 커맨드 실행
case "$1" in
    uvicorn)
        echo "🌐 Starting FastAPI server..."
        exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
        ;;
    celery-worker)
        echo "👷 Starting Celery worker..."
        exec celery -A celery_app worker --loglevel=info --concurrency=${CELERY_WORKER_CONCURRENCY:-2}
        ;;
    celery-beat)
        echo "⏰ Starting Celery beat..."
        exec celery -A celery_app beat --loglevel=info
        ;;
    flower)
        echo "🌸 Starting Flower..."
        exec celery -A celery_app flower --port=5555
        ;;
    *)
        # 기본: 전달된 명령 실행
        exec "$@"
        ;;
esac
