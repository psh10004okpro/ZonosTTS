# 🐳 Zonos TTS API - Docker 설치 및 실행 가이드

완전한 Docker 환경 구성 및 실행 가이드입니다.

## 📋 사전 요구사항

### 필수
- Docker: 20.10 이상
- Docker Compose: 2.0 이상
- 디스크 공간: 최소 10GB (모델 다운로드 포함)
- RAM: 최소 4GB (CPU), 8GB+ 권장 (GPU)

### GPU 사용 시 추가 요구사항
- NVIDIA GPU (CUDA 11.8 호환)
- NVIDIA Driver: 최신 버전
- NVIDIA Container Toolkit

#### NVIDIA Container Toolkit 설치 (Ubuntu)

```bash
# 1. 저장소 설정
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
   && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
   && curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
      sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
      sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# 2. 설치
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# 3. Docker 재시작
sudo systemctl restart docker

# 4. GPU 테스트
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

## 🚀 빠른 시작

### 1. GPU 환경 (권장)

```bash
# 저장소 클론
git clone <repository-url>
cd ZonosTTS

# Docker Compose로 전체 스택 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f backend

# 상태 확인
docker-compose ps
```

### 2. CPU 환경

```bash
# CPU 전용 설정으로 실행
docker-compose -f docker-compose.cpu.yml up -d

# 로그 확인
docker-compose -f docker-compose.cpu.yml logs -f backend
```

## 📦 서비스 구성

### 기본 서비스 (항상 실행)

| 서비스 | 포트 | 설명 |
|--------|------|------|
| **backend** | 8000 | FastAPI 백엔드 API |
| **redis** | 6379 | 캐싱 및 Celery 브로커 |
| **celery-worker** | - | 비동기 TTS 작업 처리 |
| **celery-beat** | - | 주기적 작업 스케줄러 |
| **flower** | 5555 | Celery 모니터링 UI |

### 선택 서비스

| 서비스 | 포트 | 설명 |
|--------|------|------|
| frontend | 3000 | React 프론트엔드 (옵션) |
| prometheus | 9090 | 메트릭 수집 |
| grafana | 3001 | 메트릭 시각화 |

## 🔧 설정 방법

### 환경 변수 설정

프로덕션 환경에서는 `.env` 파일 생성:

```bash
# .env 파일 생성
cat > .env << 'EOF'
# 환경
ENV=production

# 디바이스 설정
DEVICE=cuda  # 또는 cpu

# 데이터베이스
DATABASE_URL=sqlite+aiosqlite:///./data/zonos_tts.db

# Redis
REDIS_ENABLED=true
REDIS_HOST=redis
REDIS_PORT=6379

# 동시성 제어
MAX_CONCURRENT_TTS=2
MAX_CONCURRENT_EMBEDDING=1
MAX_QUEUE_SIZE=10

# Celery
CELERY_WORKER_CONCURRENCY=2

# 보안 (프로덕션에서 변경 필수!)
SECRET_KEY=change-this-in-production
API_KEYS=your-api-key-here
EOF
```

### GPU 메모리 설정

GPU 메모리가 제한적인 경우:

```yaml
# docker-compose.override.yml 생성
services:
  backend:
    environment:
      - MAX_CONCURRENT_TTS=1
      - MAX_CONCURRENT_EMBEDDING=1

  celery-worker:
    environment:
      - CELERY_WORKER_CONCURRENCY=1
```

## 📝 사용 예시

### 전체 스택 시작

```bash
# 백그라운드 실행
docker-compose up -d

# 프론트그라운드 실행 (로그 확인)
docker-compose up

# 특정 서비스만 시작
docker-compose up -d backend redis celery-worker
```

### 로그 확인

```bash
# 모든 서비스 로그
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f backend
docker-compose logs -f celery-worker

# 최근 100줄만
docker-compose logs --tail=100 backend
```

### 서비스 재시작

```bash
# 모든 서비스 재시작
docker-compose restart

# 특정 서비스만 재시작
docker-compose restart backend

# 코드 변경 후 재빌드
docker-compose up -d --build backend
```

### 서비스 중지

```bash
# 서비스 중지 (컨테이너 유지)
docker-compose stop

# 서비스 중지 및 컨테이너 삭제
docker-compose down

# 볼륨까지 모두 삭제 (주의!)
docker-compose down -v
```

## 🌐 접속 정보

서비스 시작 후 다음 URL로 접속:

| 서비스 | URL | 인증 |
|--------|-----|------|
| **API 문서** | http://localhost:8000/docs | - |
| **API 엔드포인트** | http://localhost:8000 | API Key |
| **Flower** | http://localhost:5555 | - |
| **Prometheus** | http://localhost:9090 | - |
| **Grafana** | http://localhost:3001 | admin/admin |
| **Frontend** | http://localhost:3000 | - |

## 🧪 헬스체크

### API 상태 확인

```bash
# 헬스체크
curl http://localhost:8000/api/system/health

# 시스템 통계
curl http://localhost:8000/api/system/stats

# 캐시 통계
curl http://localhost:8000/api/system/cache/stats
```

### Docker 상태 확인

```bash
# 컨테이너 상태
docker-compose ps

# 리소스 사용량
docker stats

# 특정 컨테이너 상태
docker inspect zonos-backend
```

## 🔍 문제 해결

### 1. 컨테이너가 시작되지 않음

```bash
# 로그 확인
docker-compose logs backend

# 컨테이너 재생성
docker-compose up -d --force-recreate backend

# 이미지 재빌드
docker-compose build --no-cache backend
```

### 2. GPU를 찾을 수 없음

```bash
# GPU 확인
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# NVIDIA Container Toolkit 재설치
sudo apt-get install --reinstall nvidia-container-toolkit
sudo systemctl restart docker
```

### 3. Redis 연결 실패

```bash
# Redis 상태 확인
docker-compose exec redis redis-cli ping

# Redis 재시작
docker-compose restart redis

# Redis 로그 확인
docker-compose logs redis
```

### 4. 포트가 이미 사용중

```bash
# 포트 사용 확인
sudo lsof -i :8000
sudo lsof -i :6379

# docker-compose.yml에서 포트 변경
# ports:
#   - "8001:8000"  # 호스트:컨테이너
```

### 5. 디스크 공간 부족

```bash
# 사용되지 않는 이미지/컨테이너 정리
docker system prune -a

# 볼륨 정리 (주의: 데이터 삭제됨)
docker volume prune

# 전체 정리 (주의: 모든 Docker 데이터 삭제)
docker system prune -a --volumes
```

### 6. 메모리 부족

```bash
# 메모리 사용량 확인
docker stats

# 동시성 설정 낮추기 (.env)
MAX_CONCURRENT_TTS=1
CELERY_WORKER_CONCURRENCY=1
```

## 🔧 고급 설정

### 커스텀 docker-compose.override.yml

```yaml
# docker-compose.override.yml
version: '3.8'

services:
  backend:
    environment:
      - DEBUG=true
      - LOG_LEVEL=debug
    volumes:
      - ./backend:/app  # 개발용: 코드 hot-reload

  redis:
    ports:
      - "6380:6379"  # 다른 포트 사용
```

### 프로덕션 최적화

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    environment:
      - ENV=production
      - DEBUG=false
      - LOG_LEVEL=warning
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          memory: 2G

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
```

### Docker Swarm / Kubernetes

```bash
# Docker Swarm 초기화
docker swarm init

# 스택 배포
docker stack deploy -c docker-compose.yml zonos-tts

# 서비스 확인
docker service ls
docker service logs zonos-tts_backend
```

## 📊 모니터링

### 모니터링 스택 활성화

```bash
# Prometheus + Grafana 함께 실행
docker-compose --profile monitoring up -d

# 또는 CPU 버전
docker-compose -f docker-compose.cpu.yml --profile monitoring up -d
```

### Grafana 대시보드 설정

1. http://localhost:3001 접속
2. admin/admin으로 로그인
3. Data Sources > Add Prometheus
   - URL: `http://prometheus:9090`
4. Dashboards > Import > Upload `monitoring/grafana-dashboard.json`

## 🔐 보안 고려사항

### 프로덕션 체크리스트

- [ ] `.env` 파일에 강력한 SECRET_KEY 설정
- [ ] API Key 인증 활성화
- [ ] Redis 비밀번호 설정
- [ ] Grafana 기본 비밀번호 변경
- [ ] HTTPS/TLS 인증서 설정 (Nginx 사용)
- [ ] 방화벽 설정 (필요한 포트만 오픈)
- [ ] 정기 백업 설정
- [ ] 로그 로테이션 설정

### Redis 비밀번호 설정

```yaml
# docker-compose.yml
services:
  redis:
    command: redis-server --requirepass your_strong_password
    environment:
      - REDIS_PASSWORD=your_strong_password

  backend:
    environment:
      - REDIS_PASSWORD=your_strong_password
```

## 📦 백업 및 복구

### 데이터 백업

```bash
# 볼륨 백업
docker run --rm \
  -v zonos_db_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/db-$(date +%Y%m%d).tar.gz -C /data .

# uploads 백업
docker run --rm \
  -v $(pwd)/uploads:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/uploads-$(date +%Y%m%d).tar.gz -C /data .
```

### 데이터 복구

```bash
# 볼륨 복구
docker run --rm \
  -v zonos_db_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/db-20250101.tar.gz -C /data
```

## 🚀 성능 최적화

### Docker 설정 최적화

```json
// /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
```

### 빌드 캐시 활용

```bash
# BuildKit 활성화
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# 병렬 빌드
docker-compose build --parallel

# 캐시 활용하여 빌드
docker-compose build --build-arg BUILDKIT_INLINE_CACHE=1
```

## 📚 추가 리소스

- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Compose 문서](https://docs.docker.com/compose/)
- [NVIDIA Container Toolkit](https://github.com/NVIDIA/nvidia-docker)
- [FastAPI 배포 가이드](https://fastapi.tiangolo.com/deployment/)

## 🆘 지원

문제가 발생하면:

1. 로그 확인: `docker-compose logs -f`
2. GitHub Issues에 문제 등록
3. 커뮤니티 Discord/Slack 채널

---

**다음 단계:** [API 문서](http://localhost:8000/docs) | [모니터링 가이드](./MONITORING.md) | [Celery 가이드](./CELERY.md)
