"""
Zonos TTS 모델 래퍼 클래스
Zonos 모델을 초기화하고 음성 생성, 화자 임베딩 생성 등을 처리
"""

import torch
import torchaudio
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from loguru import logger
import os

# Zonos 라이브러리는 설치 후 임포트
# pip install git+https://github.com/Zyphra/Zonos.git
try:
    from zonos.model import Zonos
    from zonos.conditioning import make_cond_dict
    ZONOS_AVAILABLE = True
except ImportError:
    logger.warning("Zonos 라이브러리가 설치되지 않았습니다. 더미 모드로 실행됩니다.")
    ZONOS_AVAILABLE = False


class ZonosModelWrapper:
    """Zonos TTS 모델 래퍼 클래스"""

    def __init__(
        self,
        model_name: str = "Zyphra/Zonos-v0.1-transformer",
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        cache_dir: Optional[str] = None
    ):
        """
        Args:
            model_name: Hugging Face 모델 이름
            device: 실행 디바이스 (cuda/cpu)
            cache_dir: 모델 캐시 디렉토리
        """
        self.model_name = model_name
        self.device = device
        self.cache_dir = cache_dir
        self.model = None
        self.sampling_rate = 44100  # Zonos 기본 샘플링 레이트

        logger.info(f"ZonosModelWrapper 초기화: device={device}, model={model_name}")

    def load_model(self):
        """모델 로드 (지연 로딩)"""
        if self.model is not None:
            logger.info("모델이 이미 로드되어 있습니다.")
            return

        if not ZONOS_AVAILABLE:
            logger.warning("Zonos를 사용할 수 없습니다. 더미 모드로 실행합니다.")
            return

        try:
            logger.info(f"Zonos 모델 로드 중... ({self.model_name})")
            self.model = Zonos.from_pretrained(
                self.model_name,
                device=self.device,
                cache_dir=self.cache_dir
            )
            logger.info("✓ Zonos 모델 로드 완료")

            # 샘플링 레이트 업데이트
            if hasattr(self.model, 'autoencoder') and hasattr(self.model.autoencoder, 'sampling_rate'):
                self.sampling_rate = self.model.autoencoder.sampling_rate

        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")
            raise

    def create_speaker_embedding(
        self,
        audio_path: str,
        output_path: Optional[str] = None
    ) -> Optional[torch.Tensor]:
        """
        화자 임베딩 생성 (음성 복제용)

        Args:
            audio_path: 화자 샘플 오디오 파일 경로
            output_path: 임베딩 저장 경로 (.pt 파일)

        Returns:
            speaker embedding tensor
        """
        if not ZONOS_AVAILABLE or self.model is None:
            logger.warning("모델이 로드되지 않았습니다.")
            return None

        try:
            # 오디오 로드
            wav, sr = torchaudio.load(audio_path)

            # 스테레오 -> 모노 변환
            if wav.shape[0] > 1:
                wav = wav.mean(dim=0, keepdim=True)

            # 리샘플링 (필요시)
            if sr != self.sampling_rate:
                resampler = torchaudio.transforms.Resample(sr, self.sampling_rate)
                wav = resampler(wav)

            # 화자 임베딩 생성
            logger.info(f"화자 임베딩 생성 중: {audio_path}")
            speaker = self.model.make_speaker_embedding(wav, self.sampling_rate)

            # 임베딩 저장
            if output_path:
                torch.save(speaker, output_path)
                logger.info(f"✓ 화자 임베딩 저장: {output_path}")

            return speaker

        except Exception as e:
            logger.error(f"화자 임베딩 생성 실패: {e}")
            raise

    def load_speaker_embedding(self, embedding_path: str) -> Optional[torch.Tensor]:
        """저장된 화자 임베딩 로드"""
        try:
            speaker = torch.load(embedding_path, map_location=self.device)
            logger.info(f"화자 임베딩 로드: {embedding_path}")
            return speaker
        except Exception as e:
            logger.error(f"화자 임베딩 로드 실패: {e}")
            return None

    def generate_speech(
        self,
        text: str,
        speaker: Optional[torch.Tensor] = None,
        language: str = "en-us",
        speaking_rate: float = 1.0,
        pitch_shift: float = 0.0,
        emotion: str = "neutral",
        **kwargs
    ) -> Tuple[np.ndarray, int]:
        """
        음성 생성

        Args:
            text: 생성할 텍스트
            speaker: 화자 임베딩 (None이면 기본 음성)
            language: 언어 코드
            speaking_rate: 말하기 속도 (0.5 ~ 2.0)
            pitch_shift: 피치 조절 (반음 단위)
            emotion: 감정 (neutral, happy, sad, angry, fear)
            **kwargs: 추가 파라미터

        Returns:
            (audio_array, sample_rate) 튜플
        """
        if not ZONOS_AVAILABLE or self.model is None:
            logger.warning("모델이 없어 더미 오디오 생성")
            return self._generate_dummy_audio(len(text))

        try:
            # 조건 딕셔너리 생성
            cond_dict = make_cond_dict(
                text=text,
                speaker=speaker,
                language=language,
                speaking_rate=speaking_rate
            )

            # 감정 파라미터 추가 (Zonos가 지원하는 경우)
            emotion_params = self._get_emotion_params(emotion)
            if emotion_params:
                cond_dict.update(emotion_params)

            # 피치 조절 (후처리로 구현)
            if pitch_shift != 0.0:
                cond_dict['pitch_shift'] = pitch_shift

            # 컨디셔닝 준비
            conditioning = self.model.prepare_conditioning(cond_dict)

            # 음성 생성
            logger.info(f"음성 생성 중... (텍스트 길이: {len(text)}자)")
            with torch.no_grad():
                codes = self.model.generate(conditioning)
                wavs = self.model.autoencoder.decode(codes).cpu()

            audio = wavs[0].numpy()

            # 피치 조절 적용 (필요시)
            if pitch_shift != 0.0:
                audio = self._apply_pitch_shift(audio, pitch_shift)

            logger.info(f"✓ 음성 생성 완료 (길이: {len(audio)/self.sampling_rate:.2f}초)")
            return audio, self.sampling_rate

        except Exception as e:
            logger.error(f"음성 생성 실패: {e}")
            raise

    def generate_speech_streaming(
        self,
        text: str,
        speaker: Optional[torch.Tensor] = None,
        language: str = "en-us",
        speaking_rate: float = 1.0,
        chunk_size: int = 100,
        **kwargs
    ):
        """
        스트리밍 음성 생성 (제너레이터)

        Args:
            text: 생성할 텍스트
            speaker: 화자 임베딩
            language: 언어 코드
            speaking_rate: 말하기 속도
            chunk_size: 청크당 문자 수
            **kwargs: 추가 파라미터

        Yields:
            (audio_chunk, sample_rate) 튜플
        """
        # 텍스트를 문장 단위로 분할
        sentences = self._split_into_sentences(text, chunk_size)

        for i, sentence in enumerate(sentences):
            logger.info(f"청크 {i+1}/{len(sentences)} 생성 중: {sentence[:30]}...")

            try:
                audio, sr = self.generate_speech(
                    text=sentence,
                    speaker=speaker,
                    language=language,
                    speaking_rate=speaking_rate,
                    **kwargs
                )
                yield audio, sr

            except Exception as e:
                logger.error(f"청크 {i+1} 생성 실패: {e}")
                continue

    def _split_into_sentences(self, text: str, max_length: int = 100) -> list[str]:
        """텍스트를 문장 단위로 분할"""
        import re

        # 문장 종결 기호로 분할
        sentences = re.split(r'([.!?。！？]+)', text)

        # 종결 기호와 텍스트를 다시 합침
        result = []
        current = ""
        for i, part in enumerate(sentences):
            current += part
            if i % 2 == 1:  # 종결 기호
                result.append(current.strip())
                current = ""

        if current:
            result.append(current.strip())

        # 너무 긴 문장은 쉼표로 추가 분할
        final_result = []
        for sent in result:
            if len(sent) <= max_length:
                final_result.append(sent)
            else:
                # 쉼표로 분할
                parts = sent.split(',')
                for part in parts:
                    if part.strip():
                        final_result.append(part.strip())

        return [s for s in final_result if s]

    def _get_emotion_params(self, emotion: str) -> Dict[str, Any]:
        """감정 파라미터 생성 (Zonos 모델에 따라 조정 필요)"""
        emotion_map = {
            "neutral": {},
            "happy": {"emotion_intensity": 0.7, "emotion_type": "positive"},
            "sad": {"emotion_intensity": 0.7, "emotion_type": "negative"},
            "angry": {"emotion_intensity": 0.9, "emotion_type": "aggressive"},
            "fear": {"emotion_intensity": 0.8, "emotion_type": "anxious"}
        }
        return emotion_map.get(emotion, {})

    def _apply_pitch_shift(self, audio: np.ndarray, semitones: float) -> np.ndarray:
        """
        피치 시프트 적용 (간단한 리샘플링 방식)
        실제 구현시 librosa 또는 pyrubberband 사용 권장
        """
        # 간단한 구현 - 실제로는 librosa.effects.pitch_shift 사용
        ratio = 2 ** (semitones / 12.0)
        indices = np.arange(0, len(audio), ratio)
        indices = np.clip(indices, 0, len(audio) - 1).astype(int)
        return audio[indices]

    def _generate_dummy_audio(self, text_length: int) -> Tuple[np.ndarray, int]:
        """더미 오디오 생성 (테스트용)"""
        duration = min(text_length / 20, 10)  # 최대 10초
        samples = int(duration * self.sampling_rate)
        audio = np.sin(2 * np.pi * 440 * np.arange(samples) / self.sampling_rate) * 0.3
        return audio.astype(np.float32), self.sampling_rate

    def save_audio(
        self,
        audio: np.ndarray,
        sample_rate: int,
        output_path: str,
        format: str = "wav"
    ):
        """오디오를 파일로 저장"""
        try:
            # numpy array를 tensor로 변환
            audio_tensor = torch.from_numpy(audio).unsqueeze(0)

            # 저장
            torchaudio.save(
                output_path,
                audio_tensor,
                sample_rate,
                format=format
            )
            logger.info(f"✓ 오디오 저장: {output_path}")

        except Exception as e:
            logger.error(f"오디오 저장 실패: {e}")
            raise

    def get_audio_duration(self, audio_path: str) -> float:
        """오디오 파일의 재생 시간 반환 (초)"""
        try:
            info = torchaudio.info(audio_path)
            return info.num_frames / info.sample_rate
        except Exception as e:
            logger.error(f"오디오 정보 로드 실패: {e}")
            return 0.0


# 전역 모델 인스턴스 (싱글톤)
_model_instance: Optional[ZonosModelWrapper] = None


def get_zonos_model() -> ZonosModelWrapper:
    """전역 Zonos 모델 인스턴스 반환 (지연 로딩)"""
    global _model_instance

    if _model_instance is None:
        device = os.getenv("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
        model_name = os.getenv("ZONOS_MODEL", "Zyphra/Zonos-v0.1-transformer")

        _model_instance = ZonosModelWrapper(
            model_name=model_name,
            device=device
        )
        _model_instance.load_model()

    return _model_instance
