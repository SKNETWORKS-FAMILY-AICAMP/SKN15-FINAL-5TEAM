import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { isAuthenticated, getUserData, clearTokens } from '@/utils/authUtils';
import { apiClient } from '@/services/api';

export type Theme = 'light' | 'dark';
export type FontSize = 'sm' | 'md' | 'lg';
export type ChatWindowSize = 'compact' | 'cozy' | 'spacious';

interface AppContextType {
  isSidebarOpen: boolean;
  isSettingsModalOpen: boolean;
  isAdvancedSettingsOpen: boolean;
  isMyAccountModalOpen: boolean;
  isLoginModalOpen: boolean;
  isPaymentModalOpen: boolean;
  isPasswordResetModalOpen: boolean;
  isLoggedIn: boolean;
  isAuthLoading: boolean;
  userEmail: string;
  currentUser: string | null;
  currentUserId: string | null;
  currentBubbles: number;
  theme: Theme;
  fontSize: FontSize;
  chatWindowSize: ChatWindowSize;
  setTheme: (theme: Theme) => void;
  setFontSize: (size: FontSize) => void;
  setChatWindowSize: (size: ChatWindowSize) => void;
  updateBubbles: (count: number) => void;
  consumeBubbles: (amount: number) => boolean;
  openSidebar: () => void;
  closeSidebar: () => void;
  toggleSidebar: () => void;
  openSettings: () => void;
  closeSettings: () => void;
  openAdvancedSettings: () => void;
  closeAdvancedSettings: () => void;
  openMyAccount: () => void;
  closeMyAccount: () => void;
  openLoginModal: () => void;
  closeLoginModal: () => void;
  openPaymentModal: () => void;
  closePaymentModal: () => void;
  openPasswordResetModal: () => void;
  closePasswordResetModal: () => void;
  login: (email: string) => void;
  logout: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

export const AppProvider = ({ children }: { children: ReactNode }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
  const [isAdvancedSettingsOpen, setIsAdvancedSettingsOpen] = useState(false);
  const [isMyAccountModalOpen, setIsMyAccountModalOpen] = useState(false);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [isPasswordResetModalOpen, setIsPasswordResetModalOpen] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [userEmail, setUserEmail] = useState('');
  const [currentUser, setCurrentUser] = useState<string | null>(() => {
    const storedUser = getUserData();
    if (!storedUser) {
      return null;
    }
    return storedUser.display_name || storedUser.username || null;
  });
  const [currentUserId, setCurrentUserId] = useState<string | null>(() => {
    const storedUser = getUserData();
    return storedUser?.user_id || null;
  });
  const [currentBubbles, setCurrentBubbles] = useState(0);
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof window !== 'undefined') {
      const storedTheme = localStorage.getItem('theme') as Theme;
      if (storedTheme) {
        return storedTheme;
      }
      if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark';
      }
    }
    return 'light';
  });
  const [fontSize, setFontSize] = useState<FontSize>('md');
  const [chatWindowSize, setChatWindowSize] = useState<ChatWindowSize>('cozy');

  useEffect(() => {
    const root = window.document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  // 초기 로딩 시 토큰 유효성 검증 및 로그인 상태 확인
  useEffect(() => {
    const validateToken = async () => {
      if (isAuthenticated()) {
        try {
          // Validate token by calling /api/auth/me
          const userInfo = await apiClient.getCurrentUser();

          // Token is valid, set logged in state
          setIsLoggedIn(true);
          setUserEmail(userInfo.display_name || userInfo.username);
          setCurrentUser(userInfo.display_name || userInfo.username || null);
          setCurrentUserId(userInfo.user_id || null);

          // Load user credits (bubble count)
          try {
            const credits = await apiClient.getUserCredits();
            setCurrentBubbles(credits.bubble_count);
          } catch (error) {
            console.error('Failed to load credits:', error);
            setCurrentBubbles(0);
          }
        } catch (error) {
          // Token is invalid or expired, clear it
          console.error('Token validation failed:', error);
          clearTokens();
          setIsLoggedIn(false);
          setUserEmail('');
          setCurrentUser(null);
          setCurrentUserId(null);
        }
      } else {
        setIsLoggedIn(false);
        setUserEmail('');
        setCurrentUser(null);
        setCurrentUserId(null);
      }
      setIsAuthLoading(false);
    };

    validateToken();
  }, []);

  const openSidebar = () => setIsSidebarOpen(true);
  const closeSidebar = () => setIsSidebarOpen(false);
  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);
  const openSettings = () => setIsSettingsModalOpen(true);
  const closeSettings = () => setIsSettingsModalOpen(false);
  const openAdvancedSettings = () => setIsAdvancedSettingsOpen(true);
  const closeAdvancedSettings = () => setIsAdvancedSettingsOpen(false);
  const openMyAccount = () => setIsMyAccountModalOpen(true);
  const closeMyAccount = () => setIsMyAccountModalOpen(false);
  const openLoginModal = () => setIsLoginModalOpen(true);
  const closeLoginModal = () => setIsLoginModalOpen(false);
  const openPaymentModal = () => setIsPaymentModalOpen(true);
  const closePaymentModal = () => setIsPaymentModalOpen(false);
  const openPasswordResetModal = () => setIsPasswordResetModalOpen(true);
  const closePasswordResetModal = () => setIsPasswordResetModalOpen(false);
  const login = (email: string) => {
    setIsLoggedIn(true);
    setUserEmail(email);
    const storedUser = getUserData();
    if (storedUser) {
      setCurrentUser(storedUser.display_name || storedUser.username || null);
    } else {
      setCurrentUser(null);
    }
    setCurrentUserId(storedUser?.user_id || null);
  };
  const logout = () => {
    clearTokens(); // JWT 토큰 삭제
    setIsLoggedIn(false);
    setUserEmail('');
    setCurrentUser(null);
    setCurrentUserId(null);
  };
  const updateBubbles = (count: number) => {
    setCurrentBubbles(count);
  };
  const consumeBubbles = (amount: number) => {
    if (currentBubbles >= amount) {
      setCurrentBubbles(prev => prev - amount);
      return true;
    }
    return false;
  };

  return (
    <AppContext.Provider
      value={{
        isSidebarOpen,
        isSettingsModalOpen,
        isAdvancedSettingsOpen,
        isMyAccountModalOpen,
        isLoginModalOpen,
        isPaymentModalOpen,
        isPasswordResetModalOpen,
        isLoggedIn,
        isAuthLoading,
        userEmail,
        currentUser,
        currentUserId,
        currentBubbles,
        theme,
        fontSize,
        chatWindowSize,
        setTheme,
        setFontSize,
        setChatWindowSize,
        openSidebar,
        closeSidebar,
        toggleSidebar,
        openSettings,
        closeSettings,
        openAdvancedSettings,
        closeAdvancedSettings,
        openMyAccount,
        closeMyAccount,
        openLoginModal,
        closeLoginModal,
        openPaymentModal,
        closePaymentModal,
        openPasswordResetModal,
        closePasswordResetModal,
        login,
        logout,
        updateBubbles,
        consumeBubbles,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};
