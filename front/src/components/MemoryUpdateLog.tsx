import { useEffect, useState } from 'react';
import { MemoryEvent } from '@/services/api';

interface MemoryUpdateLogProps {
  events: Array<MemoryEvent & { id: string; timestamp: number }>;
}

export default function MemoryUpdateLog({ events }: MemoryUpdateLogProps) {
  const [isHovered, setIsHovered] = useState(false);

  // 전역 이벤트로도 열 수 있게 지원 (햄버거 메뉴에서 호출)
  useEffect(() => {
    const handleOpen = () => setIsHovered(true);
    window.addEventListener('open-memory-log', handleOpen);
    return () => window.removeEventListener('open-memory-log', handleOpen);
  }, []);

  // 자동 닫힘 타이머 (수동 열림 시 몇 초 후 닫힘)
  useEffect(() => {
    if (!isHovered) return;
    const timer = setTimeout(() => setIsHovered(false), 4500);
    return () => clearTimeout(timer);
  }, [isHovered]);

  const getEventIcon = (eventType: string) => {
    if (eventType === 'saved') {
      return '💾';
    }
    return '🧠';
  };

  const getMemoryTypeLabel = (memoryType: string) => {
    const labels: Record<string, string> = {
      fact: '사실',
      event: '사건',
      relationship: '관계',
      preference: '선호도'
    };
    return labels[memoryType] || memoryType;
  };

  const formatTimestamp = (timestamp: number) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (seconds < 60) return `${seconds}초 전`;
    if (minutes < 60) return `${minutes}분 전`;
    if (hours < 24) return `${hours}시간 전`;
    return date.toLocaleString('ko-KR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getImportanceColor = (importance: number) => {
    if (importance >= 0.8) return 'text-red-600 bg-red-100';
    if (importance >= 0.6) return 'text-orange-600 bg-orange-100';
    if (importance >= 0.4) return 'text-yellow-600 bg-yellow-100';
    return 'text-gray-600 bg-gray-100';
  };

  if (!isHovered) {
    return <div className="fixed left-0 top-1/2 -translate-y-1/2 z-40 pointer-events-none" />;
  }

  return (
    <div className="fixed left-0 top-1/2 -translate-y-1/2 z-40 flex items-center pointer-events-auto">
      {/* Sliding panel ONLY (기존 왼쪽 탭 제거) */}
      <div
        className="
          bg-white/95 backdrop-blur-sm shadow-2xl rounded-r-2xl
          overflow-hidden transition-all duration-300 ease-in-out
          w-96 opacity-100
        "
      >
        <div className="p-6 max-h-[80vh] overflow-y-auto">
          {/* Header */}
          <div className="mb-4 pb-3 border-b border-gray-200 flex items-start justify-between gap-4">
            <div>
              <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                🧠 기억 업데이트 로그
              </h3>
              <p className="text-xs text-gray-500 mt-1">
                AI 캐릭터의 기억 저장 및 회상 기록
              </p>
            </div>
            <button
              onClick={() => setIsHovered(false)}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              aria-label="기억 로그 닫기"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Events list */}
          {events.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <svg className="w-12 h-12 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
              </svg>
              <p className="text-sm">아직 기억 이벤트가 없습니다</p>
            </div>
          ) : (
            <div className="space-y-3">
              {events.slice().reverse().map((event) => (
                <div
                  key={event.id}
                  className="p-3 bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg border border-purple-200 hover:shadow-md transition-shadow"
                >
                  {/* Event header */}
                  <div className="flex items-start gap-2 mb-2">
                    <div className="text-2xl flex-shrink-0">
                      {getEventIcon(event.event_type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-gray-800 text-sm truncate">
                          {event.character_name}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          event.event_type === 'saved'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-blue-100 text-blue-700'
                        }`}>
                          {event.event_type === 'saved' ? '저장' : '회상'}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500">
                        {formatTimestamp(event.timestamp)}
                      </div>
                    </div>
                  </div>

                  {/* Memory content */}
                  <div className="ml-9 space-y-1">
                    <div className="flex items-center gap-2 text-xs">
                      <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded">
                        {getMemoryTypeLabel(event.memory_type)}
                      </span>
                      <span className={`px-2 py-0.5 rounded font-medium ${getImportanceColor(event.importance)}`}>
                        중요도 {(event.importance * 100).toFixed(0)}%
                      </span>
                      {event.count && event.count > 1 && (
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
                          {event.count}개
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-700 line-clamp-2">
                      {event.memory_content}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <style>{`
        .line-clamp-2 {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      `}</style>
    </div>
  );
}
