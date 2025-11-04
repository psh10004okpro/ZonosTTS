"""
실시간 스트리밍 서비스
Server-Sent Events (SSE)를 사용한 실시간 오디오 스트리밍
"""

import asyncio
import base64
import io
from typing import Optional, AsyncGenerator
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from models.zonos_model import get_zonos_model
from services.speaker_service import SpeakerService
from loguru import logger


class StreamService:
    """실시간 스트리밍 서비스"""

    def __init__(self):
        self.speaker_service = SpeakerService()

    async def stream_tts(
        self,
        text: str,
        db: AsyncSession,
        speaker_id: Optional[int] = None,
        language: str = "en-us",
        speaking_rate: float = 1.0,
        pitch_shift: float = 0.0,
        emotion: str = "neutral",
        chunk_size: int = 100
    ) -> AsyncGenerator[bytes, None]:
        """
        실시간 TTS 스트리밍 (SSE 형식)

        Args:
            text: 생성할 텍스트
            db: 데이터베이스 세션
            speaker_id: 화자 ID
            language: 언어 코드
            speaking_rate: 말하기 속도
            pitch_shift: 피치 조절
            emotion: 감정
            chunk_size: 청크당 문자 수

        Yields:
            SSE 형식의 바이트 데이터
        """
        try:
            # Zonos 모델 가져오기
            model = get_zonos_model()

            # 화자 임베딩 로드
            speaker_embedding = None
            if speaker_id:
                speaker = await self.speaker_service.get_speaker(db, speaker_id)
                if speaker and speaker.embedding_path:
                    speaker_embedding = model.load_speaker_embedding(speaker.embedding_path)

            logger.info(f"스트리밍 시작: 텍스트={text[:50]}..., 화자={speaker_id}")

            # 스트리밍 생성
            async for audio_chunk, sample_rate in self._generate_streaming(
                model=model,
                text=text,
                speaker=speaker_embedding,
                language=language,
                speaking_rate=speaking_rate,
                pitch_shift=pitch_shift,
                emotion=emotion,
                chunk_size=chunk_size
            ):
                # 오디오를 base64로 인코딩
                encoded_audio = self._encode_audio_chunk(audio_chunk, sample_rate)

                # SSE 형식으로 전송
                event_data = f"data: {encoded_audio}\n\n"
                yield event_data.encode('utf-8')

                # 백프레셔 방지를 위한 작은 딜레이
                await asyncio.sleep(0.01)

            # 스트림 종료 신호
            yield b"data: [DONE]\n\n"
            logger.info("✓ 스트리밍 완료")

        except Exception as e:
            logger.error(f"스트리밍 실패: {e}")
            error_msg = f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            yield error_msg.encode('utf-8')

    async def _generate_streaming(
        self,
        model,
        text: str,
        speaker: Optional[object],
        language: str,
        speaking_rate: float,
        pitch_shift: float,
        emotion: str,
        chunk_size: int
    ) -> AsyncGenerator[tuple, None]:
        """
        스트리밍 방식으로 오디오 생성

        Yields:
            (audio_chunk, sample_rate) 튜플
        """
        # 동기 제너레이터를 비동기로 변환
        streaming_gen = model.generate_speech_streaming(
            text=text,
            speaker=speaker,
            language=language,
            speaking_rate=speaking_rate,
            pitch_shift=pitch_shift,
            emotion=emotion,
            chunk_size=chunk_size
        )

        for audio, sr in streaming_gen:
            yield audio, sr
            # 이벤트 루프에 제어권 양보
            await asyncio.sleep(0)

    def _encode_audio_chunk(self, audio: np.ndarray, sample_rate: int) -> str:
        """
        오디오 청크를 base64 인코딩된 JSON으로 변환

        Args:
            audio: 오디오 numpy 배열
            sample_rate: 샘플링 레이트

        Returns:
            base64 인코딩된 JSON 문자열
        """
        import json

        # numpy 배열을 bytes로 변환
        audio_bytes = audio.tobytes()

        # base64 인코딩
        encoded = base64.b64encode(audio_bytes).decode('utf-8')

        # JSON으로 패키징
        data = {
            "audio": encoded,
            "sample_rate": sample_rate,
            "dtype": str(audio.dtype),
            "shape": audio.shape
        }

        return json.dumps(data)

    @staticmethod
    def decode_audio_chunk(encoded_data: str) -> tuple:
        """
        base64 인코딩된 오디오 청크 디코딩 (클라이언트 측에서 사용)

        Args:
            encoded_data: base64 인코딩된 JSON 문자열

        Returns:
            (audio_array, sample_rate) 튜플
        """
        import json

        data = json.loads(encoded_data)

        # base64 디코딩
        audio_bytes = base64.b64decode(data["audio"])

        # numpy 배열로 변환
        audio = np.frombuffer(audio_bytes, dtype=np.dtype(data["dtype"]))
        audio = audio.reshape(data["shape"])

        return audio, data["sample_rate"]
