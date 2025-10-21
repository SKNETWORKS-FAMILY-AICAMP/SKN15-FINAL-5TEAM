import { useParams, Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import ChatHeader from '@/components/ChatHeader';
import { useApp } from '@/contexts/AppContext';
import scenariosData from '@/data/scenarios.json';

interface Character {
  name: string;
  image: string;
  greeting: string;
  status: string;
  color: string;
}

interface ScenarioData {
  id: string;
  title: string;
  emoji: string;
  description: string;
  detailDescription: string;
  image: string;
  implemented: boolean;
  type: string;
  tags: string[];
  category: string;
  mood: string[];
  likes: number;
  comments: number;
  views: number;
  characters?: Character[];
}

export default function CharacterPage() {
  const { characterId } = useParams<{ characterId: string }>();
  const { toggleSidebar, openSettings } = useApp();
  const navigate = useNavigate();
  const [scenarioExpanded, setScenarioExpanded] = useState(false);
  const [charactersExpanded, setCharactersExpanded] = useState(true);
  const [isLiked, setIsLiked] = useState(false);

  // Load scenario data dynamically from JSON
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

  const handleStartChat = () => {
    if (scenario.implemented) {
      navigate(`/chat/${scenario.id}`);
    } else {
      alert('백엔드 API 연결 후 채팅 기능이 활성화됩니다!');
    }
  };

  const handleLike = () => {
    setIsLiked(!isLiked);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <ChatHeader
        onToggleSidebar={toggleSidebar}
        onOpenSettings={openSettings}
        title={scenario.title}
        showBackButton={true}
      />

      <main className="overflow-y-auto" style={{ height: 'calc(100vh - 64px)' }}>
        <div className="max-w-7xl mx-auto px-6 py-8">
          {/* Hero Section - 상단 메인 섹션 */}
          <div className="bg-white rounded-3xl shadow-lg overflow-hidden mb-6">
            <div className="grid md:grid-cols-2 gap-0">
              {/* 왼쪽: 이미지 */}
              <div className="relative h-96 md:h-auto">
                <img
                  src={scenario.image}
                  alt={scenario.title}
                  className="w-full h-full object-cover"
                />
                <div className="absolute top-4 left-4">
                  <Link
                    to="/"
                    className="bg-white bg-opacity-90 hover:bg-opacity-100 rounded-full p-2 inline-flex items-center justify-center transition-all"
                  >
                    <svg className="w-6 h-6 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                  </Link>
                </div>
              </div>

              {/* 오른쪽: 정보 */}
              <div className="p-8 flex flex-col justify-between">
                <div>
                  <h1 className="text-4xl font-bold mb-4 text-gray-900">{scenario.title}</h1>

                  {/* 태그 */}
                  <div className="flex flex-wrap gap-2 mb-4">
                    {scenario.tags.map((tag, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 bg-purple-100 text-purple-600 rounded-full text-sm font-medium"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>

                  {/* 통계 */}
                  <div className="flex items-center gap-6 mb-6 text-gray-600">
                    <button
                      onClick={handleLike}
                      className="flex items-center gap-2 hover:text-red-500 transition-colors"
                    >
                      <svg
                        className={`w-5 h-5 ${isLiked ? 'fill-red-500 text-red-500' : ''}`}
                        fill={isLiked ? 'currentColor' : 'none'}
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                      </svg>
                      <span className="font-medium">{scenario.likes + (isLiked ? 1 : 0)}</span>
                      <span>좋아요</span>
                    </button>

                    <div className="flex items-center gap-2">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                      </svg>
                      <span className="font-medium">{scenario.comments}</span>
                      <span>댓글</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                      <span className="font-medium">{scenario.views}</span>
                      <span>조회수</span>
                    </div>
                  </div>

                  {/* 설명 */}
                  <p className="text-gray-700 text-lg leading-relaxed mb-6">
                    {scenario.description}
                  </p>
                </div>

                {/* 버튼 */}
                <div>
                  <button
                    onClick={handleStartChat}
                    className="w-full py-4 bg-purple-600 hover:bg-purple-700 text-white rounded-xl font-semibold text-lg transition-colors flex items-center justify-center gap-2"
                  >
                    <span>채팅 시작하기</span>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* 하단 2열 레이아웃 */}
          <div className="grid md:grid-cols-3 gap-6">
            {/* 왼쪽 컬럼: 카테고리 & 랭킹 */}
            <div className="md:col-span-1 space-y-6">
              {/* 카테고리 */}
              <div className="bg-white rounded-2xl shadow-md p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
                    <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                    </svg>
                  </div>
                  <h2 className="text-xl font-bold text-gray-900">카테고리</h2>
                </div>
                <p className="text-gray-700 font-medium mb-3">{scenario.category}</p>
                <div className="flex flex-wrap gap-2">
                  {scenario.mood.map((mood, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-purple-50 text-purple-600 rounded-full text-sm"
                    >
                      {mood}
                    </span>
                  ))}
                </div>
              </div>

              {/* 주간 랭킹 */}
              <div className="bg-white rounded-2xl shadow-md p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
                      <svg className="w-5 h-5 text-orange-600" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
                      </svg>
                    </div>
                    <h2 className="text-xl font-bold text-gray-900">주간 랭킹</h2>
                  </div>
                  <span className="text-xs text-purple-600 bg-purple-50 px-2 py-1 rounded-full font-medium">
                    실시간
                  </span>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between p-2 hover:bg-gray-50 rounded-lg transition-colors">
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-bold text-purple-600">1</span>
                      <span className="text-sm text-gray-700">엔딩 이후</span>
                    </div>
                    <span className="text-xs text-gray-500">2,847 ↑</span>
                  </div>

                  <div className="flex items-center justify-between p-2 hover:bg-gray-50 rounded-lg transition-colors">
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-bold text-gray-600">2</span>
                      <span className="text-sm text-gray-700">무한성</span>
                    </div>
                    <span className="text-xs text-gray-500">2,156 ↑</span>
                  </div>

                  <div className="flex items-center justify-between p-2 hover:bg-gray-50 rounded-lg transition-colors">
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-bold text-gray-600">3</span>
                      <span className="text-sm text-gray-700">아이돌/밴드 AU</span>
                    </div>
                    <span className="text-xs text-gray-500">1,923 ↑</span>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-gray-100">
                  <p className="text-xs text-gray-500 text-center">
                    현재 시나리오 랭킹: <span className="text-purple-600 font-bold">#위워</span>
                  </p>
                </div>
              </div>
            </div>

            {/* 오른쪽 컬럼: 시나리오 소개 & 등장인물 */}
            <div className="md:col-span-2 space-y-6">
              {/* 시나리오 소개 */}
              <div className="bg-white rounded-2xl shadow-md overflow-hidden">
                <button
                  onClick={() => setScenarioExpanded(!scenarioExpanded)}
                  className="w-full p-6 flex items-center justify-between hover:bg-gray-50 transition-colors"
                >
                  <h2 className="text-2xl font-bold text-gray-900">시나리오 소개</h2>
                  <svg
                    className={`w-6 h-6 text-gray-600 transition-transform ${scenarioExpanded ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {scenarioExpanded && (
                  <div className="px-6 pb-6">
                    <p className="text-gray-700 leading-relaxed text-lg mb-6">
                      {scenario.detailDescription}
                    </p>

                    <div className="bg-purple-50 border-l-4 border-purple-600 p-4 rounded-r-lg">
                      <h3 className="flex items-center gap-2 text-purple-900 font-semibold mb-2">
                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
                        </svg>
                        특별한 경험
                      </h3>
                      <p className="text-purple-800 text-sm">
                        지열한 전투가 끝난 후의 평화로운 일상을 체험해보세요. 동료들과 함께하는 소소한 행복과 서로를 돌보는 따뜻한 마음을 느낄 수 있는 힐링 스토리입니다!
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* 등장인물 */}
              {scenario.characters && scenario.characters.length > 0 && (
                <div className="bg-white rounded-2xl shadow-md overflow-hidden">
                  <button
                    onClick={() => setCharactersExpanded(!charactersExpanded)}
                    className="w-full p-6 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <h2 className="text-2xl font-bold text-gray-900">등장인물</h2>
                    <svg
                      className={`w-6 h-6 text-gray-600 transition-transform ${charactersExpanded ? 'rotate-180' : ''}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>

                  {charactersExpanded && (
                    <div className="px-6 pb-6">
                      <div className="grid md:grid-cols-2 gap-4">
                        {scenario.characters.map((character, index) => (
                          <div
                            key={index}
                            className={`${character.color} rounded-2xl p-4 border-2 border-transparent hover:border-purple-300 transition-all`}
                          >
                            <div className="flex items-start gap-4">
                              <div className="relative flex-shrink-0">
                                <img
                                  src={character.image}
                                  alt={character.name}
                                  className="w-16 h-16 rounded-full object-cover border-4 border-white shadow-md"
                                />
                                <div className="absolute bottom-0 right-0 w-4 h-4 bg-green-500 border-2 border-white rounded-full"></div>
                              </div>

                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between mb-1">
                                  <h3 className="font-bold text-gray-900 text-lg">{character.name}</h3>
                                  <span className="text-xs bg-white px-2 py-1 rounded-full text-gray-600 font-medium">
                                    {character.status}
                                  </span>
                                </div>
                                <p className="text-gray-700 text-sm leading-relaxed">
                                  {character.greeting}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>

                      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-xl p-4">
                        <h4 className="flex items-center gap-2 text-blue-900 font-semibold mb-2">
                          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
                          </svg>
                          상호작용 팁
                        </h4>
                        <p className="text-blue-800 text-sm">
                          각 캐릭터는 고유한 성격과 말투를 가지고 있어요. 자연스럽게 대화하면서 그들의 개성을 느껴보세요!
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
