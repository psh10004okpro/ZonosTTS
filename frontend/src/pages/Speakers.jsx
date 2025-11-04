import React, { useState, useEffect } from 'react';
import { listSpeakers, uploadSpeaker, deleteSpeaker } from '../services/api';
import { formatDate } from '../utils/audioUtils';

/**
 * 화자 관리 페이지
 */
function Speakers() {
  const [speakers, setSpeakers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showUploadModal, setShowUploadModal] = useState(false);

  useEffect(() => {
    loadSpeakers();
  }, []);

  const loadSpeakers = async () => {
    try {
      setLoading(true);
      setError(null);

      const data = await listSpeakers();
      setSpeakers(data);
    } catch (err) {
      console.error('화자 목록 로드 실패:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (speakerId) => {
    if (!confirm('정말 삭제하시겠습니까?')) {
      return;
    }

    try {
      await deleteSpeaker(speakerId);
      loadSpeakers(); // 목록 새로고침
    } catch (err) {
      console.error('화자 삭제 실패:', err);
      alert('화자 삭제에 실패했습니다: ' + err.message);
    }
  };

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">화자 관리</h1>
        <button
          onClick={() => setShowUploadModal(true)}
          className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
        >
          + 새 화자 추가
        </button>
      </div>

      {/* 에러 메시지 */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      {/* 로딩 */}
      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="text-gray-500">로딩 중...</div>
        </div>
      ) : speakers.length === 0 ? (
        <div className="bg-white shadow rounded-lg p-12 text-center">
          <p className="text-gray-500">등록된 화자가 없습니다</p>
          <button
            onClick={() => setShowUploadModal(true)}
            className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
          >
            첫 화자 추가하기
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {speakers.map((speaker) => (
            <SpeakerCard
              key={speaker.id}
              speaker={speaker}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* 업로드 모달 */}
      {showUploadModal && (
        <UploadModal
          onClose={() => setShowUploadModal(false)}
          onSuccess={() => {
            setShowUploadModal(false);
            loadSpeakers();
          }}
        />
      )}
    </div>
  );
}

/**
 * 화자 카드 컴포넌트
 */
function SpeakerCard({ speaker, onDelete }) {
  return (
    <div className="bg-white shadow rounded-lg p-6">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-lg font-semibold text-gray-900">{speaker.name}</h3>
        <button
          onClick={() => onDelete(speaker.id)}
          className="text-red-600 hover:text-red-900 text-sm"
        >
          삭제
        </button>
      </div>

      <div className="space-y-2 text-sm text-gray-600">
        <div>
          <span className="font-medium">언어:</span> {speaker.language}
        </div>
        <div>
          <span className="font-medium">사용 횟수:</span> {speaker.usage_count}회
        </div>
        <div>
          <span className="font-medium">등록일:</span> {formatDate(speaker.created_at)}
        </div>
      </div>

      {/* 샘플 오디오 재생 */}
      <div className="mt-4">
        <audio
          controls
          src={`/uploads/speakers/${speaker.sample_path.split('/').pop()}`}
          className="w-full h-10"
        />
      </div>
    </div>
  );
}

/**
 * 업로드 모달 컴포넌트
 */
function UploadModal({ onClose, onSuccess }) {
  const [name, setName] = useState('');
  const [language, setLanguage] = useState('en-us');
  const [audioFile, setAudioFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!name.trim()) {
      setError('화자 이름을 입력해주세요');
      return;
    }

    if (!audioFile) {
      setError('오디오 파일을 선택해주세요');
      return;
    }

    try {
      setUploading(true);
      setError(null);

      await uploadSpeaker(name, language, audioFile);
      onSuccess();
    } catch (err) {
      console.error('화자 업로드 실패:', err);
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium text-gray-900">새 화자 추가</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 화자 이름 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              화자 이름
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border border-gray-300 rounded-md p-2"
              placeholder="예: 김철수"
            />
          </div>

          {/* 언어 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              언어
            </label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full border border-gray-300 rounded-md p-2"
            >
              <option value="en-us">English (US)</option>
              <option value="ja">日本語</option>
              <option value="zh">中文</option>
              <option value="fr">Français</option>
              <option value="de">Deutsch</option>
            </select>
          </div>

          {/* 오디오 파일 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              오디오 샘플 (5-30초)
            </label>
            <input
              type="file"
              accept="audio/*"
              onChange={(e) => setAudioFile(e.target.files[0])}
              className="w-full border border-gray-300 rounded-md p-2"
            />
            <p className="text-xs text-gray-500 mt-1">
              WAV, MP3, FLAC 등 지원 (5초 이상 30초 이하)
            </p>
          </div>

          {/* 버튼 */}
          <div className="flex space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={uploading}
              className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {uploading ? '업로드 중...' : '추가'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default Speakers;
