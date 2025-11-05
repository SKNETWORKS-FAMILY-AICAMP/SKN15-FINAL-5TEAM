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
  const { toggleSidebar, openSettings, isLoggedIn, isAuthLoading, openLoginModal } = useApp();

  // Session restoration state
  const [lastSession, setLastSession] = useState<LastSessionInfo | null>(null);
  const [showResumeModal, setShowResumeModal] = useState(false);
  const [resumeSessionId, setResumeSessionId] = useState<string | undefined>(undefined);
  const [sessionCheckDone, setSessionCheckDone] = useState(false);

  // Authentication guard: show login modal if not authenticated
  useEffect(() => {
    // isAuthLoading이 false가 되어 로딩이 완료된 후에만 체크
    if (!isAuthLoading && !isLoggedIn) {
      openLoginModal();
      setSessionCheckDone(false);
    }
  }, [isLoggedIn, isAuthLoading, openLoginModal]);

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
  const scenarioLookupKey =
    characterId && !scenarios[characterId]
      ? SCENARIO_ID_MAP[characterId] || characterId
      : characterId || null;
  const scenario = scenarioLookupKey ? scenarios[scenarioLookupKey] : null;

  // Fallback for unknown scenarios
  if (!scenario) {
    return (
      <div className="min-h-screen bg-[#f5f2ff]">
        <ChatHeader
          onToggleSidebar={toggleSidebar}
          onOpenSettings={openSettings}
          title="알 수 없는 시나리오"
          showBackButton={true}
          titleClassName="font-display-main text-theme-primary"
        />
        <main className="relative" style={{ height: 'calc(100vh - 64px)' }}>
          <div className="relative z-10 flex items-center justify-center h-full px-4">
            <div className="text-center card-surface p-8 rounded-2xl max-w-md w-full">
              <div className="text-6xl mb-6">❓</div>
              <h1 className="text-3xl font-bold mb-4 text-theme-primary">존재하지 않는 시나리오</h1>
              <p className="text-theme-secondary mb-6">요청하신 시나리오를 찾을 수 없습니다.</p>
              <Link
                to="/"
                className="inline-block px-6 py-3 bg-gradient-to-r from-[#2f1d83] via-[#4331c5] to-[#7a1fb9] text-white rounded-lg transition-transform hover:scale-[1.02] hover:shadow-[0_16px_32px_rgba(67,49,197,0.35)]"
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
      <div className="min-h-screen bg-[#f5f2ff]">
        <ChatHeader
          onToggleSidebar={toggleSidebar}
          onOpenSettings={openSettings}
          title={scenario.title}
          showBackButton={true}
          titleClassName="font-display-main text-theme-primary"
        />
        <main className="relative" style={{ height: 'calc(100vh - 64px)' }}>
          <div className="relative z-10 flex items-center justify-center h-full px-4">
            <div className="text-center card-surface p-8 rounded-2xl max-w-md w-full">
              <div className="text-6xl mb-6">🚧</div>
              <h1 className="text-3xl font-bold mb-4 text-theme-primary">준비 중입니다</h1>
              <p className="text-theme-secondary mb-2">
                <span className="font-semibold text-theme-primary">{scenario.title}</span>
                {' '}시나리오는 현재 개발 중입니다.
              </p>
              <p className="text-sm text-theme-secondary mb-6">백엔드 API 연결 후 이용 가능합니다!</p>
              <Link
                to="/"
                className="inline-block px-6 py-3 bg-gradient-to-r from-[#2f1d83] via-[#4331c5] to-[#7a1fb9] text-white rounded-lg transition-transform hover:scale-[1.02] hover:shadow-[0_16px_32px_rgba(67,49,197,0.35)]"
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
      <div className="min-h-screen bg-[#f5f2ff]">
        <ChatHeader
          onToggleSidebar={toggleSidebar}
          onOpenSettings={openSettings}
          title={scenario?.title || '채팅'}
          showBackButton={true}
          titleClassName="font-display-main text-theme-primary"
        />
        <main className="relative" style={{ height: 'calc(100vh - 64px)' }}>
          <div className="relative z-10 flex items-center justify-center h-full px-4">
            <div className="text-center card-surface p-8 rounded-2xl max-w-md w-full">
              <div className="text-6xl mb-6">🔐</div>
              <h1 className="text-3xl font-bold mb-4 text-theme-primary">로그인이 필요합니다</h1>
              <p className="text-theme-secondary mb-6">
                채팅을 시작하려면 로그인해주세요.
              </p>
              <button
                onClick={openLoginModal}
                className="inline-block px-6 py-3 bg-gradient-to-r from-[#2f1d83] via-[#4331c5] to-[#7a1fb9] text-white rounded-lg transition-transform hover:scale-[1.02] hover:shadow-[0_16px_32px_rgba(67,49,197,0.35)]"
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
    <div className="min-h-screen bg-[#f5f2ff]">
      <ChatHeader
        onToggleSidebar={toggleSidebar}
        onOpenSettings={openSettings}
        title="KIME CHAT"
        showBackButton={true}
        titleClassName="font-display-main text-theme-primary"
      />

      <main style={{ height: 'calc(100vh - 64px)' }}>
        {/* ChatInterface handles full layout (left background + right chat) */}
        <ChatInterface
          characterId={characterId || 'ending'}
          initialSessionId={resumeSessionId}
          scenarioTitle={scenario.title}
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
