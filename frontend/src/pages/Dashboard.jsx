import React, { useState, useEffect } from 'react';
import { getStats, listAudioFiles } from '../services/api';
import { formatDuration, formatFileSize, formatDate } from '../utils/audioUtils';

/**
 * 대시보드 페이지
 * 통계 및 최근 파일 표시
 */
function Dashboard() {
  const [stats, setStats] = useState(null);
  const [recentFiles, setRecentFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      // 통계 로드
      const statsData = await getStats();
      setStats(statsData);

      // 최근 파일 로드 (5개)
      const filesData = await listAudioFiles(1, 5);
      setRecentFiles(filesData.items);
    } catch (err) {
      console.error('데이터 로드 실패:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">로딩 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
        에러: {error}
      </div>
    );
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">대시보드</h1>

      {/* 통계 카드 */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <StatCard
          title="총 오디오 파일"
          value={stats?.total_audio_files || 0}
          unit="개"
          icon="📁"
        />
        <StatCard
          title="총 화자 수"
          value={stats?.total_speakers || 0}
          unit="명"
          icon="🎤"
        />
        <StatCard
          title="총 재생 시간"
          value={formatDuration(stats?.total_duration_seconds || 0)}
          icon="⏱️"
        />
        <StatCard
          title="총 저장 용량"
          value={stats?.total_storage_mb?.toFixed(2) || 0}
          unit="MB"
          icon="💾"
        />
      </div>

      {/* 최근 생성 파일 */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">최근 생성 파일</h2>

        {recentFiles.length === 0 ? (
          <p className="text-gray-500 text-center py-8">생성된 파일이 없습니다</p>
        ) : (
          <div className="space-y-4">
            {recentFiles.map((file) => (
              <div
                key={file.id}
                className="border-b border-gray-200 pb-4 last:border-b-0"
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">
                      {file.text.substring(0, 100)}
                      {file.text.length > 100 && '...'}
                    </p>
                    <div className="mt-1 flex items-center space-x-4 text-xs text-gray-500">
                      <span>{formatDate(file.created_at)}</span>
                      <span>•</span>
                      <span>{formatDuration(file.duration)}</span>
                      <span>•</span>
                      <span>{formatFileSize(file.file_size)}</span>
                    </div>
                  </div>
                  <audio
                    controls
                    src={`/api/audio/stream/${file.id}`}
                    className="ml-4 h-8"
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * 통계 카드 컴포넌트
 */
function StatCard({ title, value, unit = '', icon }) {
  return (
    <div className="bg-white overflow-hidden shadow rounded-lg">
      <div className="p-5">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <span className="text-3xl">{icon}</span>
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 truncate">{title}</dt>
              <dd className="flex items-baseline">
                <div className="text-2xl font-semibold text-gray-900">
                  {value}
                  {unit && <span className="ml-1 text-lg text-gray-500">{unit}</span>}
                </div>
              </dd>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
