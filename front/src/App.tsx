import { Routes, Route } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import { useApp } from './contexts/AppContext'
import ErrorBoundary from './components/ErrorBoundary'

// Lazy load pages for code splitting (P2 optimization)
const HomePage = lazy(() => import('./pages/HomePage'))
const ChatPage = lazy(() => import('./pages/ChatPage'))
const CharacterPage = lazy(() => import('./pages/CharacterPage'))
const MyGalleryPage = lazy(() => import('./pages/MyGalleryPage'))
const PasswordResetConfirmPage = lazy(() => import('./pages/PasswordResetConfirmPage'))
const PasswordResetModal = lazy(() => import('./components/PasswordResetModal'))
const SettingsModal = lazy(() => import('./components/SettingsModal'))
const LeftSidebar = lazy(() => import('./components/LeftSidebar'))
const MyAccountModal = lazy(() => import('./components/MyAccountModal'))

// Loading fallback component
const LoadingFallback = () => (
  <div style={{
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100vh',
    fontSize: '1.2rem',
    color: '#666'
  }}>
    Loading...
  </div>
)

function App() {
  const {
    isPasswordResetModalOpen,
    closePasswordResetModal,
    isSettingsModalOpen,
    closeSettings,
    isSidebarOpen,
    toggleSidebar
  } = useApp()

  return (
    <ErrorBoundary>
      <Suspense fallback={<LoadingFallback />}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/chat/:characterId" element={<ChatPage />} />
          <Route path="/character/:characterId" element={<CharacterPage />} />
          <Route path="/gallery" element={<MyGalleryPage />} />
          <Route path="/reset-password" element={<PasswordResetConfirmPage />} />
        </Routes>

        {/* Global Modals and Sidebar */}
        <PasswordResetModal
          isOpen={isPasswordResetModalOpen}
          onClose={closePasswordResetModal}
        />
        <SettingsModal
          isOpen={isSettingsModalOpen}
          onClose={closeSettings}
        />
        <LeftSidebar
          isOpen={isSidebarOpen}
          onToggle={toggleSidebar}
        />
        <MyAccountModal />
      </Suspense>
    </ErrorBoundary>
  )
}

export default App
