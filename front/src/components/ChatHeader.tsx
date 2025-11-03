import { Link } from 'react-router-dom';
import { useApp } from '@/contexts/AppContext';

interface ChatHeaderProps {
  onToggleSidebar: () => void;
  onOpenSettings?: () => void;
  title?: string;
  showBackButton?: boolean;
}

export default function ChatHeader({ onToggleSidebar, onOpenSettings, title = "Kime Chat", showBackButton = false }: ChatHeaderProps) {
  const { isLoggedIn, openMyAccount, openLoginModal } = useApp();
  return (
    <header className="bg-white shadow-sm border-b border-gray-200 px-4 py-3 flex items-center justify-between">
      <div className="flex items-center space-x-3">
        {/* 햄버거 메뉴 버튼 */}
        <button
          onClick={onToggleSidebar}
          className="p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200"
          aria-label="대화 목록 열기"
        >
          <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        {/* 뒤로가기 버튼 (채팅 페이지에서만 표시) */}
        {showBackButton && (
          <Link
            to="/"
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200"
            aria-label="홈으로 돌아가기"
          >
            <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </Link>
        )}

        {/* 로고와 제목 */}
        <div className="flex items-center space-x-3">
          <img
            src="/images/귀멸의칼날로고.png"
            alt="귀멸의 칼날 로고"
            className="h-8 w-auto object-contain"
          />
          <h1 className="text-lg font-semibold text-gray-800">{title}</h1>
        </div>
      </div>

      {/* 우측 버튼들 */}
      <div className="flex items-center space-x-2">
        {/* 설정 버튼 (톱니바퀴 아이콘) */}
        {onOpenSettings && (
          <button
            onClick={onOpenSettings}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200"
            aria-label="설정 열기"
          >
            <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        )}

        {!isLoggedIn && (
          <button
            onClick={openLoginModal}
            className="px-4 py-2 text-purple-600 border border-purple-200 rounded-lg hover:bg-purple-50 transition-colors duration-200 text-sm font-medium"
          >
            Login
          </button>
        )}
        {isLoggedIn && (
          <button
            onClick={openMyAccount}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors duration-200 text-sm font-medium"
          >
            My account
          </button>
        )}
      </div>
    </header>
  );
}