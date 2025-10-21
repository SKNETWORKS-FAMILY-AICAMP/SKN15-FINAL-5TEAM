import { createContext, useContext, useState, ReactNode } from 'react';

interface AppContextType {
  isSidebarOpen: boolean;
  isSettingsModalOpen: boolean;
  isAdvancedSettingsOpen: boolean;
  isMyAccountModalOpen: boolean;
  isLoginModalOpen: boolean;
  isPaymentModalOpen: boolean;
  isLoggedIn: boolean;
  userEmail: string;
  currentBubbles: number;
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
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userEmail, setUserEmail] = useState('');
  const [currentBubbles, setCurrentBubbles] = useState(847);

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
  const login = (email: string) => {
    setIsLoggedIn(true);
    setUserEmail(email);
  };
  const logout = () => {
    setIsLoggedIn(false);
    setUserEmail('');
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
        isLoggedIn,
        userEmail,
        currentBubbles,
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