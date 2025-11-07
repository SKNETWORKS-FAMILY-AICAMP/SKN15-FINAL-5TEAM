import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import CharacterCarousel from '@/components/CharacterCarousel';
import ChatHeader from '@/components/ChatHeader';
import MyAccountModal from '@/components/MyAccountModal';
import LoginModal from '@/components/LoginModal';
import { useApp } from '@/contexts/AppContext';
import { apiClient, type ScenarioCard } from '@/services/api';

const CDN_URL = import.meta.env.VITE_CDN_URL || '/images';

interface CharacterCard {
  id: string;
  title: string;
  description: string;
  image: string;
  likes: number;
  comments: number;
  views: number;
  tags: string[];
  size: 'large' | 'normal';
  link: string;
}

export default function HomePage() {
  const [activeTab, setActiveTab] = useState('Home');
  const [likedCards, setLikedCards] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [characters, setCharacters] = useState<CharacterCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { toggleSidebar, openSettings, currentUser } = useApp();

  // Load scenarios from API
  useEffect(() => {
    const loadScenarios = async () => {
      setLoading(true);
      setError(null);
      try {
        // Use authenticated endpoint if user is logged in for user-specific data
        const scenarios: ScenarioCard[] = currentUser
          ? await apiClient.getUserScenarios()
          : await apiClient.getScenarios();

        // Transform API data to CharacterCard format
        const transformedCharacters: CharacterCard[] = scenarios.map((scenario) => ({
          id: scenario.scenario_id,
          title: scenario.title,
          description: scenario.description,
          image: scenario.image_url,
          likes: scenario.likes,
          comments: scenario.comments,
          views: scenario.views,
          tags: scenario.tags.map(tag => tag.startsWith('#') ? tag : `#${tag}`),
          size: scenario.card_size,
          link: `/character/${scenario.scenario_id}`  // Always navigate to detail page first
        }));

        setCharacters(transformedCharacters);

        // Set initial liked cards from user progress (if authenticated)
        if (currentUser) {
          const likedScenarioIds = scenarios
            .filter(s => s.is_liked)
            .map(s => s.scenario_id);
          setLikedCards(new Set(likedScenarioIds));
        }
      } catch (err) {
        console.error('Failed to load scenarios:', err);
        setError('시나리오를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.');
      } finally {
        setLoading(false);
      }
    };

    loadScenarios();
  }, [currentUser]);

  const handleLike = async (cardId: string) => {
    // Optimistically update UI first
    const isCurrentlyLiked = likedCards.has(cardId);
    setLikedCards(prev => {
      const newLiked = new Set(prev);
      if (newLiked.has(cardId)) {
        newLiked.delete(cardId);
      } else {
        newLiked.add(cardId);
      }
      return newLiked;
    });

    // Also update the likes count in the characters array
    setCharacters(prev => prev.map(char => {
      if (char.id === cardId) {
        return {
          ...char,
          likes: isCurrentlyLiked ? char.likes - 1 : char.likes + 1
        };
      }
      return char;
    }));

    // Call API if user is authenticated
    if (currentUser) {
      try {
        const result = await apiClient.toggleScenarioLike(cardId);

        // Update likes count with server response
        setCharacters(prev => prev.map(char => {
          if (char.id === cardId) {
            return { ...char, likes: result.total_likes };
          }
          return char;
        }));
      } catch (err) {
        console.error('Failed to toggle like:', err);
        // Revert optimistic update on error
        setLikedCards(prev => {
          const newLiked = new Set(prev);
          if (isCurrentlyLiked) {
            newLiked.add(cardId);
          } else {
            newLiked.delete(cardId);
          }
          return newLiked;
        });
        setCharacters(prev => prev.map(char => {
          if (char.id === cardId) {
            return {
              ...char,
              likes: isCurrentlyLiked ? char.likes + 1 : char.likes - 1
            };
          }
          return char;
        }));
      }
    }
  };

  const filteredCharacters = characters.filter(character => {
    if (!searchQuery.trim()) return true;

    const query = searchQuery.toLowerCase().trim();

    const titleMatch = character.title.toLowerCase().includes(query);
    const descriptionMatch = character.description.toLowerCase().includes(query);
    const tagMatch = character.tags.some(tag =>
      tag.toLowerCase().replace('#', '').includes(query) ||
      tag.toLowerCase().includes(query)
    );
    const idMatch = character.id.toLowerCase().includes(query);

    const keywords = query.split(' ').filter(keyword => keyword.length > 0);
    const keywordMatch = keywords.every(keyword =>
      character.title.toLowerCase().includes(keyword) ||
      character.description.toLowerCase().includes(keyword) ||
      character.tags.some(tag => tag.toLowerCase().replace('#', '').includes(keyword)) ||
      character.id.toLowerCase().includes(keyword)
    );

    return titleMatch || descriptionMatch || tagMatch || idMatch || keywordMatch;
  });

  const tabs = ['Home', 'Ranking', 'Category'];

  return (
    <div className="min-h-screen bg-hero text-theme-primary">
      {/* 헤더 */}
      <ChatHeader
        onToggleSidebar={toggleSidebar}
        onOpenSettings={openSettings}
        title="KIME CHAT"
        titleClassName="font-display-main text-theme-primary"
      />

      {/* 메인 콘텐츠 */}
      <main
        className="relative"
        style={{
          backgroundImage: `url('${CDN_URL}/홈배경.jpg')`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          height: 'calc(100vh - 64px)'
        }}
      >
        {/* 배경 오버레이 */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute inset-0 bg-hero-overlay opacity-70 mix-blend-screen"></div>
          <div className="absolute inset-0 bg-white/45 mix-blend-screen"></div>
        </div>

        {/* 컨텐츠 컨테이너 */}
        <div className="relative z-10 h-full flex flex-col justify-between max-w-7xl mx-auto px-4 py-4 text-theme-secondary">

          {/* 상단 네비게이션 */}
          <div className="flex justify-between items-center mb-4">
            <div className="flex space-x-8">
              {tabs.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`relative text-lg font-inter font-medium px-4 py-1 transition-all duration-300 rounded-full border ${
                    activeTab === tab
                      ? 'bg-theme-surface-strong text-theme-primary border-theme-card shadow-theme'
                      : 'border-transparent text-theme-secondary hover:text-theme-primary hover:bg-theme-surface'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            {/* 검색 바 */}
            <div className="flex items-center space-x-4">
              <div className="relative">
                <input
                  type="text"
                  placeholder="탄지로, 무한열차, 편의점, 상담소..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-80 px-4 py-2 pl-10 bg-theme-surface-strong border border-theme-card rounded-full focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent transition-all duration-300 text-theme-primary placeholder:text-[#a299c8]"
                />
                <svg
                  className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-theme-secondary"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery('')}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-theme-secondary hover:text-theme-primary transition-colors"
                    >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* 메인 제목 */}
          <div className="text-center flex-shrink-0">
            <div className="flex items-center justify-center space-x-4 mb-2">
              <button className="flex-shrink-0">
                <img
                  src="/images/kimechatlogo.png"
                  alt="Kime Chat Logo"
                  className="h-20 w-auto object-contain hover:scale-105 transition-transform duration-300"
                />
              </button>
              <h1
                className="text-5xl md:text-6xl font-bold font-display-main text-theme-primary drop-shadow-lg"
                style={{ textShadow: '0 10px 26px rgba(108, 92, 231, 0.25)' }}
              >
                KIME CHAT
              </h1>
            </div>

            {searchQuery && (
              <div className="mt-2 text-sm text-theme-secondary bg-white/80 px-4 py-2 rounded-full inline-block">
                <span className="font-medium text-theme-primary">"{searchQuery}"</span> 검색 결과:
                <span className="font-bold text-[#6c5ce7] ml-1">{filteredCharacters.length}개</span>
              </div>
            )}
          </div>

          {/* 캐릭터 표시 영역 */}
          <div className="flex-1 flex items-center">
            {loading ? (
              <div className="w-full flex justify-center items-center">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-purple-600 mx-auto mb-4"></div>
                  <p className="text-theme-secondary font-medium">시나리오를 불러오는 중...</p>
                </div>
              </div>
            ) : error ? (
              <div className="w-full flex justify-center items-center">
                <div className="text-center bg-theme-surface-strong rounded-2xl p-8 shadow-theme border border-theme-card">
                  <div className="text-6xl mb-4">⚠️</div>
                  <h3 className="text-xl font-semibold text-theme-primary mb-2">불러오기 실패</h3>
                  <p className="text-theme-secondary mb-4">{error}</p>
                  <button
                    onClick={() => window.location.reload()}
                    className="px-6 py-2 text-white rounded-lg transition-transform bg-gradient-to-r from-[#2f1d83] via-[#4331c5] to-[#7a1fb9] hover:scale-[1.02] hover:shadow-[0_16px_32px_rgba(67,49,197,0.35)] shadow-[0_14px_28px_rgba(47,29,131,0.3)]"
                  >
                    다시 시도
                  </button>
                </div>
              </div>
            ) : searchQuery && filteredCharacters.length > 0 && filteredCharacters.length <= 3 ? (
              <div className="w-full flex justify-center">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-4xl">
                  {filteredCharacters.map((character) => (
                    <SearchResultCard
                      key={character.id}
                      character={character}
                      isLiked={likedCards.has(character.id)}
                      onLike={() => handleLike(character.id)}
                      searchQuery={searchQuery}
                    />
                  ))}
                </div>
              </div>
            ) : (
              <CharacterCarousel
                characters={filteredCharacters}
                likedCards={likedCards}
                onLike={handleLike}
              />
            )}
          </div>

          {/* 검색 결과 없음 */}
          {searchQuery && filteredCharacters.length === 0 && (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="text-6xl mb-4">🔍</div>
                <h3 className="text-xl font-semibold text-theme-primary mb-2">검색 결과가 없습니다</h3>
                <p className="text-theme-secondary">"{searchQuery}"에 대한 캐릭터를 찾을 수 없습니다.</p>
                <button
                  onClick={() => setSearchQuery('')}
                  className="mt-4 px-6 py-2 text-white rounded-lg transition-transform bg-gradient-to-r from-[#2f1d83] via-[#4331c5] to-[#7a1fb9] hover:scale-[1.02] hover:shadow-[0_16px_32px_rgba(67,49,197,0.35)] shadow-[0_14px_28px_rgba(47,29,131,0.3)]"
                >
                  전체 보기
                </button>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Modals */}
      <MyAccountModal />
      <LoginModal />
    </div>
  );
}

// 검색 결과 카드 컴포넌트
interface SearchResultCardProps {
  character: CharacterCard;
  isLiked: boolean;
  onLike: () => void;
  searchQuery: string;
}

function SearchResultCard({ character, isLiked, onLike, searchQuery }: SearchResultCardProps) {
  const highlightText = (text: string, query: string) => {
    if (!query.trim()) return text;

    const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const parts = text.split(new RegExp(`(${escapedQuery})`, 'i'));

    return parts.map((part, index) => {
      if (part.toLowerCase() === query.toLowerCase()) {
        return (
          <span key={index} className="bg-gradient-to-r from-purple-200 to-pink-200 text-theme-primary font-semibold px-1 rounded">
            {part}
          </span>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <Link to={character.link}>
      <div className="bg-theme-surface-strong border border-theme-card rounded-2xl shadow-theme transition-all duration-300 overflow-hidden cursor-pointer group hover:-translate-y-1">
        <div className="relative h-48 overflow-hidden bg-black/40">
          <img
            src={character.image}
            alt={character.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
          <div className="absolute top-2 right-2">
            <span className="text-xs chip-theme px-2 py-1 rounded-full shadow-sm">
              검색 결과
            </span>
          </div>
        </div>

        <div className="p-4">
          <h3 className="font-bold text-lg mb-2 text-theme-primary">
            {highlightText(character.title, searchQuery)}
          </h3>

          <p className="text-theme-secondary text-sm mb-3 line-clamp-3">
            {highlightText(character.description, searchQuery)}
          </p>

          <div className="flex flex-wrap gap-1 mb-3">
            {character.tags.map((tag, index) => (
              <span
                key={index}
                className="text-xs chip-theme px-2 py-1 rounded-full"
              >
                {highlightText(tag, searchQuery)}
              </span>
            ))}
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4 text-sm text-theme-secondary">
              <div className="flex items-center space-x-1">
                <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clipRule="evenodd" />
                </svg>
                <span>{character.likes}</span>
              </div>
              <div className="flex items-center space-x-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <span>{character.comments}</span>
              </div>
              <div className="flex items-center space-x-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                <span>{character.views}</span>
              </div>
            </div>

            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onLike();
              }}
              className="p-2 rounded-full hover:bg-theme-surface transition-colors"
            >
              <svg
                className={`w-5 h-5 ${isLiked ? 'text-red-500 fill-current' : 'text-theme-secondary'}`}
                viewBox="0 0 20 20"
                fill={isLiked ? "currentColor" : "none"}
                stroke="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </Link>
  );
}
