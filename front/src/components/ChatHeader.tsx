import { Link } from 'react-router-dom';
import { useApp } from '@/contexts/AppContext';

const CDN_URL = import.meta.env.VITE_CDN_URL || '/images';

interface ChatHeaderProps {
  onToggleSidebar: () => void;
  onOpenSettings?: () => void;
  title?: string;
  showBackButton?: boolean;
  invitedCharacters?: string[];
  onBackClick?: () => void; // Custom back button handler
  variant?: string; // For different header styles
  titleClassName?: string; // Custom title styling
  className?: string; // Custom container styling
}

// 캐릭터 프로필 이미지 매핑
const getCharacterProfile = (charId: string): string => {
  const profileMap: Record<string, string> = {
    tanjiro: `${CDN_URL}/프로필_탄지로.png`,
    nezuko: `${CDN_URL}/프로필_네즈코.png`,
    zenitsu: `${CDN_URL}/프로필_젠이츠.png`,
    inosuke: `${CDN_URL}/프로필_이노스케.png`,
    rengoku: `${CDN_URL}/프로필_렌고쿠.png`,
    shinobu: `${CDN_URL}/프로필_시노부.png`,
  };
  return profileMap[charId] || `${CDN_URL}/프로필_탄지로.png`;
};

// 캐릭터 이름 매핑
const getCharacterName = (charId: string): string => {
  const nameMap: Record<string, string> = {
    tanjiro: '탄지로',
    nezuko: '네즈코',
    zenitsu: '젠이츠',
    inosuke: '이노스케',
    rengoku: '렌고쿠',
    shinobu: '시노부',
  };
  return nameMap[charId] || charId;
};

export default function ChatHeader({
  onToggleSidebar,
  onOpenSettings,
  title = "Kime Chat",
  showBackButton = false,
  invitedCharacters = [],
  onBackClick,
  variant,
  titleClassName
}: ChatHeaderProps) {
  const { isLoggedIn, openMyAccount, openLoginModal } = useApp();
  return (
    <header className="bg-white shadow-sm border-b border-gray-200 px-4 py-3 flex items-center justify-between">
      <div className="flex items-center space-x-3">
        {/* 햄버거 메뉴 버튼 */}
        <button
          data-tour-target="chat-menu-button"
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
          onBackClick ? (
            <button
              onClick={onBackClick}
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200"
              aria-label="홈으로 돌아가기"
            >
              <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
          ) : (
            <Link
              to="/"
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200"
              aria-label="홈으로 돌아가기"
            >
              <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </Link>
          )
        )}

        {/* 로고와 제목 */}
        <div className="flex items-center space-x-3">
          <Link to="/" className="hover:opacity-80 transition-opacity duration-200" aria-label="홈으로 이동">
            <img
              src="/images/귀멸의칼날로고.png"
              alt="귀멸의 칼날 로고"
              className="h-8 w-auto object-contain cursor-pointer"
            />
          </Link>
          <h1 className={titleClassName || "text-lg font-semibold text-gray-800"}>{title}</h1>
        </div>
      </div>

      {/* 우측 버튼들 */}
      <div className="flex items-center space-x-3">
        {/* 참여 중인 캐릭터들 (설정 톱니바퀴 왼쪽) */}
        {invitedCharacters.length > 0 && (
          <div className="flex items-center space-x-1">
            {invitedCharacters.map((charId, index) => (
              <div key={charId} className="relative">
                <img
                  src={getCharacterProfile(charId)}
                  alt={getCharacterName(charId)}
                  className="w-8 h-8 rounded-full border-2 border-white shadow-sm"
                  style={{ marginLeft: index > 0 ? '-6px' : '0' }}
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = `${CDN_URL}/프로필_탄지로.png`;
                  }}
                  title={getCharacterName(charId)}
                />
              </div>
            ))}
            {invitedCharacters.length > 1 && (
              <span className="text-xs text-gray-500 ml-2">
                {invitedCharacters.length}명
              </span>
            )}
          </div>
        )}

        {/* 설정 버튼 (톱니바퀴 아이콘) */}
        {onOpenSettings && (
          <button
            data-tour-target="chat-settings-button"
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
