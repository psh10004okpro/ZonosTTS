# ⚡ Zonos TTS API - 빠른 시작 가이드

5분 안에 Zonos TTS API를 실행하세요!

## 🎯 전제 조건

- Docker & Docker Compose 설치
- (GPU 사용 시) NVIDIA Docker 설치

## 🚀 실행 방법

### Option 1: GPU 사용 (권장)

```bash
# 1. 저장소 클론
git clone <repository-url>
cd ZonosTTS

# 2. Docker Compose 실행
docker-compose up -d

# 3. 로그 확인 (초기 모델 다운로드 시 시간 소요)
docker-compose logs -f backend

# 4. 준비 완료!
# API 문서: http://localhost:8000/docs
```

### Option 2: CPU 사용

```bash
# CPU 전용 실행
docker-compose -f docker-compose.cpu.yml up -d

# 로그 확인
docker-compose -f docker-compose.cpu.yml logs -f backend
```

## 🌐 접속 정보

| 서비스 | URL | 설명 |
|--------|-----|------|
| **API 문서** | http://localhost:8000/docs | Swagger UI |
| **Flower** | http://localhost:5555 | Celery 모니터링 |
| **Grafana** | http://localhost:3001 | 메트릭 대시보드 |

## 🧪 API 테스트

### 1. TTS 생성 (동기)

```bash
curl -X POST "http://localhost:8000/api/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test",
    "language": "en-us",
    "save_to_db": true
  }'
```

### 2. TTS 생성 (비동기)

```bash
# 작업 시작
curl -X POST "http://localhost:8000/api/tts/generate-async" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is an async test",
    "language": "en-us"
  }'

# 응답: {"job_id": "abc123", "status": "pending", ...}

# 상태 확인
curl "http://localhost:8000/api/jobs/abc123"

# 결과 가져오기 (완료 후)
curl "http://localhost:8000/api/jobs/abc123/result"
```

### 3. 헬스체크

```bash
curl "http://localhost:8000/api/system/health"
```

## 🛑 중지

```bash
# 서비스 중지
docker-compose down

# 데이터까지 모두 삭제 (주의!)
docker-compose down -v
```

## 📚 자세한 문서

- **전체 설정**: [DOCKER_SETUP.md](./DOCKER_SETUP.md)
- **API 가이드**: [README.md](./README.md)
- **비동기 작업**: [CELERY.md](./CELERY.md)
- **모니터링**: [MONITORING.md](./MONITORING.md)
- **DB 최적화**: [DATABASE_OPTIMIZATION.md](./DATABASE_OPTIMIZATION.md)

## ⚠️ 문제 해결

### GPU를 찾을 수 없음

```bash
# NVIDIA Container Toolkit 설치 확인
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# 안되면 CPU 버전 사용
docker-compose -f docker-compose.cpu.yml up -d
```

### 포트가 이미 사용중

```bash
# 사용 중인 프로세스 확인
sudo lsof -i :8000

# 또는 docker-compose.yml에서 포트 변경
# ports: - "8001:8000"
```

### 메모리 부족

```bash
# 동시성 낮추기 (docker-compose.yml 또는 .env)
MAX_CONCURRENT_TTS=1
CELERY_WORKER_CONCURRENCY=1
```

## 🎉 다음 단계

1. ✅ Swagger UI에서 API 테스트
2. ✅ Flower에서 비동기 작업 모니터링
3. ✅ Grafana에서 성능 메트릭 확인
4. ✅ 화자 목소리 복제 시도
5. ✅ 프론트엔드 연동

궁금한 점이 있으면 [DOCKER_SETUP.md](./DOCKER_SETUP.md)를 참고하세요!
