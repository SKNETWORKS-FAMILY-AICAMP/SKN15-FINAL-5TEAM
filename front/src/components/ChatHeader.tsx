import { Link } from 'react-router-dom';
import { useApp } from '@/contexts/AppContext';

interface ChatHeaderProps {
  onToggleSidebar: () => void;
  onOpenSettings?: () => void;
  title?: string;
  showBackButton?: boolean;
  titleClassName?: string;
  className?: string;
  variant?: 'light' | 'dark';
}

export default function ChatHeader({
  onToggleSidebar,
  onOpenSettings,
  title = "KIME CHAT",
  showBackButton = false,
  titleClassName = '',
  className = '',
  variant = 'light'
}: ChatHeaderProps) {
  const { isLoggedIn, openMyAccount, openLoginModal } = useApp();

  const variantStyles = {
    light: {
      header: "bg-theme-surface-strong border border-theme-card shadow-theme",
      hover: "hover:bg-theme-surface",
      icon: "text-theme-secondary",
      title: "text-theme-primary",
      login:
        "px-4 py-2 text-[#6c5ce7] border border-theme-card rounded-lg hover:bg-theme-surface transition-colors duration-200 text-sm font-medium",
      account:
        "px-4 py-2 bg-gradient-to-r from-[#2f1d83] via-[#4331c5] to-[#7a1fb9] text-white rounded-lg transition-transform duration-200 text-sm font-medium hover:scale-[1.03] hover:shadow-[0_12px_24px_rgba(67,49,197,0.35)]"
    },
    dark: {
      header:
        "bg-[#120b24]/90 border border-white/10 shadow-[0_24px_80px_rgba(6,3,18,0.6)] backdrop-blur-2xl",
      hover: "hover:bg-white/10",
      icon: "text-slate-200",
      title: "text-white",
      login:
        "px-4 py-2 text-violet-200 border border-white/20 rounded-lg hover:bg-white/10 transition-colors duration-200 text-sm font-medium",
      account:
        "px-4 py-2 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 text-white rounded-lg transition-transform duration-200 text-sm font-medium hover:scale-[1.03] hover:shadow-[0_16px_32px_rgba(99,102,241,0.45)]"
    }
  } as const;

  const styles = variantStyles[variant];
  const headerClass = [
    "px-4 py-3 flex items-center justify-between transition-colors duration-200",
    styles.header,
    className
  ]
    .filter(Boolean)
    .join(" ");
  const computedTitleClass = [`text-lg font-semibold`, styles.title, titleClassName]
    .filter(Boolean)
    .join(" ");
  const iconWrapperClass = ["p-2 rounded-lg transition-colors duration-200", styles.hover]
    .filter(Boolean)
    .join(" ");
  const iconClass = ["w-6 h-6", styles.icon].join(" ");

  return (
    <header className={headerClass}>
      <div className="flex items-center space-x-3">
        {/* 햄버거 메뉴 버튼 */}
        <button
          onClick={onToggleSidebar}
          className={iconWrapperClass}
          aria-label="대화 목록 열기"
        >
          <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        {/* 뒤로가기 버튼 (채팅 페이지에서만 표시) */}
        {showBackButton && (
          <Link
            to="/"
            className={iconWrapperClass}
            aria-label="홈으로"
          >
            <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
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
          <h1 className={computedTitleClass}>{title}</h1>
        </div>
      </div>

      {/* 우측 버튼들 */}
      <div className="flex items-center space-x-2">
        {/* 설정 버튼 (톱니바퀴 아이콘) */}
        {onOpenSettings && (
          <button
            onClick={onOpenSettings}
            className={iconWrapperClass}
            aria-label="설정 열기"
          >
            <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        )}

        {!isLoggedIn && (
          <button onClick={openLoginModal} className={styles.login}>
            Login
          </button>
        )}
        {isLoggedIn && (
          <button onClick={openMyAccount} className={styles.account}>
            My account
          </button>
        )}
      </div>
    </header>
  );
}
