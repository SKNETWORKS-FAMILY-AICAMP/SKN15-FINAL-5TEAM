import { useParams, Link } from 'react-router-dom';
import ChatInterface from '@/components/ChatInterface';
import ChatHeader from '@/components/ChatHeader';
import { useApp } from '@/contexts/AppContext';
import scenariosData from '@/data/scenarios.json';

interface ScenarioData {
  id: string;
  title: string;
  image: string;
  description: string;
  detailDescription: string;
  implemented: boolean;
}

export default function ChatPage() {
  const { characterId } = useParams<{ characterId: string }>();
  const { toggleSidebar, openSettings } = useApp();

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

  // Implemented scenario - Show 2-column layout
  return (
    <div className="min-h-screen bg-gray-50">
      <ChatHeader
        onToggleSidebar={toggleSidebar}
        onOpenSettings={openSettings}
        title={scenario.title}
        showBackButton={true}
      />

      <main className="flex" style={{ height: 'calc(100vh - 64px)' }}>
        {/* Left Column: Scenario Image */}
        <div className="w-1/2 relative overflow-hidden bg-gradient-to-br from-purple-50 to-pink-50">
          <div className="absolute inset-0 flex items-center justify-center p-8">
            <div className="relative w-full h-full">
              <img
                src={scenario.image}
                alt={scenario.title}
                className="w-full h-full object-contain drop-shadow-2xl"
              />

              {/* Info Card - 이미지 위에 겹쳐서 표시 */}
              <div className="absolute bottom-8 left-8 right-8 bg-white bg-opacity-95 backdrop-blur-sm rounded-2xl shadow-2xl p-6 border border-purple-100">
                <div className="flex items-center gap-4 mb-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-purple-400 to-pink-400 rounded-full flex items-center justify-center shadow-lg">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-gray-900">Info</h3>
                    <p className="text-sm text-gray-600">시나리오 정보</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">제목</span>
                    <span className="text-sm font-semibold text-gray-900">{scenario.title}</span>
                  </div>
                  <div className="pt-2 border-t border-gray-200">
                    <p className="text-xs text-gray-500 leading-relaxed">
                      {scenario.description}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Decorative elements */}
          <div className="absolute top-0 left-0 w-full h-full pointer-events-none">
            <div className="absolute top-10 left-10 w-20 h-20 bg-purple-200 rounded-full opacity-20 blur-xl"></div>
            <div className="absolute bottom-20 right-10 w-32 h-32 bg-pink-200 rounded-full opacity-20 blur-xl"></div>
            <div className="absolute top-1/2 right-20 w-16 h-16 bg-blue-200 rounded-full opacity-20 blur-xl"></div>
          </div>
        </div>

        {/* Right Column: Chat Interface */}
        <div className="w-1/2 bg-white">
          <ChatInterface characterId={characterId || 'ending'} />
        </div>
      </main>
    </div>
  );
}
