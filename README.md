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
│   ├── models/              # 데이터베이스 모델 및 Zonos 래퍼
│   │   ├── database.py      # SQLAlchemy ORM 모델
│   │   └── zonos_model.py   # Zonos 모델 래퍼
│   ├── routes/              # API 라우터
│   │   ├── tts.py           # TTS API
│   │   ├── speakers.py      # 화자 관리 API
│   │   └── audio.py         # 파일 관리 API
│   ├── services/            # 비즈니스 로직
│   │   ├── tts_service.py   # TTS 서비스
│   │   ├── speaker_service.py  # 화자 서비스
│   │   └── stream_service.py   # 스트리밍 서비스
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
