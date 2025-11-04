/**
 * 오디오 유틸리티 함수
 */

/**
 * base64 인코딩된 오디오 청크를 AudioBuffer로 디코딩
 */
export const decodeAudioChunk = async (audioData) => {
  const { audio, sample_rate, dtype, shape } = audioData;

  // base64 디코딩
  const binaryString = atob(audio);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);

  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }

  // dtype에 따라 TypedArray 생성
  let audioArray;
  if (dtype === 'float32') {
    audioArray = new Float32Array(bytes.buffer);
  } else if (dtype === 'float64') {
    audioArray = new Float64Array(bytes.buffer);
  } else {
    throw new Error(`지원하지 않는 dtype: ${dtype}`);
  }

  // Web Audio API를 사용하여 AudioBuffer 생성
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const audioBuffer = audioContext.createBuffer(1, audioArray.length, sample_rate);

  // 오디오 데이터 복사
  audioBuffer.getChannelData(0).set(audioArray);

  return audioBuffer;
};

/**
 * AudioBuffer 재생
 */
export const playAudioBuffer = (audioContext, audioBuffer) => {
  const source = audioContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioContext.destination);
  source.start();
  return source;
};

/**
 * 오디오 큐 관리 클래스
 */
export class AudioQueue {
  constructor() {
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    this.queue = [];
    this.isPlaying = false;
    this.currentSource = null;
  }

  /**
   * 오디오 청크 추가
   */
  async enqueue(audioData) {
    const audioBuffer = await decodeAudioChunk(audioData);
    this.queue.push(audioBuffer);

    // 재생 중이 아니면 재생 시작
    if (!this.isPlaying) {
      this.playNext();
    }
  }

  /**
   * 다음 오디오 재생
   */
  playNext() {
    if (this.queue.length === 0) {
      this.isPlaying = false;
      return;
    }

    this.isPlaying = true;
    const audioBuffer = this.queue.shift();

    this.currentSource = this.audioContext.createBufferSource();
    this.currentSource.buffer = audioBuffer;
    this.currentSource.connect(this.audioContext.destination);

    // 재생 완료 시 다음 오디오 재생
    this.currentSource.onended = () => {
      this.playNext();
    };

    this.currentSource.start();
  }

  /**
   * 재생 중지
   */
  stop() {
    if (this.currentSource) {
      this.currentSource.stop();
      this.currentSource = null;
    }
    this.queue = [];
    this.isPlaying = false;
  }

  /**
   * AudioContext 재개 (사용자 인터랙션 후 필요)
   */
  resume() {
    if (this.audioContext.state === 'suspended') {
      this.audioContext.resume();
    }
  }
}

/**
 * 재생 시간 포맷팅 (초 -> mm:ss)
 */
export const formatDuration = (seconds) => {
  if (!seconds || isNaN(seconds)) return '00:00';

  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);

  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

/**
 * 파일 크기 포맷팅 (바이트 -> KB/MB)
 */
export const formatFileSize = (bytes) => {
  if (!bytes) return '0 KB';

  if (bytes < 1024) {
    return `${bytes} B`;
  } else if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(2)} KB`;
  } else {
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }
};

/**
 * 날짜 포맷팅
 */
export const formatDate = (dateString) => {
  if (!dateString) return '-';

  const date = new Date(dateString);
  const now = new Date();
  const diff = now - date;

  // 1분 이내
  if (diff < 60000) {
    return '방금 전';
  }
  // 1시간 이내
  else if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}분 전`;
  }
  // 24시간 이내
  else if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}시간 전`;
  }
  // 그 외
  else {
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
};
