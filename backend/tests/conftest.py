"""
pytest fixtures and configuration
"""

import pytest
import asyncio
from typing import AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# 테스트용 임포트
import sys
from pathlib import Path

# backend 디렉토리를 path에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 fixture"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """테스트용 데이터베이스 세션"""
    # 인메모리 SQLite 사용
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # 테이블 생성
    from models.database import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 세션 팩토리
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def test_client():
    """FastAPI 테스트 클라이언트"""
    from main import app
    return TestClient(app)


@pytest.fixture
def mock_audio_file():
    """모의 오디오 파일 데이터"""
    from io import BytesIO

    # WAV 헤더 (간단한 더미)
    wav_header = b'RIFF' + b'\x00' * 4 + b'WAVE'
    return BytesIO(wav_header + b'\x00' * 1000)


@pytest.fixture
def sample_text():
    """샘플 텍스트"""
    return "Hello, this is a test text for TTS generation."
