import { Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import ChatPage from './pages/ChatPage'
import CharacterPage from './pages/CharacterPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/chat/:characterId" element={<ChatPage />} />
      <Route path="/character/:characterId" element={<CharacterPage />} />
    </Routes>
  )
}

export default App
