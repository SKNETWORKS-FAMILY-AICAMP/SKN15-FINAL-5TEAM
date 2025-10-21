import { useState, useRef, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';

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

interface CharacterCarouselProps {
  characters: CharacterCard[];
  likedCards: Set<string>;
  onLike: (cardId: string) => void;
}

export default function CharacterCarousel({ characters, likedCards, onLike }: CharacterCarouselProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [currentIndex, setCurrentIndex] = useState(characters.length); // 복제된 카드들 고려
  const [containerWidth, setContainerWidth] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [expandedCard, setExpandedCard] = useState<string | null>(null);

  // 무한 순환을 위한 복제된 카드 배열 생성
  const duplicatedCharacters = [
    ...characters, // 앞쪽 복제
    ...characters, // 원본
    ...characters  // 뒤쪽 복제
  ];

  // 반응형 설정
  const getVisibleCards = useCallback(() => {
    if (containerWidth < 480) return 1; // 작은 모바일 (480px 미만)
    if (containerWidth < 768) return 1; // 모바일 (480px-767px)
    if (containerWidth < 1024) return 3; // 태블릿 (768px-1023px)
    if (containerWidth < 1280) return 5; // 작은 데스크톱 (1024px-1279px)
    return 5; // 큰 데스크톱 (1280px 이상)
  }, [containerWidth]);

  const visibleCards = getVisibleCards();
  // 5개 카드 정확 표시를 위한 카드 너비 계산 (겹침 방지를 위해 여백 추가)
  const baseCardWidth = containerWidth / 5;
  const cardWidth = baseCardWidth * 0.85; // 15% 여백으로 겹침 방지
  const cardSpacing = baseCardWidth; // 카드 간격은 기본 너비 유지
  const maxIndex = duplicatedCharacters.length - 1;

  // 컨테이너 크기 감지
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.clientWidth);
      }
    };

    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  // 동적 중앙 카드 계산 - 항상 화면 중앙에 위치한 카드 감지
  const getCurrentCenterCard = useCallback(() => {
    if (visibleCards === 1) return currentIndex;
    if (visibleCards === 3) return currentIndex + 1;
    if (visibleCards === 5) return currentIndex + 2;
    return currentIndex;
  }, [currentIndex, visibleCards]);

  const centerIndex = getCurrentCenterCard();
  // 실제 카드 인덱스 (복제 고려)
  const actualCenterIndex = centerIndex % characters.length;

  // 카드 이동
  const moveToCard = useCallback((index: number) => {
    if (isTransitioning) return;

    setCurrentIndex(index);
    setIsTransitioning(true);

    setTimeout(() => {
      setIsTransitioning(false);
      // 경계 확인 및 위치 재조정
      if (index <= 0) {
        setCurrentIndex(characters.length); // 첫 번째 세트로 점프
      } else if (index >= characters.length * 2) {
        setCurrentIndex(characters.length); // 두 번째 세트로 점프
      }
    }, 300);
  }, [isTransitioning, characters.length]);

  // 화살표 버튼 핸들러 - 진정한 무한 순환
  const handlePrevious = () => {
    const newCurrentIndex = currentIndex - 1;
    moveToCard(newCurrentIndex);
  };

  const handleNext = () => {
    const newCurrentIndex = currentIndex + 1;
    moveToCard(newCurrentIndex);
  };

  // 키보드 이벤트
  useEffect(() => {
    const handleKeydown = (e: KeyboardEvent) => {
      if (expandedCard && e.key === 'Escape') {
        e.preventDefault();
        handleCloseModal();
      } else if (!expandedCard) {
        if (e.key === 'ArrowLeft') {
          e.preventDefault();
          handlePrevious();
        } else if (e.key === 'ArrowRight') {
          e.preventDefault();
          handleNext();
        }
      }
    };

    window.addEventListener('keydown', handleKeydown);
    return () => window.removeEventListener('keydown', handleKeydown);
  }, [currentIndex, visibleCards, expandedCard]);

  // 터치 및 휠 이벤트
  const [touchStart, setTouchStart] = useState<number | null>(null);
  const [touchEnd, setTouchEnd] = useState<number | null>(null);

  const handleTouchStart = (e: React.TouchEvent) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    setTouchEnd(e.targetTouches[0].clientX);
  };

  const handleTouchEnd = () => {
    if (!touchStart || !touchEnd) return;
    const distance = touchStart - touchEnd;
    const minSwipeDistance = containerWidth < 768 ? 30 : 50; // 모바일에서 더 민감하게
    const isLeftSwipe = distance > minSwipeDistance;
    const isRightSwipe = distance < -minSwipeDistance;

    if (isLeftSwipe && !isTransitioning) {
      handleNext();
    } else if (isRightSwipe && !isTransitioning) {
      handlePrevious();
    }
  };

  const handleWheel = useCallback((e: WheelEvent) => {
    if (isTransitioning) return;

    e.preventDefault();

    // 수평 스크롤 우선, 수직 스크롤도 허용
    const threshold = 10;
    if (Math.abs(e.deltaX) > threshold || Math.abs(e.deltaY) > threshold) {
      if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
        // 수평 스크롤
        if (e.deltaX > 0) {
          handleNext();
        } else {
          handlePrevious();
        }
      } else {
        // 수직 스크롤을 수평으로 변환
        if (e.deltaY > 0) {
          handleNext();
        } else {
          handlePrevious();
        }
      }
    }
  }, [currentIndex, isTransitioning]);

  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.addEventListener('wheel', handleWheel, { passive: false });
      return () => container.removeEventListener('wheel', handleWheel);
    }
  }, [handleWheel]);

  // 인디케이터 도트 클릭
  const handleDotClick = (index: number) => {
    moveToCard(index);
  };

  const canScrollLeft = true; // 무한 순환으로 항상 스크롤 가능
  const canScrollRight = true; // 무한 순환으로 항상 스크롤 가능

  // 더보기 모달 핸들러
  const handleExpandCard = (cardId: string) => {
    setExpandedCard(cardId);
    document.body.style.overflow = 'hidden';
  };

  const handleCloseModal = () => {
    setExpandedCard(null);
    document.body.style.overflow = 'unset';
  };

  return (
    <div className="relative w-full" ref={containerRef}>
      {/* 왼쪽 화살표 */}
      <button
        onClick={handlePrevious}
        disabled={!canScrollLeft || isTransitioning}
        className={`absolute left-4 top-1/2 transform -translate-y-1/2 z-30
          bg-white bg-opacity-95 backdrop-blur-sm rounded-full p-4 shadow-xl transition-all duration-300
          ${canScrollLeft && !isTransitioning
            ? 'hover:shadow-2xl hover:bg-opacity-100 cursor-pointer opacity-100 hover:scale-110 hover:bg-purple-50'
            : 'opacity-30 cursor-not-allowed'
          }`}
        aria-label="이전 카드"
      >
        <svg className="w-6 h-6 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      {/* 오른쪽 화살표 */}
      <button
        onClick={handleNext}
        disabled={!canScrollRight || isTransitioning}
        className={`absolute right-4 top-1/2 transform -translate-y-1/2 z-30
          bg-white bg-opacity-95 backdrop-blur-sm rounded-full p-4 shadow-xl transition-all duration-300
          ${canScrollRight && !isTransitioning
            ? 'hover:shadow-2xl hover:bg-opacity-100 cursor-pointer opacity-100 hover:scale-110 hover:bg-purple-50'
            : 'opacity-30 cursor-not-allowed'
          }`}
        aria-label="다음 카드"
      >
        <svg className="w-6 h-6 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>

      {/* 카드 컨테이너 */}
      <div
        className="overflow-hidden"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        <div
          className="flex gpu-accelerated"
          style={{
            transform: `translateX(-${currentIndex * cardSpacing}px) translateZ(0)`,
            width: `${duplicatedCharacters.length * cardSpacing}px`,
            willChange: isTransitioning ? 'transform' : 'auto',
            backfaceVisibility: 'hidden',
            transition: isTransitioning ? 'transform 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)' : 'none',
            perspective: '1000px'
          }}
        >
          {duplicatedCharacters.map((character, index) => {
            const isCenter = index === centerIndex;
            const distanceFromCenter = Math.abs(index - centerIndex);

            return (
              <CharacterCardComponent
                key={`${character.id}-${index}`} // 고유 키 생성
                character={character}
                isLiked={likedCards.has(character.id)}
                onLike={() => onLike(character.id)}
                isCenter={isCenter}
                distanceFromCenter={distanceFromCenter}
                cardWidth={cardWidth}
                cardSpacing={cardSpacing}
                visibleCards={visibleCards}
                onExpand={handleExpandCard}
                isTransitioning={isTransitioning}
              />
            );
          })}
        </div>
      </div>

      {/* 인디케이터 도트 */}
      {characters.length > visibleCards && (
        <div className="flex justify-center mt-6 space-x-2">
          {characters.map((_, index) => {
            const isActive = index === actualCenterIndex;

            return (
              <button
                key={index}
                onClick={() => {
                  // 클릭한 카드가 중앙에 오도록 currentIndex 계산 (두 번째 세트 기준)
                  const targetIndex = characters.length + index;
                  const newCurrentIndex = Math.max(0, targetIndex - 2);
                  moveToCard(newCurrentIndex);
                }}
                className={`w-2 h-2 rounded-full transition-all duration-300 ${
                  isActive
                    ? 'bg-purple-600 scale-125'
                    : 'bg-gray-300 hover:bg-gray-400'
                }`}
                aria-label={`${index + 1}번 카드로 이동`}
              />
            );
          })}
        </div>
      )}

      {/* 더보기 모달 */}
      {expandedCard && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4" onClick={handleCloseModal}>
          <div className="bg-white rounded-3xl p-6 max-w-md w-full max-h-96 overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            {(() => {
              const character = characters.find(c => c.id === expandedCard);
              if (!character) return null;

              return (
                <>
                  <div className="flex justify-between items-start mb-4">
                    <h3 className="text-xl font-bold text-gray-800">{character.title}</h3>
                    <button
                      onClick={handleCloseModal}
                      className="text-gray-500 hover:text-gray-700 text-2xl"
                    >
                      ×
                    </button>
                  </div>

                  <div className="mb-4">
                    <img
                      src={character.image}
                      alt={character.title}
                      className="w-full h-48 object-cover rounded-2xl"
                    />
                  </div>

                  <div className="text-gray-700 text-sm leading-relaxed mb-4">
                    {character.description}
                  </div>

                  <div className="flex flex-wrap gap-2 mb-4">
                    {character.tags.map((tag, index) => (
                      <span key={index} className="text-xs bg-purple-100 text-purple-600 px-2 py-1 rounded-full">
                        {tag}
                      </span>
                    ))}
                  </div>

                  <div className="flex justify-center space-x-4 text-sm text-gray-600">
                    <div className="flex items-center space-x-1">
                      <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clipRule="evenodd" />
                      </svg>
                      <span>{character.likes + (likedCards.has(character.id) ? 1 : 0)}</span>
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
                </>
              );
            })()}
          </div>
        </div>
      )}
    </div>
  );
}

interface CharacterCardProps {
  character: CharacterCard;
  isLiked: boolean;
  onLike: () => void;
  isCenter: boolean;
  distanceFromCenter: number;
  cardWidth: number;
  cardSpacing: number;
  visibleCards: number;
  onExpand: (cardId: string) => void;
  isTransitioning: boolean;
}

function CharacterCardComponent({
  character,
  isLiked,
  onLike,
  isCenter,
  distanceFromCenter,
  cardWidth,
  cardSpacing,
  visibleCards,
  onExpand,
  isTransitioning
}: CharacterCardProps) {
  // 중앙 카드 확대 효과 및 거리별 스케일링
  const scale = isCenter ? 1.25 : Math.max(0.8, 1 - distanceFromCenter * 0.1);
  const opacity = visibleCards === 5 ? (distanceFromCenter === 0 ? 1 : Math.max(0.4, 1 - distanceFromCenter * 0.15)) : 1;
  const zIndex = isCenter ? 30 : Math.max(10, 20 - distanceFromCenter);

  // 텍스트 길이 체크 (더보기 버튼 표시 여부 결정)
  const maxLength = isCenter ? 120 : 80; // 중앙 카드는 더 긴 텍스트 허용
  const shouldShowReadMore = character.description.length > maxLength;

  return (
    <div
      className="flex justify-center items-center"
      style={{
        width: `${cardSpacing}px`,
        display: 'flex',
        justifyContent: 'center',
        position: 'relative',
        padding: '0 10px', // 카드 간 최소 여백
      }}
    >
      <Link to={character.link}>
        <div
          className={`
            rounded-[28px] cursor-pointer group relative
            bg-zeplin-card overflow-hidden gpu-accelerated
          `}
          style={{
            transform: `scale(${scale}) translateZ(0)`,
            opacity,
            zIndex,
            width: `${cardWidth}px`, // 실제 카드 크기
            height: isCenter ? '450px' : '380px', // 중앙 카드만 더 크게
            willChange: isTransitioning ? 'transform, opacity' : 'auto',
            backfaceVisibility: 'hidden',
            perspective: '1000px',
            boxShadow: isCenter
              ? '0 20px 40px rgba(0, 0, 0, 0.3), 0 10px 20px rgba(0, 0, 0, 0.15)'
              : '0 10px 20px rgba(0, 0, 0, 0.2)',
            transition: 'all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)'
          }}
          onMouseEnter={(e) => {
            if (!isTransitioning) {
              e.currentTarget.style.transform = `scale(${scale * 1.05}) translateZ(0)`;
            }
          }}
          onMouseLeave={(e) => {
            if (!isTransitioning) {
              e.currentTarget.style.transform = `scale(${scale}) translateZ(0)`;
            }
          }}
        >
          {/* 캐릭터 이미지 */}
          <div className="relative overflow-hidden rounded-t-[28px]"
               style={{
                 height: isCenter ? '300px' : '240px'
               }}>
            <img
              src={character.image}
              alt={character.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-400 ease-in-out"
              draggable={false}
            />
          </div>

          {/* 카드 내용 - 개선된 구조 */}
          <div className="p-4 flex flex-col justify-between" style={{
            height: isCenter ? '150px' : '140px'
          }}>
            {/* 제목 영역 */}
            <div className="text-center mb-2">
              <h3 className="font-bold font-inter text-xs text-black leading-tight">
                {character.title}
              </h3>
            </div>

            {/* 설명 영역 - 확장 */}
            <div className="flex-grow text-center mb-3">
              <p className="text-black font-inter text-xs leading-relaxed"
                 style={{
                   display: '-webkit-box',
                   WebkitLineClamp: isCenter ? 6 : 4,
                   WebkitBoxOrient: 'vertical',
                   overflow: 'hidden'
                 }}>
                {character.description}
              </p>
              {shouldShowReadMore && (
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onExpand(character.id);
                  }}
                  className="mt-2 text-purple-600 text-xs hover:text-purple-800 transition-colors duration-200"
                >
                  더보기
                </button>
              )}
            </div>

            {/* 해시태그 영역 */}
            <div className="text-center mb-2">
              <div className="text-black font-inter text-xs opacity-70">
                {character.tags.join(' ')}
              </div>
            </div>
          </div>

          {/* 상호작용 지표 - Zeplin 스타일 */}
          <div className="absolute bottom-2 left-1/2 transform -translate-x-1/2">
            <div className="bg-white rounded-full px-3 py-1 shadow-md flex items-center space-x-2">
              {/* 좋아요 버튼 */}
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onLike();
                }}
                className="flex items-center space-x-1"
              >
                <svg
                  className={`w-3.5 h-3.5 ${isLiked ? 'text-red-500 fill-current' : 'text-gray-600'}`}
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
                <span className="text-xs font-inter text-black">
                  {character.likes + (isLiked ? 1 : 0)}
                </span>
              </button>

              {/* 댓글 수 */}
              <div className="flex items-center space-x-1">
                <svg className="w-3.5 h-3.5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <span className="text-xs font-inter text-black">{character.comments}</span>
              </div>

              {/* 조회수 */}
              <div className="flex items-center space-x-1">
                <svg className="w-3.5 h-3.5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                <span className="text-xs font-inter text-black">{character.views}</span>
              </div>
            </div>
          </div>
        </div>
      </Link>
    </div>
  );
}