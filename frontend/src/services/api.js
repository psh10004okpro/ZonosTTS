/**
 * API 서비스
 * 백엔드 API와 통신하는 함수들
 */

import axios from 'axios';

// Axios 인스턴스 생성
const api = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5분 (음성 생성에 시간이 걸릴 수 있음)
  headers: {
    'Content-Type': 'application/json'
  }
});

// ==================== TTS API ====================

/**
 * 음성 파일 생성
 */
export const generateAudio = async (data) => {
  const response = await api.post('/tts/generate', data);
  return response.data;
};

/**
 * 실시간 스트리밍 TTS (EventSource 사용)
 */
export const streamTTS = (data, onChunk, onComplete, onError) => {
  const url = `/api/tts/stream`;
  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    if (event.data === '[DONE]') {
      eventSource.close();
      if (onComplete) onComplete();
      return;
    }

    try {
      const audioData = JSON.parse(event.data);
      if (onChunk) onChunk(audioData);
    } catch (error) {
      console.error('스트리밍 데이터 파싱 실패:', error);
    }
  };

  eventSource.onerror = (error) => {
    console.error('스트리밍 에러:', error);
    eventSource.close();
    if (onError) onError(error);
  };

  // POST 요청을 위한 대체 방법 (fetch 사용)
  return streamTTSWithFetch(data, onChunk, onComplete, onError);
};

/**
 * Fetch API를 사용한 스트리밍 (POST 지원)
 */
export const streamTTSWithFetch = async (data, onChunk, onComplete, onError) => {
  try {
    const response = await fetch('/api/tts/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        if (onComplete) onComplete();
        break;
      }

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);

          if (data === '[DONE]') {
            if (onComplete) onComplete();
            return;
          }

          try {
            const audioData = JSON.parse(data);
            if (onChunk) onChunk(audioData);
          } catch (error) {
            console.error('데이터 파싱 실패:', error);
          }
        }
      }
    }
  } catch (error) {
    console.error('스트리밍 실패:', error);
    if (onError) onError(error);
  }
};

/**
 * 대시보드 통계 조회
 */
export const getStats = async () => {
  const response = await api.get('/tts/stats');
  return response.data;
};

// ==================== 화자 API ====================

/**
 * 화자 목록 조회
 */
export const listSpeakers = async () => {
  const response = await api.get('/speakers/list');
  return response.data;
};

/**
 * 화자 정보 조회
 */
export const getSpeaker = async (speakerId) => {
  const response = await api.get(`/speakers/${speakerId}`);
  return response.data;
};

/**
 * 화자 업로드
 */
export const uploadSpeaker = async (name, language, audioFile) => {
  const formData = new FormData();
  formData.append('name', name);
  formData.append('language', language);
  formData.append('audio_file', audioFile);

  const response = await api.post('/speakers/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });

  return response.data;
};

/**
 * 화자 삭제
 */
export const deleteSpeaker = async (speakerId) => {
  const response = await api.delete(`/speakers/${speakerId}`);
  return response.data;
};

// ==================== 오디오 파일 API ====================

/**
 * 오디오 파일 목록 조회
 */
export const listAudioFiles = async (page = 1, pageSize = 20, search = null) => {
  const params = { page, page_size: pageSize };
  if (search) params.search = search;

  const response = await api.get('/audio/list', { params });
  return response.data;
};

/**
 * 오디오 파일 정보 조회
 */
export const getAudioFile = async (audioId) => {
  const response = await api.get(`/audio/${audioId}`);
  return response.data;
};

/**
 * 오디오 파일 다운로드 URL
 */
export const getAudioDownloadUrl = (audioId) => {
  return `/api/audio/download/${audioId}`;
};

/**
 * 오디오 파일 스트리밍 URL
 */
export const getAudioStreamUrl = (audioId) => {
  return `/api/audio/stream/${audioId}`;
};

/**
 * 오디오 파일 삭제
 */
export const deleteAudioFile = async (audioId) => {
  const response = await api.delete(`/audio/${audioId}`);
  return response.data;
};

// ==================== 에러 핸들링 ====================

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API 에러:', error);

    if (error.response) {
      // 서버에서 응답이 왔지만 에러 상태
      throw new Error(error.response.data.detail || '서버 에러가 발생했습니다');
    } else if (error.request) {
      // 요청이 전송되었지만 응답이 없음
      throw new Error('서버에 연결할 수 없습니다');
    } else {
      // 요청 설정 중 에러 발생
      throw new Error('요청 중 에러가 발생했습니다');
    }
  }
);

export default api;
