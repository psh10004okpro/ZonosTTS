import React, { useState, useEffect, useRef } from 'react';
import { generateAudio, streamTTSWithFetch, listSpeakers } from '../services/api';
import { AudioQueue } from '../utils/audioUtils';

/**
 * 음성 생성 페이지
 */
function Generate() {
  const [text, setText] = useState('');
  const [speakers, setSpeakers] = useState([]);
  const [selectedSpeaker, setSelectedSpeaker] = useState(null);
  const [language, setLanguage] = useState('en-us');
  const [speakingRate, setSpeakingRate] = useState(1.0);
  const [pitchShift, setPitchShift] = useState(0.0);
  const [emotion, setEmotion] = useState('neutral');

  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const audioQueueRef = useRef(null);

  useEffect(() => {
    loadSpeakers();
    audioQueueRef.current = new AudioQueue();
  }, []);

  const loadSpeakers = async () => {
    try {
      const data = await listSpeakers();
      setSpeakers(data);
    } catch (err) {
      console.error('화자 목록 로드 실패:', err);
    }
  };

  // 파일 생성
  const handleGenerate = async () => {
    if (!text.trim()) {
      setError('텍스트를 입력해주세요');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setResult(null);

      const data = await generateAudio({
        text,
        speaker_id: selectedSpeaker,
        language,
        speaking_rate: speakingRate,
        pitch_shift: pitchShift,
        emotion,
        save_to_db: true
      });

      setResult(data);
    } catch (err) {
      console.error('음성 생성 실패:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 실시간 스트리밍
  const handleStream = async () => {
    if (!text.trim()) {
      setError('텍스트를 입력해주세요');
      return;
    }

    try {
      setStreaming(true);
      setError(null);
      setResult(null);

      // AudioContext 재개
      audioQueueRef.current.resume();

      await streamTTSWithFetch(
        {
          text,
          speaker_id: selectedSpeaker,
          language,
          speaking_rate: speakingRate,
          pitch_shift: pitchShift,
          emotion
        },
        // onChunk
        (audioData) => {
          audioQueueRef.current.enqueue(audioData);
        },
        // onComplete
        () => {
          console.log('스트리밍 완료');
          setStreaming(false);
        },
        // onError
        (err) => {
          console.error('스트리밍 에러:', err);
          setError('스트리밍 중 에러가 발생했습니다');
          setStreaming(false);
        }
      );
    } catch (err) {
      console.error('스트리밍 실패:', err);
      setError(err.message);
      setStreaming(false);
    }
  };

  // 스트리밍 중지
  const handleStopStream = () => {
    audioQueueRef.current?.stop();
    setStreaming(false);
  };

  return (
    <div className="px-4 py-6 sm:px-0">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">음성 생성</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 왼쪽: 입력 영역 */}
        <div className="lg:col-span-2 space-y-6">
          {/* 텍스트 입력 */}
          <div className="bg-white shadow rounded-lg p-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              생성할 텍스트
            </label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="텍스트를 입력하세요 (최대 5000자)"
              maxLength={5000}
              rows={10}
              className="w-full border border-gray-300 rounded-md shadow-sm p-3 focus:ring-primary-500 focus:border-primary-500"
            />
            <div className="mt-2 text-sm text-gray-500 text-right">
              {text.length} / 5000
            </div>
          </div>

          {/* 화자 선택 */}
          <div className="bg-white shadow rounded-lg p-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              화자 선택
            </label>
            <select
              value={selectedSpeaker || ''}
              onChange={(e) => setSelectedSpeaker(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full border border-gray-300 rounded-md shadow-sm p-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="">기본 음성</option>
              {speakers.map((speaker) => (
                <option key={speaker.id} value={speaker.id}>
                  {speaker.name}
                </option>
              ))}
            </select>
          </div>

          {/* 액션 버튼 */}
          <div className="flex space-x-4">
            <button
              onClick={handleStream}
              disabled={loading || streaming}
              className="flex-1 bg-green-600 text-white px-6 py-3 rounded-md font-medium hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {streaming ? '재생 중...' : '실시간 재생'}
            </button>
            {streaming && (
              <button
                onClick={handleStopStream}
                className="px-6 py-3 bg-red-600 text-white rounded-md font-medium hover:bg-red-700"
              >
                중지
              </button>
            )}
            <button
              onClick={handleGenerate}
              disabled={loading || streaming}
              className="flex-1 bg-primary-600 text-white px-6 py-3 rounded-md font-medium hover:bg-primary-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {loading ? '생성 중...' : '파일 생성'}
            </button>
          </div>

          {/* 에러 메시지 */}
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          {/* 결과 */}
          {result && (
            <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
              <p className="font-medium">✓ 음성 생성 완료!</p>
              <audio
                controls
                src={`/api/audio/stream/${result.id}`}
                className="mt-3 w-full"
              />
              <a
                href={`/api/audio/download/${result.id}`}
                download
                className="mt-3 inline-block text-green-700 underline"
              >
                다운로드
              </a>
            </div>
          )}
        </div>

        {/* 오른쪽: 설정 패널 */}
        <div className="space-y-6">
          {/* 언어 선택 */}
          <div className="bg-white shadow rounded-lg p-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              언어
            </label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full border border-gray-300 rounded-md shadow-sm p-2"
            >
              <option value="en-us">English (US)</option>
              <option value="ja">日本語</option>
              <option value="zh">中文</option>
              <option value="fr">Français</option>
              <option value="de">Deutsch</option>
            </select>
          </div>

          {/* 말하기 속도 */}
          <div className="bg-white shadow rounded-lg p-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              말하기 속도: {speakingRate.toFixed(1)}x
            </label>
            <input
              type="range"
              min="0.5"
              max="2.0"
              step="0.1"
              value={speakingRate}
              onChange={(e) => setSpeakingRate(parseFloat(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>느림 (0.5x)</span>
              <span>빠름 (2.0x)</span>
            </div>
          </div>

          {/* 피치 조절 */}
          <div className="bg-white shadow rounded-lg p-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              피치 조절: {pitchShift > 0 ? '+' : ''}{pitchShift.toFixed(1)}
            </label>
            <input
              type="range"
              min="-12"
              max="12"
              step="0.5"
              value={pitchShift}
              onChange={(e) => setPitchShift(parseFloat(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>낮음 (-12)</span>
              <span>높음 (+12)</span>
            </div>
          </div>

          {/* 감정 선택 */}
          <div className="bg-white shadow rounded-lg p-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              감정
            </label>
            <select
              value={emotion}
              onChange={(e) => setEmotion(e.target.value)}
              className="w-full border border-gray-300 rounded-md shadow-sm p-2"
            >
              <option value="neutral">중립 (Neutral)</option>
              <option value="happy">행복 (Happy)</option>
              <option value="sad">슬픔 (Sad)</option>
              <option value="angry">분노 (Angry)</option>
              <option value="fear">두려움 (Fear)</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Generate;
