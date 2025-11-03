import { useParams, Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import ChatInterface from '@/components/ChatInterface';
import ChatHeader from '@/components/ChatHeader';
import LoginModal from '@/components/LoginModal';
import SessionResumeModal from '@/components/SessionResumeModal';
import { useApp } from '@/contexts/AppContext';
import { apiClient, LastSessionInfo } from '@/services/api';
import scenariosData from '@/data/scenarios.json';

interface ScenarioData {
  id: string;
  title: string;
  image: string;
  description: string;
  detailDescription: string;
  implemented: boolean;
}

const SCENARIO_ID_MAP: Record<string, string> = {
  train: 'cutscene5_llm_driven',
  ending: 'cutscene5_llm_driven',
  cutscene5_llm_driven: 'cutscene5_llm_driven',
};

export default function ChatPage() {
  const { characterId } = useParams<{ characterId: string }>();
  const { toggleSidebar, openSettings, isLoggedIn, openLoginModal } = useApp();

  // Session restoration state
  const [lastSession, setLastSession] = useState<LastSessionInfo | null>(null);
  const [showResumeModal, setShowResumeModal] = useState(false);
  const [resumeSessionId, setResumeSessionId] = useState<string | undefined>(undefined);
  const [sessionCheckDone, setSessionCheckDone] = useState(false);

  // Authentication guard: show login modal if not authenticated
  useEffect(() => {
    if (!isLoggedIn) {
      openLoginModal();
      setSessionCheckDone(false);
    }
  }, [isLoggedIn, openLoginModal]);

  // Check for last session after login
  useEffect(() => {
    if (isLoggedIn && characterId && !sessionCheckDone) {
      checkLastSession();
    }
  }, [isLoggedIn, characterId, sessionCheckDone]);

  const checkLastSession = async () => {
    try {
      const backendScenarioId = SCENARIO_ID_MAP[characterId || ''] || characterId;
      const session = await apiClient.getUserLastSession(backendScenarioId);

      if (session) {
        setLastSession(session);
        setShowResumeModal(true);
      }
      setSessionCheckDone(true);
    } catch (error) {
      console.error('Failed to check last session:', error);
      setSessionCheckDone(true);
    }
  };

  const handleResume = (sessionId: string) => {
    console.log('Resuming session:', sessionId);
    setResumeSessionId(sessionId);
    setShowResumeModal(false);
  };

  const handleNewSession = () => {
    console.log('Starting new session');
    setResumeSessionId(undefined);
    setShowResumeModal(false);
    setSessionCheckDone(true);
  };

  // Load scenario data dynamically
  const scenarios = scenariosData as Record<string, ScenarioData>;
  const scenario = characterId ? scenarios[characterId] : null;

  // Fallback for unknown scenarios
  if (!scenario) {
    return (
      <div className="min-h-screen bg-gray-50">
        <ChatHeader
          onToggleSidebar={toggleSidebar}
          onOpenSettings={openSettings}
          title="알 수 없는 시나리오"
          showBackButton={true}
        />
        <main className="relative" style={{ height: 'calc(100vh - 64px)' }}>
          <div className="relative z-10 flex items-center justify-center h-full">
            <div className="text-center bg-white bg-opacity-90 p-8 rounded-xl shadow-xl max-w-md">
              <div className="text-6xl mb-6">❓</div>
              <h1 className="text-3xl font-bold mb-4 text-gray-800">존재하지 않는 시나리오</h1>
              <p className="text-gray-600 mb-6">요청하신 시나리오를 찾을 수 없습니다.</p>
              <Link
                to="/"
                className="inline-block px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                홈으로 돌아가기
              </Link>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // Check if implemented
  if (!scenario.implemented) {
    return (
      <div className="min-h-screen bg-gray-50">
        <ChatHeader
          onToggleSidebar={toggleSidebar}
          onOpenSettings={openSettings}
          title={scenario.title}
          showBackButton={true}
        />
        <main className="relative" style={{ height: 'calc(100vh - 64px)' }}>
          <div className="relative z-10 flex items-center justify-center h-full">
            <div className="text-center bg-white bg-opacity-90 p-8 rounded-xl shadow-xl max-w-md">
              <div className="text-6xl mb-6">🚧</div>
              <h1 className="text-3xl font-bold mb-4 text-gray-800">준비 중입니다</h1>
              <p className="text-gray-600 mb-2">
                <span className="font-semibold text-purple-600">{scenario.title}</span>
                {' '}시나리오는 현재 개발 중입니다.
              </p>
              <p className="text-sm text-gray-500 mb-6">백엔드 API 연결 후 이용 가능합니다!</p>
              <Link
                to="/"
                className="inline-block px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                홈으로 돌아가기
              </Link>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // Authentication lock screen for unauthenticated users
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-gray-50">
        <ChatHeader
          onToggleSidebar={toggleSidebar}
          onOpenSettings={openSettings}
          title={scenario?.title || '채팅'}
          showBackButton={true}
        />
        <main className="relative" style={{ height: 'calc(100vh - 64px)' }}>
          <div className="relative z-10 flex items-center justify-center h-full">
            <div className="text-center bg-white bg-opacity-90 p-8 rounded-xl shadow-xl max-w-md">
              <div className="text-6xl mb-6">🔐</div>
              <h1 className="text-3xl font-bold mb-4 text-gray-800">로그인이 필요합니다</h1>
              <p className="text-gray-600 mb-6">
                채팅을 시작하려면 로그인해주세요.
              </p>
              <button
                onClick={openLoginModal}
                className="inline-block px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                로그인하기
              </button>
            </div>
          </div>
        </main>
        <LoginModal />
      </div>
    );
  }

  // Implemented scenario - ChatInterface handles full layout
  return (
    <div className="min-h-screen bg-gray-50">
      <ChatHeader
        onToggleSidebar={toggleSidebar}
        onOpenSettings={openSettings}
        title={scenario.title}
        showBackButton={true}
      />

      <main style={{ height: 'calc(100vh - 64px)' }}>
        {/* ChatInterface handles full layout (left background + right chat) */}
        <ChatInterface
          characterId={characterId || 'ending'}
          initialSessionId={resumeSessionId}
        />
      </main>

      <LoginModal />

      {/* Session Resume Modal */}
      {showResumeModal && lastSession && (
        <SessionResumeModal
          lastSession={lastSession}
          onResume={handleResume}
          onNewSession={handleNewSession}
          onClose={() => setShowResumeModal(false)}
        />
      )}
    </div>
  );
}
