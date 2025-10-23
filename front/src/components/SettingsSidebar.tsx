import { useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useApp } from '@/contexts/AppContext';

interface SettingsSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

// 최근 대화 목록 데이터 (백엔드 API 연결 후 사용)
const recentConversations: Array<{
  id: string;
  characterName: string;
  lastMessage: string;
  timestamp: string;
  profileImage: string;
  scenarioId: string;
}> = [];

export default function SettingsSidebar({ isOpen, onClose }: SettingsSidebarProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const pathname = location.pathname;
  const { openPaymentModal } = useApp();
  // ESC 키로 닫기
  useEffect(() => {
    const handleEscKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscKey);
    return () => document.removeEventListener('keydown', handleEscKey);
  }, [isOpen, onClose]);

  // 사이드바가 열려있을 때 body 스크롤 방지
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }

    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <>
      {/* 오버레이 */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40"
        onClick={onClose}
      />

      {/* 사이드바 */}
      <div className="fixed left-0 top-0 h-full w-80 bg-white shadow-2xl z-50 transform transition-transform duration-300 ease-in-out">
        {/* 헤더 */}
        <div className="bg-purple-600 text-white p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">메뉴</h2>
            <div className="flex items-center space-x-2">
              {/* 홈 버튼 - 홈 화면이 아닐 때만 표시 */}
              {pathname !== '/' && (
                <button
                  onClick={() => {
                    navigate('/');
                    onClose();
                  }}
                  className="text-white hover:text-gray-200 transition-colors p-2 rounded-lg hover:bg-purple-700"
                  aria-label="홈으로 이동"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                  </svg>
                </button>
              )}
              {/* X 버튼 */}
              <button
                onClick={onClose}
                className="text-white hover:text-gray-200 transition-colors p-2 rounded-lg hover:bg-purple-700"
                aria-label="메뉴 닫기"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* 메뉴 아이템들 */}
        <div className="p-6 space-y-4">
          {/* 결제하기 버튼 */}
          <button
            onClick={() => {
              openPaymentModal();
              onClose();
            }}
            className="w-full bg-gradient-to-r from-red-500 via-orange-500 to-yellow-500 hover:from-red-600 hover:via-orange-600 hover:to-yellow-600 text-white font-bold py-4 px-6 rounded-xl shadow-lg transform transition-all duration-300 hover:scale-105 hover:shadow-xl"
          >
            <div className="flex items-center justify-center space-x-3">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span className="text-lg">⚔️ 전집중 호흡</span>
            </div>
            <div className="text-sm opacity-90 mt-1">
              결제하기
            </div>
          </button>

          {/* 최근 대화 목록 */}
          {recentConversations.length > 0 ? (
            <div className="mt-6">
              <h3 className="text-sm font-medium text-gray-600 mb-3 px-2">최근 대화</h3>
              <div className="bg-gray-50 rounded-2xl p-4 max-h-96 overflow-y-auto">
                <div className="space-y-2">
                  {recentConversations.map((conversation) => (
                    <Link
                      key={conversation.id}
                      to={`/chat/${conversation.scenarioId}`}
                      onClick={onClose}
                      className="flex items-center p-3 rounded-xl bg-white hover:bg-gray-100 transition-colors border border-gray-200 hover:border-purple-300"
                    >
                      <div className="flex-shrink-0 w-10 h-10 mr-3">
                        <img
                          src={conversation.profileImage}
                          alt={conversation.characterName}
                          className="w-full h-full rounded-full object-cover border-2 border-purple-200"
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            target.src = '/images/tanjiro.png';
                          }}
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <h4 className="text-sm font-medium text-gray-900 truncate">
                            {conversation.characterName}
                          </h4>
                          <span className="text-xs text-gray-500 flex-shrink-0 ml-2">
                            {conversation.timestamp}
                          </span>
                        </div>
                        <p className="text-xs text-gray-600 truncate mt-1">
                          {conversation.lastMessage}
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-6">
              <div className="bg-gray-50 rounded-2xl p-6 text-center">
                <div className="text-4xl mb-3">💬</div>
                <p className="text-sm text-gray-600">아직 대화 기록이 없습니다</p>
                <p className="text-xs text-gray-500 mt-1">백엔드 API 연결 후 표시됩니다</p>
              </div>
            </div>
          )}

          {/* 간단한 메뉴 설명 */}
          <div className="text-center text-gray-600 mt-6">
            <div className="text-sm mb-4">
              {pathname === '/' ? '홈 화면입니다' : '사이드바 메뉴'}
            </div>
            {pathname !== '/' && (
              <p className="text-xs text-gray-500">
                상단의 홈 버튼을 클릭하여<br />
                메인 화면으로 이동할 수 있습니다
              </p>
            )}
          </div>
        </div>
      </div>
    </>
  );
}