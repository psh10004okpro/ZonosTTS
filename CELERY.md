# 📋 Zonos TTS API - 비동기 작업 큐 가이드

Celery를 사용한 백그라운드 TTS 생성 시스템

## 🚀 빠른 시작

### Docker Compose로 전체 스택 실행

```bash
# 모든 서비스 시작 (Backend, Worker, Redis, Flower 등)
docker-compose up -d

# 서비스 상태 확인
docker-compose ps
```

### 접속 정보

| 서비스 | URL | 설명 |
|--------|-----|------|
| **Backend API** | http://localhost:8000 | TTS API 서버 |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **Flower** | http://localhost:5555 | Celery 작업 모니터링 |
| **Redis** | localhost:6379 | 메시지 브로커 |

## 🎯 왜 비동기 작업 큐가 필요한가?

### 문제점

1. **긴 처리 시간**: TTS 생성은 텍스트 길이에 따라 10초~1분+ 소요
2. **HTTP 타임아웃**: 긴 요청은 클라이언트/프록시 타임아웃 발생
3. **동시성 제한**: GPU 메모리 제한으로 동시 처리 불가
4. **사용자 경험**: 사용자가 응답을 기다리며 멈춤

### 해결책: Celery 비동기 작업 큐

```
클라이언트 → API: 작업 요청
API → 클라이언트: job_id 즉시 반환 (1초 미만)
API → Redis: 작업 큐에 추가
Celery Worker → Redis: 작업 가져오기
Celery Worker: TTS 생성 (백그라운드)
클라이언트 → API: job_id로 상태 확인 (폴링)
API → 클라이언트: 완료 시 결과 반환
```

**장점:**
- ✅ 즉시 응답 (타임아웃 없음)
- ✅ 백그라운드 처리 (사용자는 다른 작업 가능)
- ✅ 작업 상태 추적 (진행률 확인)
- ✅ 실패 시 자동 재시도
- ✅ 우선순위 큐 지원

## 📖 사용 방법

### 1. 비동기 TTS 생성 요청

#### 요청 예시

```bash
curl -X POST "http://localhost:8000/api/tts/generate-async" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a long text that will be processed in the background...",
    "language": "en-us",
    "speaker_id": 1,
    "speaking_rate": 1.0,
    "pitch_shift": 0.0,
    "emotion": "neutral",
    "priority": 5
  }'
```

#### 응답

```json
{
  "job_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "status": "pending",
  "message": "작업이 대기열에 추가되었습니다. job_id로 상태를 확인하세요.",
  "estimated_time_seconds": 30
}
```

### 2. 작업 상태 확인

#### 상태 확인 (폴링)

```bash
curl "http://localhost:8000/api/jobs/a1b2c3d4-e5f6-7890-1234-567890abcdef"
```

#### 응답 - 처리 중

```json
{
  "id": 1,
  "job_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "job_type": "tts",
  "status": "processing",
  "progress": 65,
  "request_params": {
    "text": "Hello, this is...",
    "language": "en-us",
    "speaker_id": 1
  },
  "created_at": "2025-11-04T10:30:00",
  "started_at": "2025-11-04T10:30:05"
}
```

#### 응답 - 완료

```json
{
  "id": 1,
  "job_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "job_type": "tts",
  "status": "completed",
  "progress": 100,
  "result_data": {
    "audio_id": 42,
    "filename": "tts_abc123_1699012345.wav",
    "duration": 12.5,
    "file_size": 1234567
  },
  "completed_at": "2025-11-04T10:30:45"
}
```

### 3. 작업 결과 가져오기

```bash
curl "http://localhost:8000/api/jobs/a1b2c3d4-e5f6-7890-1234-567890abcdef/result"
```

#### 응답 (완료 시)

```json
{
  "status": "completed",
  "job_type": "tts",
  "result": {
    "audio_id": 42,
    "filename": "tts_abc123_1699012345.wav",
    "file_path": "/app/uploads/generated/tts_abc123_1699012345.wav",
    "duration": 12.5,
    "file_size": 1234567,
    "sample_rate": 44100
  },
  "audio": {
    "id": 42,
    "filename": "tts_abc123_1699012345.wav",
    "text": "Hello, this is...",
    "duration": 12.5,
    "created_at": "2025-11-04T10:30:45"
  }
}
```

### 4. 작업 취소

```bash
curl -X DELETE "http://localhost:8000/api/jobs/a1b2c3d4-e5f6-7890-1234-567890abcdef"
```

## 🔧 로컬 개발 환경 설정

### 1. Celery Worker 실행

```bash
cd backend

# Worker 실행 (기본)
celery -A celery_app worker --loglevel=info

# Worker 실행 (동시성 제어)
celery -A celery_app worker --loglevel=info --concurrency=2

# Worker 실행 (특정 큐만)
celery -A celery_app worker --loglevel=info -Q tts,embedding
```

### 2. Celery Beat 실행 (주기적 작업)

```bash
# 별도 터미널에서 실행
celery -A celery_app beat --loglevel=info
```

### 3. Flower 모니터링 실행

```bash
# 별도 터미널에서 실행
celery -A celery_app flower --port=5555
```

그런 다음 http://localhost:5555 접속

## 📊 Flower 모니터링

Flower는 Celery 작업을 실시간으로 모니터링하는 웹 UI입니다.

### 주요 기능

1. **Tasks**: 실행 중/완료/실패한 작업 목록
2. **Workers**: 활성 워커 상태 및 리소스 사용량
3. **Broker**: Redis 연결 상태 및 큐 크기
4. **Monitor**: 실시간 작업 처리 속도 그래프

### 유용한 정보

- **Active Tasks**: 현재 처리 중인 작업 수
- **Success Rate**: 작업 성공률
- **Average Runtime**: 평균 처리 시간
- **Queue Length**: 대기 중인 작업 수

## 🔍 API 엔드포인트 전체 목록

### TTS 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/tts/generate` | 동기 TTS 생성 (즉시 응답 대기) |
| POST | `/api/tts/generate-async` | 비동기 TTS 생성 (job_id 반환) |
| POST | `/api/tts/stream` | 실시간 스트리밍 TTS |

### Jobs 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/jobs/{job_id}` | 작업 상태 조회 |
| GET | `/api/jobs/{job_id}/result` | 작업 결과 조회 (완료 시) |
| GET | `/api/jobs/` | 작업 목록 조회 (필터링 가능) |
| DELETE | `/api/jobs/{job_id}` | 작업 취소 |
| GET | `/api/jobs/statistics/summary` | 작업 통계 조회 |

## 🎛️ 설정 커스터마이징

### Celery Worker 설정

`backend/celery_app.py`:

```python
# 워커 동시성 (GPU 메모리에 따라 조정)
worker_prefetch_multiplier = 1  # 한 번에 하나씩 처리

# 태스크 타임아웃
task_soft_time_limit = 300  # 5분 (soft limit)
task_time_limit = 360  # 6분 (hard limit)

# 재시도 설정
task_acks_late = True  # 태스크 완료 후 ACK
task_reject_on_worker_lost = True  # 워커 다운 시 재실행
```

### 작업 우선순위

```python
# 높은 우선순위 (1-10, 10이 가장 높음)
task.apply_async(kwargs={...}, priority=10)

# 일반 우선순위
task.apply_async(kwargs={...}, priority=5)

# 낮은 우선순위
task.apply_async(kwargs={...}, priority=1)
```

### 큐 분리

```python
# TTS 작업은 tts 큐로
celery_app.conf.task_routes = {
    "tasks.tts_tasks.generate_tts_async": {"queue": "tts"},
    "tasks.tts_tasks.generate_speaker_embedding_async": {"queue": "embedding"},
}

# 워커 실행 시 큐 지정
celery -A celery_app worker -Q tts  # TTS 전용 워커
celery -A celery_app worker -Q embedding  # 임베딩 전용 워커
```

## 📈 주기적 작업 (Celery Beat)

### 자동으로 실행되는 작업

1. **cleanup-old-jobs** (매일 자정)
   - 7일 이상 된 완료/실패 작업 정리
   - 데이터베이스 용량 관리

2. **update-job-stats** (5분마다)
   - 작업 통계 업데이트
   - 모니터링 메트릭 갱신

### 스케줄 커스터마이징

`backend/celery_app.py`:

```python
celery_app.conf.beat_schedule = {
    "cleanup-old-results": {
        "task": "tasks.tts_tasks.cleanup_old_jobs",
        "schedule": crontab(hour=0, minute=0),  # 매일 자정
    },
    "update-job-stats": {
        "task": "tasks.tts_tasks.update_job_statistics",
        "schedule": 300.0,  # 5분 (초 단위)
    },
}
```

## 🔄 클라이언트 측 폴링 예시

### JavaScript/TypeScript

```typescript
async function generateTTSAsync(text: string): Promise<AudioFile> {
  // 1. 비동기 작업 시작
  const response = await fetch('/api/tts/generate-async', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language: 'en-us' })
  });
  const { job_id } = await response.json();

  // 2. 상태 폴링 (2초마다)
  while (true) {
    await new Promise(resolve => setTimeout(resolve, 2000));

    const statusResponse = await fetch(`/api/jobs/${job_id}`);
    const status = await statusResponse.json();

    console.log(`Progress: ${status.progress}%`);

    if (status.status === 'completed') {
      // 3. 결과 가져오기
      const resultResponse = await fetch(`/api/jobs/${job_id}/result`);
      return await resultResponse.json();
    } else if (status.status === 'failed') {
      throw new Error(status.error_message);
    }
  }
}
```

### Python

```python
import requests
import time

def generate_tts_async(text: str) -> dict:
    # 1. 비동기 작업 시작
    response = requests.post(
        "http://localhost:8000/api/tts/generate-async",
        json={"text": text, "language": "en-us"}
    )
    job_id = response.json()["job_id"]

    # 2. 상태 폴링
    while True:
        time.sleep(2)

        status_response = requests.get(f"http://localhost:8000/api/jobs/{job_id}")
        status = status_response.json()

        print(f"Progress: {status['progress']}%")

        if status["status"] == "completed":
            # 3. 결과 가져오기
            result_response = requests.get(f"http://localhost:8000/api/jobs/{job_id}/result")
            return result_response.json()
        elif status["status"] == "failed":
            raise Exception(status["error_message"])
```

## 🚨 문제 해결

### Worker가 작업을 처리하지 않음

1. Worker가 실행 중인지 확인:
   ```bash
   docker-compose logs celery-worker
   ```

2. Redis 연결 확인:
   ```bash
   docker exec -it zonos-redis redis-cli ping
   # PONG 응답이 와야 함
   ```

3. 큐에 작업이 쌓여있는지 확인:
   ```bash
   docker exec -it zonos-redis redis-cli
   > LLEN celery
   ```

### 작업이 계속 실패함

1. Worker 로그 확인:
   ```bash
   docker-compose logs -f celery-worker
   ```

2. GPU 메모리 확인:
   ```bash
   nvidia-smi
   ```

3. 동시성 낮추기:
   ```yaml
   # docker-compose.yml
   celery-worker:
     command: celery -A celery_app worker --loglevel=info --concurrency=1
   ```

### Flower에 접속할 수 없음

1. Flower 서비스 상태 확인:
   ```bash
   docker-compose ps flower
   ```

2. 포트가 열려있는지 확인:
   ```bash
   curl http://localhost:5555
   ```

3. 로그 확인:
   ```bash
   docker-compose logs flower
   ```

## 📚 추가 리소스

- [Celery 공식 문서](https://docs.celeryq.dev/)
- [Flower 문서](https://flower.readthedocs.io/)
- [Redis 문서](https://redis.io/docs/)

## 🎯 Best Practices

### 1. 적절한 타임아웃 설정

```python
# 짧은 작업
@celery_app.task(soft_time_limit=60, time_limit=90)
def short_task():
    pass

# 긴 작업
@celery_app.task(soft_time_limit=300, time_limit=360)
def long_task():
    pass
```

### 2. 재시도 전략

```python
@celery_app.task(
    autoretry_for=(NetworkError,),  # 네트워크 에러만 재시도
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,  # 지수 백오프
    retry_jitter=True  # 랜덤 지터 추가
)
def flaky_task():
    pass
```

### 3. 결과 보관 기간

```python
celery_app.conf.result_expires = 3600  # 1시간 후 결과 삭제
```

### 4. 메모리 관리

```python
celery_app.conf.worker_max_tasks_per_child = 50  # 50개 작업 후 워커 재시작
```

## 🔄 동기 vs 비동기 TTS 선택 가이드

### 동기 TTS 사용 (`/api/tts/generate`)

- ✅ 짧은 텍스트 (< 100자)
- ✅ 즉시 결과 필요
- ✅ 실시간 데모/테스트
- ❌ 긴 텍스트 (타임아웃 위험)

### 비동기 TTS 사용 (`/api/tts/generate-async`)

- ✅ 긴 텍스트 (> 500자)
- ✅ 배치 처리
- ✅ 안정적인 프로덕션 환경
- ✅ 사용자 경험 우선 (진행률 표시)
- ❌ 간단한 테스트 (폴링 구현 필요)

## 📊 성능 최적화

### Worker 동시성 설정

```bash
# CPU 집약적 작업
celery -A celery_app worker --concurrency=4

# GPU 집약적 작업 (메모리 제한)
celery -A celery_app worker --concurrency=1

# 혼합 (권장)
celery -A celery_app worker --concurrency=2
```

### 큐 우선순위 활용

```python
# 긴급 작업
high_priority_task.apply_async(priority=10)

# 일반 작업
normal_task.apply_async(priority=5)

# 배경 작업
low_priority_task.apply_async(priority=1)
```

### 결과 캐싱

동일한 텍스트는 캐시에서 가져오기 (Redis 캐싱 시스템 사용)

## 🎉 다음 단계

1. ✅ Celery 비동기 작업 큐 구현
2. 📝 프론트엔드에 폴링 UI 추가
3. 📊 작업 통계 대시보드 구현
4. 🔔 작업 완료 시 웹훅/알림 추가
5. 📈 더 많은 주기적 작업 추가
