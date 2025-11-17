import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getHistory, Conversation } from '@/utils/storageUtils';

interface LeftSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function LeftSidebar({ isOpen, onClose }: LeftSidebarProps) {
  const [history, setHistory] = useState<Conversation[]>([]);

  const openMemoryLog = () => {
    window.dispatchEvent(new CustomEvent('open-memory-log'));
    onClose();
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
                  <li key={conv.sessionId}>
                    <Link
                      to={`/history/${conv.sessionId}`}
                      onClick={onClose}
                      className="block p-3 rounded-xl border border-gray-100 hover:border-purple-300 hover:bg-purple-50 dark:border-gray-700 dark:hover:bg-gray-800 transition-colors"
                    >
                      <p className="font-semibold text-sm text-gray-900 dark:text-gray-100 truncate">{conv.title}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{conv.lastMessage}</p>
                      <p className="text-[10px] text-right text-gray-400 dark:text-gray-500 mt-2">
                        {new Date(conv.timestamp).toLocaleString()}
                      </p>
                    </Link>
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
