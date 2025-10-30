import { useState } from 'react';
import { Link } from 'react-router-dom';
import CharacterCarousel from '@/components/CharacterCarousel';
import ChatHeader from '@/components/ChatHeader';
import MyAccountModal from '@/components/MyAccountModal';
import LoginModal from '@/components/LoginModal';
import { useApp } from '@/contexts/AppContext';

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
  const { toggleSidebar, openSettings } = useApp();

  const characters: CharacterCard[] = [
    {
      id: 'tanjiro',
      title: '편의점 알바생 탄지로',
      description: '탄지로와 함께하는 편의점 일상 체험',
      image: `${CDN_URL}/편의점탄지로.png`,
      likes: 121,
      comments: 45,
      views: 1200,
      tags: ['#편의점', '#일상', '#탄지로'],
      size: 'normal',
      link: '/chat/tanjiro'
    },
    {
      id: 'train',
      title: '무한열차',
      description: '열차 안에서 벌어지는 사건에 휘말려 캐릭터들과 협력하여 생존 및 해결을 도모',
      image: `${CDN_URL}/무한열차.jpeg`,
      likes: 98,
      comments: 32,
      views: 890,
      tags: ['#무한열차', '#꿈속전투', '#엔무'],
      size: 'normal',
      link: '/character/train'
    },
    {
      id: 'infinity-castle',
      title: '무한성',
      description: '최종 결전을 배경으로, 캐릭터들과 함께 전략을 세우며 전투 직전의 긴장감을 체험',
      image: `${CDN_URL}/무한성.webp`,
      likes: 156,
      comments: 67,
      views: 1850,
      tags: ['#최종결전', '#귀살대', '#무잔전'],
      size: 'large',
      link: '/character/infinity-castle'
    },
    {
      id: 'ending',
      title: '엔딩 이후',
      description: '최종 결전 후 동료들과 함께하는 평범하지만 소중한 일상. 탄지로, 젠이츠, 이노스케와 함께 마을 순찰과 훈련을 하며 서로를 돌보는 따뜻한 이야기',
      image: `${CDN_URL}/엔딩이후.png`,
      likes: 87,
      comments: 28,
      views: 720,
      tags: ['#엔딩이후', '#일상', '#평화', '#동료애'],
      size: 'normal',
      link: '/chat/ending'
    },
    {
      id: 'counseling',
      title: '귀칼 상담소 AU',
      description: '캐릭터들이 상담사가 되어 서로의 고민을 풀어가는 힐링 스토리',
      image: `${CDN_URL}/귀칼상담소.png`,
      likes: 134,
      comments: 52,
      views: 1150,
      tags: ['#상담소', '#힐링AU', '#감정공감'],
      size: 'normal',
      link: '/chat/counseling'
    },
    {
      id: 'idol',
      title: '아이돌/밴드 AU',
      description: '귀멸 캐릭터들이 아이돌 그룹으로 활동, 매니저 or 팬클럽으로서 그들의 성장과 무대를 지켜봄',
      image: `${CDN_URL}/아이돌밴드.png`,
      likes: 203,
      comments: 89,
      views: 2100,
      tags: ['#아이돌AU', '#밴드AU', '#팬심폭발'],
      size: 'normal',
      link: '/chat/idol'
    }
  ];

  const handleLike = (cardId: string) => {
    setLikedCards(prev => {
      const newLiked = new Set(prev);
      if (newLiked.has(cardId)) {
        newLiked.delete(cardId);
      } else {
        newLiked.add(cardId);
      }
      return newLiked;
    });
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
    <div className="min-h-screen bg-zeplin-main">
      {/* 헤더 */}
      <ChatHeader
        onToggleSidebar={toggleSidebar}
        onOpenSettings={openSettings}
        title="Kime Chat"
      />

      {/* 메인 콘텐츠 */}
      <main
        className="relative bg-zeplin-main"
        style={{
          backgroundImage: `url('${CDN_URL}/홈배경.jpg')`,
          height: 'calc(100vh - 64px)'
        }}
      >
        {/* 배경 오버레이 */}
        <div className="absolute inset-0 bg-purple-50 bg-opacity-80"></div>

        {/* 컨텐츠 컨테이너 */}
        <div className="relative z-10 h-full flex flex-col justify-between max-w-7xl mx-auto px-4 py-4">

          {/* 상단 네비게이션 */}
          <div className="flex justify-between items-center mb-4">
            <div className="flex space-x-8">
              {tabs.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`relative text-lg font-inter font-medium px-3 py-1 transition-all duration-300 ${
                    activeTab === tab
                      ? 'text-purple-700'
                      : 'text-gray-600 hover:text-purple-600'
                  }`}
                >
                  {tab}
                  {activeTab === tab && (
                    <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-purple-600 rounded-full"></div>
                  )}
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-purple-300 rounded-full scale-x-0 hover:scale-x-100 transition-transform duration-300"></div>
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
                  className="w-80 px-4 py-2 pl-10 bg-white bg-opacity-90 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all duration-300 text-gray-700 placeholder-gray-500"
                />
                <svg
                  className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
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
              <h1 className="text-5xl font-bold font-inter text-black" style={{ letterSpacing: '-2.16px' }}>
                Kime Chat
              </h1>
            </div>

            {searchQuery && (
              <div className="mt-2 text-sm text-gray-600 bg-white bg-opacity-70 px-4 py-2 rounded-full inline-block">
                <span className="font-medium">"{searchQuery}"</span> 검색 결과:
                <span className="font-bold text-purple-600 ml-1">{filteredCharacters.length}개</span>
              </div>
            )}
          </div>

          {/* 캐릭터 표시 영역 */}
          <div className="flex-1 flex items-center">
            {searchQuery && filteredCharacters.length > 0 && filteredCharacters.length <= 3 ? (
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
                <h3 className="text-xl font-semibold text-gray-600 mb-2">검색 결과가 없습니다</h3>
                <p className="text-gray-500">"{searchQuery}"에 대한 캐릭터를 찾을 수 없습니다.</p>
                <button
                  onClick={() => setSearchQuery('')}
                  className="mt-4 px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
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

    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts = text.split(regex);

    return parts.map((part, index) =>
      regex.test(part) ? (
        <span key={index} className="bg-yellow-200 font-semibold">{part}</span>
      ) : part
    );
  };

  return (
    <Link to={character.link}>
      <div className="bg-white rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 overflow-hidden cursor-pointer group hover:scale-105">
        <div className="relative h-48 overflow-hidden">
          <img
            src={character.image}
            alt={character.title}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
          />
          <div className="absolute top-2 right-2">
            <span className="bg-purple-600 text-white text-xs px-2 py-1 rounded-full">
              검색 결과
            </span>
          </div>
        </div>

        <div className="p-4">
          <h3 className="font-bold text-lg mb-2 text-gray-800">
            {highlightText(character.title, searchQuery)}
          </h3>

          <p className="text-gray-600 text-sm mb-3 line-clamp-3">
            {highlightText(character.description, searchQuery)}
          </p>

          <div className="flex flex-wrap gap-1 mb-3">
            {character.tags.map((tag, index) => (
              <span
                key={index}
                className="text-xs bg-purple-100 text-purple-600 px-2 py-1 rounded-full"
              >
                {highlightText(tag, searchQuery)}
              </span>
            ))}
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4 text-sm text-gray-500">
              <div className="flex items-center space-x-1">
                <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clipRule="evenodd" />
                </svg>
                <span>{character.likes + (isLiked ? 1 : 0)}</span>
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
              className="p-2 rounded-full hover:bg-gray-100 transition-colors"
            >
              <svg
                className={`w-5 h-5 ${isLiked ? 'text-red-500 fill-current' : 'text-gray-400'}`}
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
