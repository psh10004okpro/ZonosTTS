# Zonos TTS API 시스템

Zyphra의 오픈소스 TTS 모델 **Zonos**를 사용한 전문적인 음성 합성 API 시스템입니다.

## 🌟 주요 기능

### 🎤 음성 생성
- **고품질 TTS**: Zonos-v0.1 모델을 사용한 자연스러운 음성 합성
- **다국어 지원**: 영어, 일본어, 중국어, 프랑스어, 독일어
- **세밀한 제어**: 말하기 속도, 피치, 감정 조절 가능
- **다양한 출력**: WAV 파일 생성 및 다운로드

### 🔄 실시간 스트리밍
- **Server-Sent Events (SSE)**: 실시간 오디오 스트리밍
- **낮은 지연시간**: 청크 단위 스트리밍으로 빠른 응답
- **브라우저 재생**: Web Audio API를 통한 즉시 재생

### 🎭 음성 복제
- **화자 샘플 업로드**: 5-30초 오디오로 음성 복제
- **임베딩 생성**: 화자 특성을 캡처한 임베딩 저장
- **다중 화자 관리**: 여러 화자 프로필 저장 및 관리

### 📊 관리 기능
- **대시보드**: 통계 및 최근 파일 조회
- **파일 관리**: 생성된 음성 파일 목록, 검색, 다운로드, 삭제
- **화자 관리**: 화자 샘플 업로드, 목록, 삭제

## 🏗️ 프로젝트 구조

```
zonos-tts/
├── backend/                  # FastAPI 백엔드
│   ├── main.py              # 메인 애플리케이션
│   ├── config.py            # 설정 및 상수
│   ├── models/              # 데이터베이스 모델 및 Zonos 래퍼
│   │   ├── database.py      # SQLAlchemy ORM 모델
│   │   └── zonos_model.py   # Zonos 모델 래퍼
│   ├── routes/              # API 라우터
│   │   ├── tts.py           # TTS API
│   │   ├── speakers.py      # 화자 관리 API
│   │   ├── audio.py         # 파일 관리 API
│   │   └── system.py        # 시스템 모니터링 API
│   ├── services/            # 비즈니스 로직
│   │   ├── tts_service.py   # TTS 서비스
│   │   ├── speaker_service.py  # 화자 서비스
│   │   └── stream_service.py   # 스트리밍 서비스
│   ├── utils/               # 유틸리티
│   │   ├── file_validator.py   # 파일 검증
│   │   └── concurrency.py      # 동시성 제어
│   └── requirements.txt     # Python 의존성
├── frontend/                # React 프론트엔드
│   ├── src/
│   │   ├── pages/           # 페이지 컴포넌트
│   │   │   ├── Dashboard.jsx   # 대시보드
│   │   │   ├── Generate.jsx    # 음성 생성
│   │   │   ├── Test.jsx         # 파일 테스트
│   │   │   └── Speakers.jsx     # 화자 관리
│   │   ├── services/        # API 서비스
│   │   │   └── api.js
│   │   └── utils/           # 유틸리티
│   │       └── audioUtils.js
│   └── package.json         # Node.js 의존성
├── docker-compose.yml       # Docker Compose 설정
└── README.md                # 이 파일
```

## 🚀 시작하기

### 시스템 요구사항

#### 하드웨어
- **GPU**: NVIDIA GPU (6GB+ VRAM 권장)
  - RTX 2080 Ti 이상
  - CUDA 11.8 이상
- **RAM**: 8GB 이상
- **저장공간**: 10GB 이상

#### 소프트웨어
- **OS**: Ubuntu 22.04/24.04 또는 macOS
- **Python**: 3.10 이상
- **Node.js**: 18 이상
- **eSpeak-NG**: 음소 변환 라이브러리

### 설치 방법

#### 방법 1: 로컬 설치

**1. 저장소 클론**
```bash
git clone https://github.com/yourusername/zonos-tts.git
cd zonos-tts
```

**2. eSpeak-NG 설치**
```bash
# Ubuntu/Debian
sudo apt install espeak-ng

# macOS
brew install espeak-ng
```

**3. Backend 설정**
```bash
cd backend

# 가상환경 생성 (권장)
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# Zonos 설치
pip install git+https://github.com/Zyphra/Zonos.git

# 환경 변수 설정
cp ../.env.example .env
# .env 파일을 편집하여 설정 조정

# 서버 실행
python main.py
```

**4. Frontend 설정**
```bash
cd ../frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

**5. 접속**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API 문서: http://localhost:8000/docs

#### 방법 2: Docker 설치

**1. Docker 및 Docker Compose 설치**
```bash
# Docker 설치 (Ubuntu)
sudo apt update
sudo apt install docker.io docker-compose

# NVIDIA Docker Runtime 설치 (GPU 사용 시)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt update
sudo apt install nvidia-docker2
sudo systemctl restart docker
```

**2. 환경 변수 설정**
```bash
cp .env.example .env
# .env 파일 편집
```

**3. 컨테이너 실행**
```bash
# GPU 사용
docker-compose up -d

# CPU만 사용 (docker-compose.yml에서 deploy 섹션 제거)
docker-compose up -d
```

**4. 로그 확인**
```bash
docker-compose logs -f
```

**5. 중지 및 제거**
```bash
docker-compose down
```

## 📖 사용 가이드

### 1. 화자 추가하기

1. **화자 관리** 페이지로 이동
2. **"+ 새 화자 추가"** 버튼 클릭
3. 화자 정보 입력:
   - 화자 이름
   - 언어 선택
   - 오디오 샘플 업로드 (5-30초, WAV/MP3/FLAC)
4. **"추가"** 버튼 클릭

### 2. 음성 생성하기

1. **음성 생성** 페이지로 이동
2. 텍스트 입력 (최대 5000자)
3. 설정 조정:
   - 화자 선택 (기본 음성 또는 등록된 화자)
   - 언어 선택
   - 말하기 속도 조절
   - 피치 조절
   - 감정 선택
4. 실행:
   - **"실시간 재생"**: 즉시 스트리밍 재생
   - **"파일 생성"**: WAV 파일로 저장 및 다운로드

### 3. 파일 관리

1. **테스트** 페이지로 이동
2. 생성된 파일 목록 확인
3. 기능:
   - 검색: 텍스트로 파일 검색
   - 재생: 브라우저에서 바로 재생
   - 다운로드: WAV 파일 다운로드
   - 삭제: 불필요한 파일 삭제

## 🔧 API 사용법

### TTS 생성

```bash
curl -X POST "http://localhost:8000/api/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test.",
    "speaker_id": null,
    "language": "en-us",
    "speaking_rate": 1.0,
    "pitch_shift": 0.0,
    "emotion": "neutral",
    "save_to_db": true
  }'
```

### 화자 업로드

```bash
curl -X POST "http://localhost:8000/api/speakers/upload" \
  -F "name=John Doe" \
  -F "language=en-us" \
  -F "audio_file=@speaker_sample.wav"
```

### 오디오 다운로드

```bash
curl -O "http://localhost:8000/api/audio/download/1"
```

자세한 API 문서는 http://localhost:8000/docs 에서 확인하세요.

## ⚙️ 설정

### 환경 변수

`.env` 파일에서 다음 설정을 조정할 수 있습니다:

```bash
# 서버 설정
HOST=0.0.0.0
PORT=8000

# 디바이스 (cuda 또는 cpu)
DEVICE=cuda

# Zonos 모델
ZONOS_MODEL=Zyphra/Zonos-v0.1-transformer
# 또는 Zyphra/Zonos-v0.1-hybrid

# 데이터베이스
DATABASE_URL=sqlite+aiosqlite:///./zonos_tts.db
```

### 모델 선택

Zonos는 두 가지 모델 변형을 제공합니다:

- **transformer**: 더 빠른 추론 속도
- **hybrid**: 더 높은 품질 (느림)

모델은 첫 실행 시 자동으로 다운로드됩니다 (약 1-2GB).

## 🎯 성능 최적화

### GPU 메모리 최적화

```python
# backend/models/zonos_model.py에서 조정
# 배치 크기 감소
chunk_size = 50  # 기본값: 100

# 모델 정밀도 감소 (절반 정밀도)
model = Zonos.from_pretrained(
    model_name,
    torch_dtype=torch.float16  # float32 대신
)
```

### 스트리밍 최적화

```python
# 청크 크기 조절 (backend/services/stream_service.py)
chunk_size = 50  # 작을수록 지연시간 감소, 처리량 감소
```

## 🔒 보안 기능

### 파일 업로드 보안 검증

시스템은 다층 보안 검증을 통해 악성 파일 및 잘못된 파일을 차단합니다:

**1. 파일 크기 제한**
- 최대 업로드 크기: 50MB
- 빈 파일 차단

**2. 확장자 검증**
- 허용된 확장자만 허용: `.wav`, `.mp3`, `.flac`, `.ogg`, `.m4a`, `.aac`
- 확장자가 없는 파일 차단

**3. MIME 타입 검증 (실제 파일 내용)**
```python
# python-magic을 사용한 Magic bytes 검사
# 파일 확장자를 속여도 실제 내용으로 검증
mime_type = magic.from_buffer(content, mime=True)
```

**4. 오디오 길이 검증**
- 화자 샘플: 5초 이상 30초 이하만 허용
- 너무 짧거나 긴 파일 차단

**5. 안전한 파일명 생성**
```python
# UUID + 타임스탬프를 사용한 충돌 방지
# 특수문자 제거로 경로 탐색 공격 방지
filename = f"speaker_{uuid}_{timestamp}.wav"
```

**6. 텍스트 입력 검증**
- 최대 길이 제한: 5,000자
- 제어 문자 제거
- XSS 방지

### 보안 설정 (config.py)

```python
# 파일 크기 제한
MAX_AUDIO_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# 허용된 MIME 타입
ALLOWED_AUDIO_MIME_TYPES = {
    "audio/wav", "audio/mpeg", "audio/flac", ...
}

# 오디오 길이 제한
MIN_SPEAKER_DURATION = 5.0  # 초
MAX_SPEAKER_DURATION = 30.0
```

### 에러 처리

모든 검증 실패는 명확한 HTTP 상태 코드와 메시지를 반환:

- **400 Bad Request**: 검증 실패 (파일 형식, 길이 등)
- **413 Payload Too Large**: 파일이 너무 큼
- **500 Internal Server Error**: 서버 내부 오류

```bash
# 예시: 파일이 너무 큰 경우
{
  "detail": "파일이 너무 큽니다. (현재: 75.23MB, 최대: 50.00MB)"
}
```

## 🔄 동시성 제어

### GPU 리소스 관리

시스템은 세마포어 기반 동시성 제어를 통해 GPU 메모리 부족 및 과부하를 방지합니다.

**주요 기능:**

**1. 세마포어 기반 제한**
```python
# 동시에 실행 가능한 TTS 생성 작업 수 제한
MAX_CONCURRENT_TTS = 2  # 기본값

# 동시에 실행 가능한 임베딩 생성 작업 수 제한
MAX_CONCURRENT_EMBEDDING = 1  # 기본값
```

**2. 큐 크기 제한**
```python
# 대기 큐에 들어갈 수 있는 최대 요청 수
MAX_QUEUE_SIZE = 10

# 큐가 가득 차면 새 요청은 즉시 거부됨
# 에러 메시지: "서버가 현재 많은 요청을 처리 중입니다..."
```

**3. 요청 타임아웃**
```python
# 세마포어 획득 대기 시간 제한
REQUEST_TIMEOUT = 300.0  # 초 (5분)

# 타임아웃 발생 시 에러 반환
```

**4. 통계 추적**
- 활성 TTS/임베딩 요청 수
- 대기 중인 요청 수
- 완료/실패한 총 요청 수
- 평균 대기 시간

### 동시성 설정

**환경 변수로 조정:**

`.env` 파일에 추가:
```bash
# 동시성 제어 설정
MAX_CONCURRENT_TTS=2          # 동시 TTS 생성 수
MAX_CONCURRENT_EMBEDDING=1     # 동시 임베딩 생성 수
MAX_QUEUE_SIZE=10              # 최대 대기 큐 크기
REQUEST_TIMEOUT=300.0          # 요청 타임아웃 (초)
```

**GPU 메모리에 따른 권장 설정:**

| GPU VRAM | MAX_CONCURRENT_TTS | MAX_CONCURRENT_EMBEDDING |
|----------|-------------------|-------------------------|
| 6GB      | 1                 | 1                       |
| 8GB      | 2                 | 1                       |
| 12GB     | 3                 | 1                       |
| 16GB+    | 4                 | 2                       |

### 시스템 모니터링

**통계 조회 API:**

```bash
# 동시성 통계 조회
curl http://localhost:8000/api/system/stats

# 응답 예시:
{
  "success": true,
  "data": {
    "tts_active": 2,
    "tts_queued": 1,
    "tts_completed": 45,
    "tts_failed": 2,
    "embedding_active": 0,
    "embedding_queued": 0,
    "embedding_completed": 5,
    "embedding_failed": 0,
    "avg_tts_wait_time": 1.23,
    "avg_embedding_wait_time": 0.0,
    "max_concurrent_tts": 2,
    "max_concurrent_embedding": 1,
    "max_queue_size": 10
  }
}
```

**헬스 체크:**

```bash
# 시스템 상태 확인
curl http://localhost:8000/api/system/health

# 정상:
{
  "status": "healthy",
  "message": "시스템이 정상적으로 작동 중입니다."
}

# 과부하:
{
  "status": "unhealthy",
  "message": "TTS 요청 큐가 가득 찼습니다."
}
```

### 동시성 제어 흐름

```
요청 → 큐 크기 체크 → 세마포어 획득 (대기) → TTS/임베딩 실행 → 세마포어 해제
         ↓ 큐 가득참                  ↓ 타임아웃
       즉시 거부                    에러 반환
```

**실제 예시:**

```python
# TTS 생성 시
async with concurrency.acquire_tts(request_id):
    # 세마포어 획득 - 최대 2개까지만 동시 실행
    audio = model.generate_speech(text)
    # 작업 완료 후 자동으로 세마포어 해제
```

### 에러 처리

**큐 가득참:**
```json
{
  "detail": "서버가 현재 많은 요청을 처리 중입니다. 잠시 후 다시 시도해주세요."
}
```

**타임아웃:**
```json
{
  "detail": "요청 대기 시간이 초과되었습니다. (타임아웃: 300초)"
}
```

## 🛡️ 에러 처리 및 복원력

### 커스텀 예외 시스템

시스템은 세분화된 예외 클래스로 명확한 에러 처리를 제공합니다:

**예외 계층 구조:**

```python
ZonosTTSException (베이스)
├── ModelException
│   ├── ModelLoadError
│   ├── ModelNotLoadedError
│   └── ModelInferenceError
├── FileException
│   ├── FileValidationError
│   ├── FileSizeTooLargeError
│   └── InvalidFileTypeError
├── ConcurrencyException
│   ├── QueueFullError
│   └── RequestTimeoutError
└── APIException
    ├── InvalidInputError
    └── RateLimitExceededError
```

**에러 응답 형식:**

```json
{
  "error": "FileSizeTooLargeError",
  "message": "파일이 너무 큽니다. (현재: 75.23MB, 최대: 50.00MB)",
  "details": {
    "file_size": 78901234,
    "max_size": 52428800
  }
}
```

### 재시도 로직 (Exponential Backoff)

네트워크 오류 및 일시적 장애에 대한 자동 재시도:

```python
from utils.retry import retry_async, RetryConfig

@retry_async(RetryConfig(
    max_retries=3,
    initial_delay=1.0,
    exponential_base=2.0
))
async def unstable_operation():
    # 재시도 가능한 작업
    pass
```

**지원 기능:**
- 지수 백오프 (1초 → 2초 → 4초 ...)
- 랜덤 지터 (충돌 방지)
- 재시도 가능한 예외 지정
- 최대 지연 시간 제한

### Circuit Breaker 패턴

연속 실패 시 시스템 보호:

```python
from utils.retry import CircuitBreaker, CircuitState

circuit = CircuitBreaker(
    failure_threshold=5,      # 5번 실패 시 차단
    recovery_timeout=60.0     # 60초 후 복구 시도
)

result = circuit.call(risky_operation)
```

**상태 전환:**
- **CLOSED**: 정상 동작
- **OPEN**: 차단 (요청 즉시 거부)
- **HALF_OPEN**: 복구 시도 (2번 성공 시 CLOSED로 복귀)

## 🧪 테스팅

### 테스트 실행

**전체 테스트 실행:**

```bash
cd backend
pytest
```

**특정 카테고리만 실행:**

```bash
# 단위 테스트만
pytest tests/unit/

# 통합 테스트만
pytest tests/integration/

# 특정 파일
pytest tests/unit/test_file_validator.py
```

**커버리지 리포트:**

```bash
# 터미널 출력
pytest --cov

# HTML 리포트 생성
pytest --cov --cov-report=html
# 결과: htmlcov/index.html
```

### 테스트 구조

```
backend/tests/
├── conftest.py           # 공통 fixtures
├── unit/                 # 단위 테스트
│   ├── test_file_validator.py
│   ├── test_concurrency.py
│   └── test_retry.py
└── integration/          # 통합 테스트
    └── test_api_endpoints.py
```

### 주요 Fixtures

```python
@pytest.fixture
async def db_session():
    """테스트용 인메모리 데이터베이스"""

@pytest.fixture
def test_client():
    """FastAPI 테스트 클라이언트"""

@pytest.fixture
def mock_audio_file():
    """모의 오디오 파일"""
```

### 테스트 작성 예시

```python
@pytest.mark.asyncio
async def test_tts_generation(test_client, sample_text):
    response = test_client.post("/api/tts/generate", json={
        "text": sample_text,
        "language": "en-us"
    })

    assert response.status_code == 200
    assert "file_path" in response.json()
```

## 🐛 문제 해결

### 1. CUDA out of memory

**해결책:**
- GPU 메모리가 부족합니다. `DEVICE=cpu`로 변경하거나 더 큰 GPU 사용
- 텍스트를 짧게 분할하여 생성

### 2. eSpeak-NG 오류

**해결책:**
```bash
# eSpeak-NG 재설치
sudo apt remove espeak-ng
sudo apt install espeak-ng

# 설치 확인
espeak-ng --version
```

### 3. 모델 다운로드 실패

**해결책:**
```bash
# 수동으로 모델 다운로드
huggingface-cli download Zyphra/Zonos-v0.1-transformer

# 또는 Python에서
from huggingface_hub import snapshot_download
snapshot_download("Zyphra/Zonos-v0.1-transformer")
```

### 4. 프론트엔드 빌드 오류

**해결책:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

## 📚 기술 스택

### Backend
- **FastAPI**: 고성능 웹 프레임워크
- **SQLAlchemy**: ORM 및 데이터베이스
- **Zonos**: TTS 모델
- **PyTorch**: 딥러닝 프레임워크
- **torchaudio**: 오디오 처리

### Frontend
- **React**: UI 라이브러리
- **Vite**: 빌드 도구
- **TailwindCSS**: CSS 프레임워크
- **Axios**: HTTP 클라이언트
- **Web Audio API**: 오디오 재생

## 📄 라이선스

이 프로젝트는 Apache 2.0 라이선스 하에 배포됩니다.

Zonos 모델도 Apache 2.0 라이선스를 따릅니다.

## 🙏 감사의 말

- [Zyphra](https://github.com/Zyphra) - Zonos TTS 모델 개발
- [FastAPI](https://fastapi.tiangolo.com/) - 웹 프레임워크
- [React](https://react.dev/) - UI 라이브러리

## 🔗 참고 링크

- [Zonos GitHub](https://github.com/Zyphra/Zonos)
- [Zonos HuggingFace](https://huggingface.co/Zyphra/Zonos-v0.1-transformer)
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [React 문서](https://react.dev/)

## 📧 문의

문제가 있거나 질문이 있으시면 [Issues](https://github.com/yourusername/zonos-tts/issues)를 통해 문의해주세요.
