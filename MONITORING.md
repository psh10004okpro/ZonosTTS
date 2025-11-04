# 📊 Zonos TTS API 모니터링 가이드

Prometheus와 Grafana를 사용한 실시간 성능 모니터링 시스템

## 🚀 빠른 시작

### Docker Compose로 전체 스택 실행

```bash
# 모든 서비스 시작 (Backend, Redis, Prometheus, Grafana)
docker-compose up -d

# 서비스 확인
docker-compose ps
```

### 접속 정보

| 서비스 | URL | 설명 |
|--------|-----|------|
| **Backend API** | http://localhost:8000 | TTS API 서버 |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **Metrics** | http://localhost:8000/metrics | Prometheus 메트릭 엔드포인트 |
| **Prometheus** | http://localhost:9090 | 메트릭 수집 및 쿼리 |
| **Grafana** | http://localhost:3001 | 대시보드 (admin/admin) |
| **Redis** | localhost:6379 | 캐싱 서버 |

## 📈 수집되는 메트릭

### 1. HTTP 요청 메트릭 (자동)

- `http_requests_total`: 총 HTTP 요청 수
- `http_request_duration_seconds`: HTTP 응답 시간 (히스토그램)
- `http_request_size_bytes`: 요청 크기
- `http_response_size_bytes`: 응답 크기

**라벨**: `method`, `handler`, `status`

### 2. TTS 생성 메트릭

```promql
# TTS 생성 요청 수
tts_requests_total{status="success", language="en-us", has_speaker="yes"}

# TTS 생성 시간 (p95)
histogram_quantile(0.95, rate(tts_generation_duration_seconds_bucket[5m]))

# 생성된 오디오 길이
tts_audio_duration_seconds

# 처리된 텍스트 길이
tts_text_length_characters
```

### 3. 캐싱 메트릭

```promql
# 캐시 히트율
rate(cache_requests_total{status="hit"}[5m]) / rate(cache_requests_total[5m]) * 100

# 캐시 메모리 사용량 (MB)
cache_memory_usage_megabytes

# 캐시된 키 개수
cache_keys_total{cache_type="speaker_embedding"}
```

### 4. 동시성 메트릭

```promql
# 활성 TTS 요청 수
active_tts_requests

# 대기 중인 요청 수
queued_tts_requests

# 활성 임베딩 생성 수
active_embedding_requests

# TTS 대기 시간
tts_wait_time_seconds
```

### 5. 에러 메트릭

```promql
# 에러 발생 수
errors_total{error_type="ModelInferenceError", endpoint="/api/tts/generate"}

# 타임아웃 발생 수
timeouts_total{operation="tts"}

# 큐 가득참 거부 수
queue_full_rejections_total{queue_type="tts"}
```

### 6. 모델 메트릭

```promql
# 모델 추론 시간
model_inference_duration_seconds{operation="tts"}

# 모델 로드 시간
model_load_duration_seconds
```

## 📊 Grafana 대시보드

### 기본 대시보드

자동으로 프로비저닝된 대시보드:

1. **Zonos TTS API Dashboard** (`monitoring/grafana-dashboard.json`)
   - HTTP 요청 속도 (RPS)
   - HTTP 응답 시간 (p95, p99)
   - TTS 생성 시간
   - 캐시 히트율
   - 활성/대기 요청 수
   - 에러율
   - 캐시 메모리 사용량
   - TTS 성공률
   - 화자 임베딩 생성 시간

### Grafana 첫 접속

1. http://localhost:3001 접속
2. 로그인: `admin` / `admin`
3. 비밀번호 변경 (선택사항)
4. 좌측 메뉴 > Dashboards > "Zonos TTS API Dashboard"

### 데이터 소스 추가 (자동 설정됨)

Prometheus 데이터 소스:
- Name: `Prometheus`
- URL: `http://prometheus:9090`
- Access: `Server (default)`

## 🔍 유용한 Prometheus 쿼리

### 성능 분석

```promql
# 평균 TTS 생성 시간 (언어별)
rate(tts_generation_duration_seconds_sum[5m]) / rate(tts_generation_duration_seconds_count[5m])

# TTS 처리량 (초당 요청 수)
rate(tts_requests_total[5m])

# 에러율 (%)
rate(tts_requests_total{status="failed"}[5m]) / rate(tts_requests_total[5m]) * 100
```

### 캐싱 효율성

```promql
# 캐시 히트율 (%)
sum(rate(cache_requests_total{status="hit"}[5m])) / sum(rate(cache_requests_total[5m])) * 100

# 캐시 미스로 인한 지연 시간 추정
avg(tts_generation_duration_seconds{has_speaker="yes"}) - avg(tts_wait_time_seconds)
```

### 시스템 부하

```promql
# 동시성 사용률 (%)
active_tts_requests / 2 * 100  # MAX_CONCURRENT_TTS=2

# 큐 사용률 (%)
queued_tts_requests / 10 * 100  # MAX_QUEUE_SIZE=10
```

## 🚨 알림 설정 (선택사항)

### Prometheus 알림 규칙 예시

`monitoring/alert_rules.yml` 생성:

```yaml
groups:
  - name: zonos_tts_alerts
    interval: 30s
    rules:
      # 높은 에러율
      - alert: HighErrorRate
        expr: rate(tts_requests_total{status="failed"}[5m]) / rate(tts_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "높은 TTS 에러율 감지"
          description: "에러율이 5%를 초과했습니다: {{ $value | humanizePercentage }}"

      # 큐 가득참
      - alert: QueueFull
        expr: queued_tts_requests >= 10
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "TTS 큐가 가득 찼습니다"
          description: "대기 중인 요청: {{ $value }}"

      # 느린 응답 시간
      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, rate(tts_generation_duration_seconds_bucket[5m])) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "TTS 생성 시간이 느립니다"
          description: "p95 응답 시간: {{ $value }}초"

      # 캐시 미사용
      - alert: CacheNotWorking
        expr: rate(cache_requests_total[5m]) == 0
        for: 10m
        labels:
          severity: info
        annotations:
          summary: "캐시가 작동하지 않습니다"
          description: "Redis 연결을 확인하세요"
```

## 📖 모니터링 Best Practices

### 1. 주요 지표 추적

**골든 시그널 (Golden Signals)**:
- **Latency** (지연시간): TTS 생성 시간
- **Traffic** (트래픽): 초당 요청 수
- **Errors** (에러): 에러율
- **Saturation** (포화도): 큐 사용률, GPU 사용률

### 2. 대시보드 구성

- **개요 대시보드**: 전체 시스템 상태 한눈에
- **상세 대시보드**: 각 컴포넌트별 심층 분석
- **비즈니스 대시보드**: 사용량, 비용 등

### 3. 알림 설정

- **Critical**: 즉시 대응 필요 (서비스 다운, 높은 에러율)
- **Warning**: 주의 필요 (느린 응답, 큐 가득참)
- **Info**: 정보성 (캐시 미사용, 업데이트 필요)

### 4. 데이터 보관

Prometheus 기본 설정:
- 보관 기간: 15일
- 스토리지: `prometheus_data` 볼륨

장기 보관이 필요한 경우:
- [Thanos](https://thanos.io/) 또는 [Cortex](https://cortexmetrics.io/) 사용
- 객체 스토리지 (S3, GCS)에 백업

## 🔧 문제 해결

### Prometheus에서 메트릭이 보이지 않음

1. Backend API가 실행 중인지 확인:
   ```bash
   curl http://localhost:8000/metrics
   ```

2. Prometheus 설정 확인:
   ```bash
   docker exec zonos-prometheus cat /etc/prometheus/prometheus.yml
   ```

3. Prometheus 타겟 상태 확인:
   - http://localhost:9090/targets

### Grafana 대시보드가 비어있음

1. Prometheus 데이터 소스 연결 확인:
   - Configuration > Data Sources > Prometheus
   - "Save & Test" 클릭

2. 메트릭 데이터 존재 확인:
   - Explore 메뉴에서 `up` 쿼리 실행

3. 대시보드 시간 범위 조정:
   - 우측 상단 시간 선택기에서 "Last 5 minutes" 선택

### 메모리 부족

Prometheus 메모리 제한 설정:

```yaml
# docker-compose.yml
prometheus:
  # ...
  deploy:
    resources:
      limits:
        memory: 2G
```

## 📚 추가 리소스

- [Prometheus 문서](https://prometheus.io/docs/)
- [Grafana 문서](https://grafana.com/docs/)
- [PromQL 가이드](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana 대시보드 갤러리](https://grafana.com/grafana/dashboards/)

## 🎯 다음 단계

1. **커스텀 대시보드 생성**: 비즈니스 요구에 맞게 조정
2. **알림 설정**: 중요한 이벤트 모니터링
3. **로그 통합**: Loki, ELK Stack 추가
4. **분산 트레이싱**: Jaeger, Zipkin 통합
5. **비용 최적화**: 메트릭 카디널리티 관리
