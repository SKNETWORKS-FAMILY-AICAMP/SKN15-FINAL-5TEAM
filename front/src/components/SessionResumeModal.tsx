import { useState } from 'react';
import { LastSessionInfo, RecentSession, apiClient } from '@/services/api';
import { normalizeScenarioId } from '@/utils/scenario';

interface SessionResumeModalProps {
  lastSession: LastSessionInfo;
  scenarioId: string;
  onResume: (sessionId: string) => void;
  onNewSession: () => void;
  onClose: () => void;
}

export default function SessionResumeModal({
  lastSession,
  scenarioId,
  onResume,
  onNewSession,
  onClose
}: SessionResumeModalProps) {
  const [allSessions, setAllSessions] = useState<RecentSession[]>([]);
  const [showAllSessions, setShowAllSessions] = useState(false);
  const [loading, setLoading] = useState(false);

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '';
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diff = now.getTime() - date.getTime();
      const hours = Math.floor(diff / (1000 * 60 * 60));
      const days = Math.floor(hours / 24);

      if (hours < 1) return '방금 전';
      if (hours < 24) return `${hours}시간 전`;
      if (days < 7) return `${days}일 전`;

      return date.toLocaleString('ko-KR', {
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  const loadAllSessions = async () => {
    setLoading(true);
    try {
      const normalizedId = normalizeScenarioId(scenarioId);
      const sessions = await apiClient.getUserSessions(normalizedId, 10);
      setAllSessions(sessions);
      setShowAllSessions(true);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  // 모든 세션 목록 보기
  if (showAllSessions) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] flex flex-col animate-fadeIn">
          {/* Header */}
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-800">세션 선택</h2>
                <p className="text-sm text-gray-600 mt-1">
                  이전 대화를 선택하거나 새로 시작하세요
                </p>
              </div>
              <button
                onClick={() => setShowAllSessions(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                ← 돌아가기
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {loading ? (
              <div className="flex justify-center items-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
                <span className="ml-3 text-gray-500">세션 불러오는 중...</span>
              </div>
            ) : (
              <div className="space-y-3">
                {/* New Session Option */}
                <button
                  onClick={onNewSession}
                  className="w-full p-4 border-2 border-dashed border-purple-300 rounded-xl hover:border-purple-500 hover:bg-purple-50 transition-all group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center group-hover:bg-purple-200 transition-colors flex-shrink-0">
                      <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                      </svg>
                    </div>
                    <div className="text-left">
                      <p className="font-semibold text-gray-800 group-hover:text-purple-600 transition-colors">
                        새로운 대화 시작
                      </p>
                      <p className="text-sm text-gray-500">처음부터 다시 시작합니다</p>
                    </div>
                  </div>
                </button>

                {/* Existing Sessions */}
                {allSessions.map((session) => (
                  <button
                    key={session.session_id}
                    onClick={() => onResume(session.session_id)}
                    className="w-full p-4 border border-gray-200 rounded-xl hover:border-purple-300 hover:bg-purple-50 transition-all text-left"
                  >
                    <div className="flex items-start gap-3">
                      <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="font-semibold text-gray-800 truncate flex-1">
                            {session.conversation_summary || `${session.turn_count || 0}개의 대화`}
                          </p>
                          <span className="text-xs text-gray-500 flex-shrink-0">
                            {formatDate(session.updated_at)}
                          </span>
                        </div>
                        {session.last_message_content && (
                          <p className="text-sm text-gray-600 truncate mb-2">
                            {session.last_message_speaker}: {session.last_message_content}
                          </p>
                        )}
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          <span className="px-2 py-1 bg-gray-100 rounded">
                            대화 {session.turn_count || 0}회
                          </span>
                          {session.current_stage && (
                            <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded">
                              {session.current_stage}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-6 border-t border-gray-200">
            <button
              onClick={onClose}
              className="w-full py-3 px-4 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors"
            >
              나중에 결정하기
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 기본 뷰: 최근 세션만 보여주기
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 p-6 animate-fadeIn">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="text-5xl mb-3">💬</div>
          <h2 className="text-2xl font-bold text-gray-800">저장된 대화가 있습니다</h2>
          <p className="text-sm text-gray-500 mt-2">
            이전에 하던 대화를 이어서 하시겠습니까?
          </p>
        </div>

        {/* Session Info */}
        <div className="mb-6 p-4 bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg border border-purple-100">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-600">진행 상황</span>
            <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs font-semibold rounded-full">
              {lastSession.turnCount}턴 진행
            </span>
          </div>

          {lastSession.currentStage && (
            <div className="mb-2">
              <span className="text-xs text-gray-500">현재 스테이지: </span>
              <span className="text-xs font-medium text-gray-700">{lastSession.currentStage}</span>
            </div>
          )}

          {lastSession.updatedAt && (
            <div className="text-xs text-gray-500 mb-3">
              마지막 대화: {formatDate(lastSession.updatedAt)}
            </div>
          )}

          {lastSession.conversationSummary && (
            <div className="mt-3 pt-3 border-t border-purple-200">
              <p className="text-xs text-gray-500 mb-1">대화 요약:</p>
              <p className="text-sm text-gray-700 line-clamp-3">
                {lastSession.conversationSummary}
              </p>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 mb-3">
          <button
            onClick={() => onResume(lastSession.sessionId)}
            className="flex-1 px-4 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all shadow-md hover:shadow-lg transform hover:scale-105"
          >
            🔄 이어서 하기
          </button>
          <button
            onClick={onNewSession}
            className="flex-1 px-4 py-3 bg-gray-100 text-gray-700 font-semibold rounded-lg hover:bg-gray-200 transition-all border border-gray-300"
          >
            🆕 새로 시작
          </button>
        </div>

        {/* View All Sessions Button */}
        <button
          onClick={loadAllSessions}
          disabled={loading}
          className="w-full text-sm text-purple-600 hover:text-purple-700 font-medium transition-colors py-2 disabled:opacity-50"
        >
          {loading ? '불러오는 중...' : '모든 세션 보기 →'}
        </button>

        {/* Close Button */}
        <button
          onClick={onClose}
          className="w-full text-sm text-gray-500 hover:text-gray-700 transition-colors py-2 mt-2"
        >
          나중에 결정하기
        </button>
      </div>

      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(-20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }
        .line-clamp-3 {
          display: -webkit-box;
          -webkit-line-clamp: 3;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      `}</style>
    </div>
  );
}
