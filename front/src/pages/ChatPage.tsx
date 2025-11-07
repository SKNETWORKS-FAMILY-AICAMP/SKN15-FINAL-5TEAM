import { useParams, Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import ChatInterface from '@/components/ChatInterface';
import ChatHeader from '@/components/ChatHeader';
import LoginModal from '@/components/LoginModal';
import SessionResumeModal from '@/components/SessionResumeModal';
import TutorialOverlay from '@/components/TutorialOverlay';
import { useApp } from '@/contexts/AppContext';
import { apiClient, LastSessionInfo } from '@/services/api';
import { getHistory } from '@/utils/storageUtils';
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
  const { characterId: routeCharacterId, sessionId: routeSessionId } = useParams<{ characterId?: string; sessionId?: string }>();
  const { toggleSidebar, openSettings, isLoggedIn, isAuthLoading, openLoginModal, currentUserId } = useApp();

  const [initialCharacterId, setInitialCharacterId] = useState<string | undefined>();
  const [initialSessionId, setInitialSessionId] = useState<string | undefined>();
  const [scenarioTitle, setScenarioTitle] = useState<string>('KIME CHAT');
  const [isReady, setIsReady] = useState(false);
  const [showTutorial, setShowTutorial] = useState(false);

  // Session restoration state
  const [lastSession, setLastSession] = useState<LastSessionInfo | null>(null);
  const [showResumeModal, setShowResumeModal] = useState(false);
  const [sessionCheckDone, setSessionCheckDone] = useState(false);

  useEffect(() => {
    // Determine if loading from history or starting a new chat
    if (routeSessionId) {
      // Loading from history
      const history = getHistory();
      const conversation = history.find(c => c.sessionId === routeSessionId);
      if (conversation) {
        setInitialCharacterId(conversation.characterId);
        setInitialSessionId(conversation.sessionId);
      } else {
        // Handle case where session ID is not in history
        console.error(`Session ${routeSessionId} not found in local history.`);
        // Maybe redirect to an error page or home
      }
    } else if (routeCharacterId) {
      // Starting a new chat
      setInitialCharacterId(routeCharacterId);
      setInitialSessionId(undefined); // Ensure it's a new session unless resumed
    }
  }, [routeCharacterId, routeSessionId]);

  // Authentication guard & Tutorial check
  useEffect(() => {
    if (!isAuthLoading) {
      if (!isLoggedIn) {
        openLoginModal();
        setSessionCheckDone(false);
      } else {
        // Show tutorial if user is logged in and hasn't completed it
        const tutorialKey = currentUserId ? `tutorialCompleted:${currentUserId}` : null;
        if (tutorialKey && !localStorage.getItem(tutorialKey)) {
          setShowTutorial(true);
        } else if (!tutorialKey && !localStorage.getItem('tutorialCompleted:guest')) {
          // Fallback for 정보 없음
          setShowTutorial(true);
        }
      }
    }
  }, [isLoggedIn, isAuthLoading, openLoginModal, currentUserId]);

  // Check for last session after login (only for new chats)
  useEffect(() => {
    if (isLoggedIn && routeCharacterId && !routeSessionId && !sessionCheckDone) {
      checkLastSession();
    }
    // If loading from history, we don't need to check for resumable sessions
    if (routeSessionId) {
        setSessionCheckDone(true);
    }
  }, [isLoggedIn, routeCharacterId, routeSessionId, sessionCheckDone]);

  const checkLastSession = async () => {
    if (!initialCharacterId) return;
    try {
      const backendScenarioId = SCENARIO_ID_MAP[initialCharacterId] || initialCharacterId;
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
    setInitialSessionId(sessionId);
    setShowResumeModal(false);
  };

  const handleNewSession = () => {
    console.log('Starting new session');
    setInitialSessionId(undefined);
    setShowResumeModal(false);
    setSessionCheckDone(true);
  };

  const handleCompleteTutorial = () => {
    const tutorialKey = currentUserId ? `tutorialCompleted:${currentUserId}` : 'tutorialCompleted:guest';
    localStorage.setItem(tutorialKey, 'true');
    setShowTutorial(false);
  };

  // Load scenario data dynamically
  const scenarios = scenariosData as Record<string, ScenarioData>;
  const scenarioLookupKey =
    initialCharacterId && !scenarios[initialCharacterId]
      ? SCENARIO_ID_MAP[initialCharacterId] || initialCharacterId
      : initialCharacterId || null;
  const scenario = scenarioLookupKey ? scenarios[scenarioLookupKey] : null;

  useEffect(() => {
    if(scenario) {
        setScenarioTitle(scenario.title);
    }
    // Mark as ready to render once we have a characterId and session check is done
    if (initialCharacterId && (sessionCheckDone || routeSessionId)) {
        setIsReady(true);
    }
  }, [initialCharacterId, sessionCheckDone, routeSessionId, scenario]);

  // Fallback for unknown scenarios
  if (!scenario && isReady) {
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

  // Render Chat now that we are ready
  return (
    <div className="min-h-screen bg-[#f5f2ff]">
      {showTutorial && <TutorialOverlay onComplete={handleCompleteTutorial} />}
      <ChatHeader
        onToggleSidebar={toggleSidebar}
        onOpenSettings={openSettings}
        title="KIME CHAT"
        showBackButton={true}
        titleClassName="font-display-main text-theme-primary"
      />

      <main style={{ height: 'calc(100vh - 64px)' }}>
        {isReady && (
            <ChatInterface
                characterId={initialCharacterId}
                initialSessionId={initialSessionId}
                scenarioTitle={scenarioTitle}
            />
        )}
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
