"""
Zonos TTS API - FastAPI 메인 애플리케이션
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from models.database import db_instance
from routes import tts, speakers, audio


# ==================== 애플리케이션 생명주기 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행"""
    # 시작 시
    logger.info("🚀 Zonos TTS API 시작 중...")

    # 데이터베이스 초기화
    logger.info("데이터베이스 초기화 중...")
    await db_instance.create_tables()
    logger.info("✓ 데이터베이스 초기화 완료")

    # 업로드 디렉토리 생성
    os.makedirs("uploads/speakers", exist_ok=True)
    os.makedirs("uploads/generated", exist_ok=True)
    os.makedirs("uploads/embeddings", exist_ok=True)
    logger.info("✓ 업로드 디렉토리 생성 완료")

    # Zonos 모델 사전 로드 (선택사항 - 첫 요청 시 로드해도 됨)
    # from models.zonos_model import get_zonos_model
    # logger.info("Zonos 모델 로드 중...")
    # get_zonos_model()
    # logger.info("✓ Zonos 모델 로드 완료")

    logger.info("✓ Zonos TTS API 시작 완료!")

    yield

    # 종료 시
    logger.info("Zonos TTS API 종료 중...")
    await db_instance.close()
    logger.info("✓ Zonos TTS API 종료 완료")


# ==================== FastAPI 애플리케이션 ====================

app = FastAPI(
    title="Zonos TTS API",
    description="""
    # Zonos TTS API

    Zyphra의 오픈소스 TTS 모델 Zonos를 사용한 음성 합성 API

    ## 주요 기능
    - 🎤 **음성 생성**: 텍스트를 고품질 음성으로 변환
    - 🔄 **실시간 스트리밍**: Server-Sent Events를 통한 실시간 음성 스트리밍
    - 🎭 **음성 복제**: 5-30초 샘플로 화자 음성 복제
    - 🌍 **다국어 지원**: 영어, 일본어, 중국어, 프랑스어, 독일어
    - 🎚️ **세밀한 제어**: 말하기 속도, 피치, 감정 조절
    - 📁 **파일 관리**: 생성된 음성 파일 저장, 목록 조회, 다운로드

    ## 기술 스택
    - **TTS 모델**: Zonos-v0.1 (Zyphra)
    - **프레임워크**: FastAPI
    - **데이터베이스**: SQLite (SQLAlchemy ORM)
    - **오디오**: PyTorch, torchaudio

    ## 라이선스
    Apache 2.0
    """,
    version="1.0.0",
    lifespan=lifespan
)


# ==================== CORS 설정 ====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React 개발 서버
        "http://localhost:5173",  # Vite 개발 서버
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 라우터 등록 ====================

app.include_router(tts.router)
app.include_router(speakers.router)
app.include_router(audio.router)


# ==================== 정적 파일 서빙 ====================

# 업로드된 파일에 대한 정적 파일 서빙 (개발 환경용)
# 프로덕션에서는 nginx 등을 사용 권장
if os.path.exists("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ==================== 기본 엔드포인트 ====================

@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "Zonos TTS API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "zonos-tts-api"
    }


# ==================== 실행 ====================

if __name__ == "__main__":
    import uvicorn

    # 환경 변수에서 설정 읽기
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RELOAD", "false").lower() == "true"

    logger.info(f"서버 시작: {host}:{port}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
