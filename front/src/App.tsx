import { Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import ChatPage from './pages/ChatPage'
import CharacterPage from './pages/CharacterPage'
import PasswordResetConfirmPage from './pages/PasswordResetConfirmPage'
import PasswordResetModal from './components/PasswordResetModal'
import { useApp } from './contexts/AppContext'

function App() {
  const { isPasswordResetModalOpen, closePasswordResetModal } = useApp()

  return (
    <>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/chat/:characterId" element={<ChatPage />} />
        <Route path="/character/:characterId" element={<CharacterPage />} />
        <Route path="/reset-password" element={<PasswordResetConfirmPage />} />
      </Routes>

      {/* Global Password Reset Modal */}
      <PasswordResetModal
        isOpen={isPasswordResetModalOpen}
        onClose={closePasswordResetModal}
      />
    </>
  )
}

export default App
