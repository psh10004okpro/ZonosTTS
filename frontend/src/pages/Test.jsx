import React, { useState, useEffect } from 'react';
import { listAudioFiles, deleteAudioFile } from '../services/api';
import { formatDuration, formatFileSize, formatDate } from '../utils/audioUtils';

/**
 * 테스트 페이지
 * 생성된 오디오 파일 목록 및 관리
 */
function Test() {
  const [audioFiles, setAudioFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const pageSize = 20;

  useEffect(() => {
    loadAudioFiles();
  }, [page, search]);

  const loadAudioFiles = async () => {
    try {
      setLoading(true);
      setError(null);

      const data = await listAudioFiles(page, pageSize, search || null);
      setAudioFiles(data.items);
      setTotalPages(Math.ceil(data.total / pageSize));
    } catch (err) {
      console.error('파일 목록 로드 실패:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (audioId) => {
    if (!confirm('정말 삭제하시겠습니까?')) {
      return;
    }

    try {
      await deleteAudioFile(audioId);
      loadAudioFiles(); // 목록 새로고침
    } catch (err) {
      console.error('파일 삭제 실패:', err);
      alert('파일 삭제에 실패했습니다: ' + err.message);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    loadAudioFiles();
  };

  return (
    <div className="px-4 py-6 sm:px-0">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">오디오 파일 테스트</h1>

      {/* 검색 바 */}
      <div className="mb-6">
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="텍스트로 검색..."
            className="flex-1 border border-gray-300 rounded-md shadow-sm p-2 focus:ring-primary-500 focus:border-primary-500"
          />
          <button
            type="submit"
            className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
          >
            검색
          </button>
          {search && (
            <button
              type="button"
              onClick={() => {
                setSearch('');
                setPage(1);
              }}
              className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600"
            >
              초기화
            </button>
          )}
        </form>
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
      ) : audioFiles.length === 0 ? (
        <div className="bg-white shadow rounded-lg p-12 text-center">
          <p className="text-gray-500">
            {search ? '검색 결과가 없습니다' : '생성된 파일이 없습니다'}
          </p>
        </div>
      ) : (
        <>
          {/* 파일 목록 테이블 */}
          <div className="bg-white shadow rounded-lg overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    텍스트
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    정보
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    재생
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    작업
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {audioFiles.map((file) => (
                  <tr key={file.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900">
                        {file.text.substring(0, 100)}
                        {file.text.length > 100 && '...'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {formatDate(file.created_at)}
                      </div>
                      <div className="text-xs text-gray-500">
                        {formatDuration(file.duration)} • {formatFileSize(file.file_size)}
                      </div>
                      <div className="text-xs text-gray-500">
                        {file.language} • {file.emotion}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <audio
                        controls
                        src={`/api/audio/stream/${file.id}`}
                        className="h-10"
                      />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <a
                        href={`/api/audio/download/${file.id}`}
                        download
                        className="text-primary-600 hover:text-primary-900 mr-3"
                      >
                        다운로드
                      </a>
                      <button
                        onClick={() => handleDelete(file.id)}
                        className="text-red-600 hover:text-red-900"
                      >
                        삭제
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 페이지네이션 */}
          {totalPages > 1 && (
            <div className="mt-6 flex justify-center">
              <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed"
                >
                  이전
                </button>
                <span className="relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium text-gray-700">
                  {page} / {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed"
                >
                  다음
                </button>
              </nav>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default Test;
