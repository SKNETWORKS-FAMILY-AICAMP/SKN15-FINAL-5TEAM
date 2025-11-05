import { LastSessionInfo } from '@/services/api';

interface SessionResumeModalProps {
  lastSession: LastSessionInfo;
  onResume: (sessionId: string) => void;
  onNewSession: () => void;
  onClose: () => void;
}

export default function SessionResumeModal({
  lastSession,
  onResume,
  onNewSession,
  onClose
}: SessionResumeModalProps) {
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '';
    try {
      return new Date(dateStr).toLocaleString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

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

        {/* Close Button */}
        <button
          onClick={onClose}
          className="w-full text-sm text-gray-500 hover:text-gray-700 transition-colors py-2"
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
