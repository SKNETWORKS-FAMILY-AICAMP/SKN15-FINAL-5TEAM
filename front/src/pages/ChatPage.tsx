import { useParams, Link, useNavigate, useBeforeUnload } from 'react-router-dom';
import { useEffect, useState, useCallback } from 'react';
import ChatInterface from '@/components/ChatInterface';
import ChatHeader from '@/components/ChatHeader';
import LoginModal from '@/components/LoginModal';
import SessionResumeModal from '@/components/SessionResumeModal';
import TutorialOverlay from '@/components/TutorialOverlay';
import { useApp } from '@/contexts/AppContext';
import { apiClient, LastSessionInfo, ScenarioCard } from '@/services/api';

const SCENARIO_ID_MAP: Record<string, string> = {
  train: 'mugen_train_full',
  ending: 'cutscene5_llm_driven',
  mugen_train_full: 'mugen_train_full',
};

export default function ChatPage() {
  const { characterId } = useParams<{ characterId: string }>();
  const { toggleSidebar, openSettings, isLoggedIn, isAuthLoading, openLoginModal, currentUserId } = useApp();
  const navigate = useNavigate();

  // Scenario loading state
  const [scenario, setScenario] = useState<ScenarioCard | null>(null);
  const [scenarioLoading, setScenarioLoading] = useState(true);
  const [scenarioError, setScenarioError] = useState<string | null>(null);

  // Session restoration state
  const [lastSession, setLastSession] = useState<LastSessionInfo | null>(null);
  const [showResumeModal, setShowResumeModal] = useState(false);
  const [resumeSessionId, setResumeSessionId] = useState<string | undefined>(undefined);
  const [sessionCheckDone, setSessionCheckDone] = useState(false);

  // Invited characters state (from ChatInterface)
  const [invitedCharacters, setInvitedCharacters] = useState<string[]>([]);

  // Track if user has interacted with chat (to show exit warning)
  const [hasStartedChat, setHasStartedChat] = useState(false);
  const [showTutorial, setShowTutorial] = useState(false);

  // Load scenario data from API
  useEffect(() => {
    const loadScenario = async () => {
      if (!characterId) {
        setScenarioError('시나리오 ID가 필요합니다.');
        setScenarioLoading(false);
        return;
      }

      setScenarioLoading(true);
      setScenarioError(null);

      try {
        const data = await apiClient.getScenario(characterId);
        setScenario(data);
      } catch (err) {
        console.error('Failed to load scenario:', err);
        setScenarioError('시나리오를 불러올 수 없습니다.');
      } finally {
        setScenarioLoading(false);
      }
    };

    loadScenario();
  }, [characterId]);

  // Authentication guard: show login modal if not authenticated (after auth loading completes)
  useEffect(() => {
    if (!isAuthLoading) {
      if (!isLoggedIn) {
        openLoginModal();
        setSessionCheckDone(false);
        setShowTutorial(false);
      } else {
        const tutorialKey = currentUserId ? `tutorialCompleted:${currentUserId}` : 'tutorialCompleted:guest';
        if (!localStorage.getItem(tutorialKey)) {
          setShowTutorial(true);
        }
      }
    }
  }, [isAuthLoading, isLoggedIn, openLoginModal, currentUserId]);

  // Check for last session after login (only after auth loading completes)
  useEffect(() => {
    if (!isAuthLoading && isLoggedIn && characterId && !sessionCheckDone) {
      checkLastSession();
    }
  }, [isAuthLoading, isLoggedIn, characterId, sessionCheckDone]);

  const checkLastSession = async () => {
    try {
      const backendScenarioId = SCENARIO_ID_MAP[characterId || ''] || characterId;
      const session = await apiClient.getUserLastSession(backendScenarioId);

      if (session) {
        // 마지막 세션이 있으면 모달 표시, sessionCheckDone은 사용자 선택 후에 true로 설정
        setLastSession(session);
        setShowResumeModal(true);
        // sessionCheckDone은 false로 유지 (사용자 선택 대기)
      } else {
        // 마지막 세션이 없으면 바로 새 세션 시작 가능
        setSessionCheckDone(true);
      }
    } catch (error) {
      console.error('Failed to check last session:', error);
      // 에러 발생 시에도 새 세션 시작 가능
      setSessionCheckDone(true);
    }
  };

  const handleResume = (sessionId: string) => {
    console.log('Resuming session:', sessionId);
    setResumeSessionId(sessionId);
    setShowResumeModal(false);
    setSessionCheckDone(true);  // 사용자가 "이어하기" 선택 완료
  };

  const handleNewSession = () => {
    console.log('Starting new session');
    setResumeSessionId(undefined);
    setShowResumeModal(false);
    setSessionCheckDone(true);  // 사용자가 "새로 시작" 선택 완료
  };

  const handleCompleteTutorial = () => {
    const tutorialKey = currentUserId ? `tutorialCompleted:${currentUserId}` : 'tutorialCompleted:guest';
    localStorage.setItem(tutorialKey, 'true');
    setShowTutorial(false);
  };

  // Warn user before leaving page (browser close/refresh)
  useBeforeUnload(
    useCallback((event) => {
      if (hasStartedChat) {
        event.preventDefault();
        // Modern browsers display a generic message, but we set returnValue anyway
        return (event.returnValue = '정말 나가시겠습니까? 진행 중인 대화가 저장되지 않을 수 있습니다.');
      }
    }, [hasStartedChat])
  );

  // Handle back button navigation with confirmation
  const handleBackNavigation = useCallback(() => {
    if (hasStartedChat) {
      const confirmed = window.confirm('정말 나가시겠습니까? 진행 중인 대화가 저장되지 않을 수 있습니다.');
      if (confirmed) {
        navigate('/');
      }
    } else {
      navigate('/');
    }
  }, [hasStartedChat, navigate]);

  // Loading state for scenario
  if (scenarioLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <ChatHeader
          onToggleSidebar={toggleSidebar}
          onOpenSettings={openSettings}
          title="로딩 중..."
          showBackButton={true}
          onBackClick={handleBackNavigation}
        />
        <main className="relative" style={{ height: 'calc(100vh - 64px)' }}>
          <div className="relative z-10 flex items-center justify-center h-full">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
              <p className="mt-4 text-gray-600">시나리오를 불러오는 중...</p>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // Error state or scenario not found
  if (scenarioError || !scenario) {
    return (
      <div className="min-h-screen bg-gray-50">
        <ChatHeader
          onToggleSidebar={toggleSidebar}
          onOpenSettings={openSettings}
          title="알 수 없는 시나리오"
          showBackButton={true}
          onBackClick={handleBackNavigation}
        />
        <main className="relative" style={{ height: 'calc(100vh - 64px)' }}>
          <div className="relative z-10 flex items-center justify-center h-full">
            <div className="text-center bg-white bg-opacity-90 p-8 rounded-xl shadow-xl max-w-md">
              <div className="text-6xl mb-6">❓</div>
              <h1 className="text-3xl font-bold mb-4 text-gray-800">
                {scenarioError ? '시나리오 로딩 실패' : '존재하지 않는 시나리오'}
              </h1>
              <p className="text-gray-600 mb-6">
                {scenarioError || '요청하신 시나리오를 찾을 수 없습니다.'}
              </p>
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

  // Check if implemented (is_active: true means active, false means not yet available)
  if (!scenario.is_active) {
    return (
      <div className="min-h-screen bg-gray-50">
        <ChatHeader
          onToggleSidebar={toggleSidebar}
          onOpenSettings={openSettings}
          title={scenario.title}
          showBackButton={true}
          onBackClick={handleBackNavigation}
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
              <p className="text-sm text-gray-500 mb-6">곧 만나보실 수 있습니다!</p>
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
          onBackClick={handleBackNavigation}
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
      {showTutorial && <TutorialOverlay onComplete={handleCompleteTutorial} />}
      <ChatHeader
        onToggleSidebar={toggleSidebar}
        onOpenSettings={openSettings}
        title={scenario.title}
        showBackButton={true}
        invitedCharacters={invitedCharacters}
        onBackClick={handleBackNavigation}
      />

      <main style={{ height: 'calc(100vh - 64px)' }}>
        {/* ChatInterface handles full layout (left background + right chat) */}
        <ChatInterface
          characterId={characterId || 'ending'}
          initialSessionId={resumeSessionId}
          onInvitedCharactersChange={setInvitedCharacters}
          onMessageSent={() => setHasStartedChat(true)}
          sessionCheckDone={sessionCheckDone}
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
