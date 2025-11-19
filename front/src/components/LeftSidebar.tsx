import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getHistory, removeConversation, Conversation } from '@/utils/storageUtils';
import { apiClient } from '@/services/api';

interface LeftSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function LeftSidebar({ isOpen, onClose }: LeftSidebarProps) {
  const [history, setHistory] = useState<Conversation[]>([]);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);

  const openMemoryLog = () => {
    window.dispatchEvent(new CustomEvent('open-memory-log'));
    onClose();
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.preventDefault(); // Prevent Link navigation
    e.stopPropagation();

    if (!confirm('이 대화를 삭제하시겠습니까?\n삭제된 대화는 복구할 수 없습니다.')) {
      return;
    }

    setDeletingSessionId(sessionId);

    try {
      // Delete from backend
      await apiClient.deleteSession(sessionId);

      // Remove from localStorage
      removeConversation(sessionId);

      // Refresh history list
      setHistory(getHistory());

      console.log('[LeftSidebar] Session deleted successfully:', sessionId);
    } catch (error) {
      console.error('[LeftSidebar] Failed to delete session:', error);
      alert('세션 삭제에 실패했습니다. 다시 시도해주세요.');
    } finally {
      setDeletingSessionId(null);
    }
  };

  useEffect(() => {
    if (isOpen) {
      setHistory(getHistory());
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <>
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
        onClick={onClose}
        aria-label="대화 목록 닫기"
      />

      <div className="fixed top-0 left-0 h-full w-80 bg-white shadow-2xl z-50 flex flex-col transform transition-transform duration-300 ease-in-out dark:bg-gray-900 dark:border-r dark:border-gray-700">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-purple-600 text-white dark:bg-gray-800 dark:border-gray-700">
          <div>
            <p className="text-xs opacity-80">세션 히스토리</p>
            <h2 className="text-lg font-bold">대화 목록</h2>
          </div>
          <button
            onClick={onClose}
            className="text-white hover:text-gray-200 transition-colors rounded-lg p-1"
            aria-label="대화 목록 닫기"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
      </div>

      <div className="flex-1 overflow-y-auto bg-white dark:bg-gray-900">
        <div className="p-4 space-y-6">
          {/* 섹션 1: 대화 목록 */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">세션 히스토리</p>
                <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">대화 목록</h3>
              </div>
              <div className="px-2 py-1 text-[11px] rounded-full bg-purple-50 text-purple-700 border border-purple-100 dark:bg-purple-900/30 dark:text-purple-200 dark:border-purple-800">
                {history.length}개
              </div>
            </div>

            {history.length === 0 ? (
              <div className="p-4 text-center text-gray-500 dark:text-gray-400 space-y-1 border border-dashed border-gray-200 dark:border-gray-700 rounded-xl">
                <p className="text-sm font-semibold">대화 기록이 없습니다</p>
                <p className="text-xs">채팅을 시작하면 자동으로 저장돼요.</p>
              </div>
            ) : (
              <ul className="space-y-2">
                {history.map((conv) => (
                  <li key={conv.sessionId} className="relative group">
                    <div className="flex items-start gap-2">
                      <Link
                        to={`/history/${conv.sessionId}`}
                        onClick={onClose}
                        className="flex-1 block p-3 rounded-xl border border-gray-100 hover:border-purple-300 hover:bg-purple-50 dark:border-gray-700 dark:hover:bg-gray-800 transition-colors"
                      >
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold text-sm text-gray-900 dark:text-gray-100 truncate">{conv.title}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{conv.lastMessage}</p>
                          <p className="text-[10px] text-right text-gray-400 dark:text-gray-500 mt-2">
                            {new Date(conv.timestamp).toLocaleString()}
                          </p>
                        </div>
                      </Link>
                      <button
                        onClick={(e) => handleDeleteSession(conv.sessionId, e)}
                        disabled={deletingSessionId === conv.sessionId}
                        className="p-2 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors opacity-0 group-hover:opacity-100 disabled:opacity-50 self-start mt-3"
                        aria-label="세션 삭제"
                        title="대화 삭제"
                      >
                        {deletingSessionId === conv.sessionId ? (
                          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                        ) : (
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* 섹션 2: 기억 로그 */}
          <div className="p-4 border border-blue-100 dark:border-blue-900/50 rounded-xl bg-blue-50 dark:bg-blue-900/20 space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-blue-700/80 dark:text-blue-200/80 font-medium">기억 로그</p>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">AI 기억 업데이트 보기</h3>
              </div>
              <span className="text-xl" role="img" aria-label="memory">🧠</span>
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-300">
              챗 페이지 왼쪽의 기억 로그 패널을 바로 열 수 있습니다.
            </p>
            <button
              onClick={openMemoryLog}
              className="w-full py-2 px-3 rounded-lg bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 transition-colors"
            >
              기억 로그 열기
            </button>
          </div>
        </div>
      </div>

        <div className="p-4 border-t border-gray-200 bg-gray-50 dark:bg-gray-800 dark:border-gray-700 text-center text-xs text-gray-500 dark:text-gray-400">
          ⚔️ 귀살대와 함께하는 대화 — 자동 저장 중
        </div>
      </div>
    </>
  );
}
