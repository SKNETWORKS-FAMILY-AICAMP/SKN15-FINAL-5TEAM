import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
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

const MAX_CENTER_SCALE = 1.15;
const MIN_SIDE_SCALE = 0.85;

export default function CharacterCarousel({ characters, likedCards, onLike }: CharacterCarouselProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [currentIndex, setCurrentIndex] = useState(characters.length); // 복제된 카드들 고려
  const [containerWidth, setContainerWidth] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [expandedCard, setExpandedCard] = useState<string | null>(null);

  // 무한 순환을 위한 복제된 카드 배열 생성
  const duplicatedCharacters = useMemo(() => ([
    ...characters, // 앞쪽 복제
    ...characters, // 원본
    ...characters  // 뒤쪽 복제
  ]), [characters]);

  // 반응형 설정
  const getVisibleCards = useCallback(() => {
    if (containerWidth < 480) return 1; // 작은 모바일 (480px 미만)
    if (containerWidth < 768) return 1; // 모바일 (480px-767px)
    if (containerWidth < 1024) return 3; // 태블릿 (768px-1023px)
    if (containerWidth < 1280) return 5; // 작은 데스크톱 (1024px-1279px)
    return 5; // 큰 데스크톱 (1280px 이상)
  }, [containerWidth]);

  const visibleCards = getVisibleCards();
  const slotWidth = visibleCards > 0 ? containerWidth / visibleCards : containerWidth;
  const cardSpacing = slotWidth || 0;
  const cardWidth = cardSpacing * 0.8; // 최대 스케일 적용 시에도 프레임 내에 유지

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

  // 길이가 변하면 중앙 인덱스 재정렬
  useEffect(() => {
    if (characters.length === 0) {
      setCurrentIndex(0);
      return;
    }
    setCurrentIndex(characters.length);
  }, [characters.length, visibleCards]);

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
  };

  const handleCloseModal = () => {
    setExpandedCard(null);
  };

  useEffect(() => {
    if (expandedCard) {
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = originalOverflow || '';
      };
    }

    document.body.style.overflow = '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [expandedCard]);

  return (
    <div className="relative w-full" ref={containerRef}>
      {/* 왼쪽 화살표 */}
      <button
        onClick={handlePrevious}
        disabled={!canScrollLeft || isTransitioning}
        className={`absolute left-4 top-1/2 transform -translate-y-1/2 z-30
          bg-theme-surface-strong rounded-full p-4 shadow-theme border border-theme-card transition-all duration-300
          ${canScrollLeft && !isTransitioning
            ? 'cursor-pointer opacity-100 hover:scale-110'
            : 'opacity-30 cursor-not-allowed'
          }`}
        aria-label="이전 카드"
      >
        <svg className="w-6 h-6 text-theme-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      {/* 오른쪽 화살표 */}
      <button
        onClick={handleNext}
        disabled={!canScrollRight || isTransitioning}
        className={`absolute right-4 top-1/2 transform -translate-y-1/2 z-30
          bg-theme-surface-strong rounded-full p-4 shadow-theme border border-theme-card transition-all duration-300
          ${canScrollRight && !isTransitioning
            ? 'cursor-pointer opacity-100 hover:scale-110'
            : 'opacity-30 cursor-not-allowed'
          }`}
        aria-label="다음 카드"
      >
        <svg className="w-6 h-6 text-theme-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>

      {/* 카드 컨테이너 */}
      <div
        className="overflow-hidden"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        style={{ padding: '32px 0' }}
      >
        <div
          className="flex gpu-accelerated"
          style={{
            transform: `translateX(-${currentIndex * cardSpacing}px) translateZ(0)`,
            width: `${duplicatedCharacters.length * cardSpacing}px`,
            willChange: isTransitioning ? 'transform' : 'auto',
            backfaceVisibility: 'hidden',
            transition: isTransitioning ? 'transform 0.45s cubic-bezier(0.25, 0.46, 0.45, 0.94)' : 'none',
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
                    ? 'bg-gradient-to-r from-purple-500 to-pink-500 scale-125 shadow-theme'
                    : 'bg-theme-surface border border-theme-card hover:bg-theme-surface-strong'
                }`}
                aria-label={`${index + 1}번 카드로 이동`}
              />
            );
          })}
        </div>
      )}

      {/* 더보기 모달 */}
      {expandedCard && (
        <div className="fixed inset-0 bg-black/65 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={handleCloseModal}>
          {(() => {
            const character = characters.find(c => c.id === expandedCard);
            if (!character) return null;

            return (
              <ScenarioDetailModal
                character={character}
                isLiked={likedCards.has(character.id)}
                onClose={handleCloseModal}
              />
            );
          })()}
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
  const scale = isCenter ? MAX_CENTER_SCALE : Math.max(MIN_SIDE_SCALE, 1 - distanceFromCenter * 0.08);
  const opacity = visibleCards === 5 ? (distanceFromCenter === 0 ? 1 : Math.max(0.45, 1 - distanceFromCenter * 0.12)) : 1;
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
            bg-theme-surface-strong border border-theme-card overflow-hidden gpu-accelerated
          `}
          style={{
            transform: `scale(${scale}) translateZ(0)`,
            opacity,
            zIndex,
            width: `${cardWidth}px`, // 실제 카드 크기
            height: isCenter ? '470px' : '405px', // 중앙 카드만 더 크게
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
          <div
            className="relative overflow-hidden rounded-t-[28px] bg-gradient-to-b from-[#1a0b2e] via-[#0f061d] to-[#1a0b2e]"
            style={{
              height: isCenter ? '300px' : '240px',
            }}
          >
            <div
              className="absolute inset-0 -z-10 blur-2xl scale-110 opacity-65"
              style={{
                backgroundImage: `url('${character.image}')`,
                backgroundSize: 'cover',
                backgroundPosition: 'center'
              }}
            />
            <img
              src={character.image}
              alt={character.title}
              className="relative z-10 w-full h-full object-cover transition-transform duration-400 ease-in-out group-hover:scale-110"
              draggable={false}
              style={{ transformOrigin: 'center' }}
            />
          </div>

          {/* 카드 내용 - 개선된 구조 */}
          <div
            className="p-4 flex flex-col justify-between"
            style={{
              minHeight: isCenter ? '180px' : '160px',
              paddingBottom: isCenter ? '56px' : '52px'
            }}
          >
            {/* 제목 영역 */}
            <div className="text-center mb-2">
              <h3 className="font-bold font-inter text-xs text-theme-primary leading-tight">
                {character.title}
              </h3>
            </div>

            {/* 설명 영역 - 확장 */}
            <div className="flex-grow text-center mb-3">
              <p className="text-theme-secondary font-inter text-xs leading-relaxed"
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
              <div className="text-theme-secondary font-inter text-xs opacity-80">
                {character.tags.join(' ')}
              </div>
            </div>
          </div>

          {/* 상호작용 지표 - Zeplin 스타일 */}
          <div className="absolute bottom-2 left-1/2 transform -translate-x-1/2">
            <div className="bg-theme-surface rounded-full px-3 py-1 shadow-theme flex items-center space-x-2 border border-theme-card">
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
                  className={`w-3.5 h-3.5 ${isLiked ? 'text-red-500 fill-current' : 'text-theme-secondary'}`}
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
                <span className="text-xs font-inter text-theme-primary">
                  {character.likes}
                </span>
              </button>

              {/* 댓글 수 */}
              <div className="flex items-center space-x-1">
                <svg className="w-3.5 h-3.5 text-theme-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <span className="text-xs font-inter text-theme-primary">{character.comments}</span>
              </div>

              {/* 조회수 */}
              <div className="flex items-center space-x-1">
                <svg className="w-3.5 h-3.5 text-theme-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                <span className="text-xs font-inter text-theme-primary">{character.views}</span>
              </div>
            </div>
          </div>
        </div>
      </Link>
    </div>
  );
}

interface ScenarioDetailModalProps {
  character: CharacterCard;
  onClose: () => void;
  isLiked: boolean;
}

const summaryTexture = 'linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(148, 163, 184, 0.05) 50%, rgba(15, 23, 42, 0.08) 100%)';

function ScenarioDetailModal({ character, onClose, isLiked }: ScenarioDetailModalProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const descriptionShouldToggle = character.description.length > 160;

  const stats = useMemo(() => [
    {
      label: '좋아요',
      value: character.likes.toLocaleString('ko-KR'),
      icon: '❤️',
      accent: 'from-rose-500/25 via-orange-500/10 to-amber-400/10',
      textClass: 'text-rose-100',
      glow: 'shadow-[0_0_35px_rgba(244,63,94,0.25)]',
      isHighlighted: isLiked
    },
    {
      label: '댓글',
      value: character.comments.toLocaleString('ko-KR'),
      icon: '💬',
      accent: 'from-sky-500/25 via-cyan-500/15 to-emerald-400/10',
      textClass: 'text-sky-100',
      glow: 'shadow-[0_0_35px_rgba(56,189,248,0.25)]'
    },
    {
      label: '조회수',
      value: character.views.toLocaleString('ko-KR'),
      icon: '👁️',
      accent: 'from-amber-400/25 via-yellow-500/15 to-fuchsia-500/10',
      textClass: 'text-amber-100',
      glow: 'shadow-[0_0_35px_rgba(251,191,36,0.18)]'
    }
  ], [character.comments, character.likes, character.views, isLiked]);

  return (
    <div className="relative w-full max-w-4xl text-slate-100 animate-scroll-unfurl" onClick={(e) => e.stopPropagation()}>
      <button
        onClick={onClose}
        className="absolute top-4 right-4 text-slate-300 hover:text-white text-3xl font-semibold transition-transform hover:scale-110 z-10"
        aria-label="모달 닫기"
      >
        ×
      </button>

      <div className="grid gap-6 md:grid-cols-[0.9fr_1.25fr] rounded-[32px] border border-white/10 bg-[#120f1f]/95 backdrop-blur-xl shadow-[0_40px_120px_rgba(10,8,25,0.65)] overflow-hidden">
        <div className="relative min-h-[320px]">
          <img
            src={character.image}
            alt={character.title}
            className="absolute inset-0 w-full h-full object-cover object-center scale-105"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/25 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 via-transparent to-sky-500/15 mix-blend-screen" />

          <div className="absolute top-5 left-5 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/20 backdrop-blur-md text-xs font-semibold uppercase tracking-[0.15em] text-slate-200">
            Scenario
          </div>

          <div className="absolute bottom-5 left-5 right-5 flex flex-wrap gap-2">
            {character.tags.map((tag, index) => (
              <span
                key={`${tag}-${index}`}
                className={`px-3 py-1 rounded-full text-[11px] border ${getTagBadgeTone(tag)}`}
              >
                {tag}
              </span>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-6 p-6 md:p-8">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-purple-200/70 mb-3">Story</p>
            <h3 className="text-3xl md:text-[34px] font-hero-mincho text-white leading-tight drop-shadow-[0_8px_24px_rgba(168,85,247,0.35)]">
              {character.title}
            </h3>
          </div>

          <div
            className="rounded-3xl border border-white/10 shadow-inner shadow-black/30 p-6 relative overflow-hidden"
            style={{ backgroundImage: summaryTexture }}
          >
            <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_top,rgba(248,113,113,0.18),transparent_60%),radial-gradient(circle_at_bottom,rgba(56,189,248,0.18),transparent_55%)] pointer-events-none" />
            <p
              className="relative text-sm leading-relaxed text-slate-100/90"
              style={{
                display: '-webkit-box',
                WebkitLineClamp: !isExpanded && descriptionShouldToggle ? 5 : undefined,
                WebkitBoxOrient: 'vertical',
                overflow: descriptionShouldToggle && !isExpanded ? 'hidden' : 'visible'
              }}
            >
              {character.description}
            </p>
            {descriptionShouldToggle && (
              <button
                onClick={() => setIsExpanded(prev => !prev)}
                className="relative mt-4 inline-flex items-center text-xs tracking-[0.12em] uppercase text-purple-200 hover:text-white transition-colors"
              >
                {isExpanded ? '접기 ▲' : '자세히 보기 ▾'}
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {stats.map(stat => (
              <div
                key={stat.label}
                className={`relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br ${stat.accent} px-4 py-5 flex flex-col gap-1 transition-transform duration-200 ${stat.glow} hover:-translate-y-1`}
              >
                <span className="text-xs uppercase tracking-[0.2em] text-white/60">{stat.label}</span>
                <div className="flex items-baseline gap-2">
                  <span className="text-lg">{stat.icon}</span>
                  <span className={`text-2xl font-semibold ${stat.textClass}`}>
                    {stat.value}
                  </span>
                </div>
                {stat.isHighlighted && (
                  <span className="text-[10px] text-rose-200/70 tracking-[0.15em] uppercase">
                    Liked
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

const TAG_BADGE_STYLES = {
  intense: 'bg-gradient-to-r from-rose-200/80 via-rose-100/60 to-orange-100/60 border-rose-200/50 text-rose-700 shadow-[0_0_18px_rgba(244,63,94,0.18)]',
  noble: 'bg-gradient-to-r from-indigo-200/80 via-violet-100/60 to-indigo-100/60 border-violet-200/50 text-indigo-700 shadow-[0_0_18px_rgba(129,140,248,0.18)]',
  serene: 'bg-gradient-to-r from-sky-200/80 via-blue-100/60 to-sky-100/60 border-sky-200/50 text-sky-700 shadow-[0_0_18px_rgba(96,165,250,0.18)]'
} as const;

function getTagBadgeTone(tag: string) {
  const normalized = tag.toLowerCase();

  if (normalized.includes('혈귀') || normalized.includes('전투') || normalized.includes('전쟁')) {
    return TAG_BADGE_STYLES.intense;
  }

  if (
    normalized.includes('주') ||
    normalized.includes('柱') ||
    normalized.includes('영웅') ||
    normalized.includes('필') ||
    normalized.includes('수련') ||
    normalized.includes('훈련') ||
    normalized.includes('성장')
  ) {
    return TAG_BADGE_STYLES.noble;
  }

  if (normalized.includes('감동') || normalized.includes('힐링') || normalized.includes('스토리') || normalized.includes('우정')) {
    return TAG_BADGE_STYLES.serene;
  }

  return TAG_BADGE_STYLES.serene;
}
