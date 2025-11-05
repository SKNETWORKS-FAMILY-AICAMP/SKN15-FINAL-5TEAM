import { useParams, Link, useNavigate } from 'react-router-dom';
import { useMemo, useState } from 'react';
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

const SCENARIO_ID_MAP: Record<string, string> = {
  train: 'cutscene5_llm_driven',
  ending: 'cutscene5_llm_driven',
  cutscene5_llm_driven: 'cutscene5_llm_driven'
};

const detailTexture =
  'linear-gradient(145deg, rgba(108,92,231,0.14) 0%, rgba(255,126,182,0.12) 50%, rgba(255,255,255,0.18) 100%)';

const TAG_BADGE_STYLES = {
  intense: 'bg-gradient-to-r from-[#fbe4e7] via-[#f7c6d1] to-[#fbe4e7] border-[#f59aae]/45 text-[#c81e63] shadow-[0_0_22px_rgba(240,82,82,0.12)]',
  noble: 'bg-gradient-to-r from-[#f4ecff] via-[#e1d5ff] to-[#f4ecff] border-[#c4b5fd]/45 text-[#4c1d95] shadow-[0_0_22px_rgba(147,51,234,0.12)]',
  serene: 'bg-gradient-to-r from-[#e7f0ff] via-[#d6e6ff] to-[#e7f0ff] border-[#93c5fd]/45 text-[#1d4ed8] shadow-[0_0_22px_rgba(59,130,246,0.12)]'
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

export default function CharacterPage() {
  const { characterId } = useParams<{ characterId: string }>();
  const { toggleSidebar, openSettings } = useApp();
  const navigate = useNavigate();
  const [isLiked, setIsLiked] = useState(false);
  const [detailExpanded, setDetailExpanded] = useState(false);

  const scenarios = scenariosData as Record<string, ScenarioData>;
  const scenarioLookupKey =
    characterId && !scenarios[characterId]
      ? SCENARIO_ID_MAP[characterId] || characterId
      : characterId || null;
  const scenario = scenarioLookupKey ? scenarios[scenarioLookupKey] : null;

  if (!scenario) {
    return (
      <div className="min-h-screen bg-[#f5f2ff] text-theme-primary">
        <ChatHeader
          onToggleSidebar={toggleSidebar}
          onOpenSettings={openSettings}
          title="알 수 없는 시나리오"
          showBackButton={true}
          titleClassName="font-display-main text-theme-primary"
        />
        <main className="min-h-[calc(100vh-64px)] flex items-center justify-center">
          <div className="text-center card-surface p-10 rounded-3xl max-w-md">
            <div className="text-6xl mb-6">❓</div>
            <h1 className="text-3xl font-hero-mincho mb-4 text-theme-primary">존재하지 않는 시나리오</h1>
            <p className="text-theme-secondary mb-6">요청하신 시나리오를 찾을 수 없습니다.</p>
            <Link
              to="/"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-gradient-to-r from-[#2f1d83] via-[#4331c5] to-[#7a1fb9] text-white font-semibold tracking-wide transition-transform hover:scale-[1.02] hover:shadow-[0_16px_32px_rgba(67,49,197,0.35)]"
            >
              홈으로 돌아가기
            </Link>
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
    setIsLiked((prev) => !prev);
  };

  const likeCount = scenario.likes + (isLiked ? 1 : 0);

  const stats = useMemo(
    () => [
      {
        label: '좋아요',
        value: likeCount.toLocaleString('ko-KR'),
        icon: '❤️',
        highlightClass: 'text-rose-500',
        isInteractive: true
      },
      {
        label: '댓글',
        value: scenario.comments.toLocaleString('ko-KR'),
        icon: '💬',
        highlightClass: 'text-sky-500'
      },
      {
        label: '조회수',
        value: scenario.views.toLocaleString('ko-KR'),
        icon: '👁️',
        highlightClass: 'text-amber-500'
      }
    ],
    [scenario.comments, scenario.views, likeCount]
  );

  const detailText = scenario.detailDescription || scenario.description;
  const detailShouldToggle = detailText.length > 260;

  return (
    <div className="min-h-screen bg-[#f5f2ff] text-theme-primary">
      <ChatHeader
        onToggleSidebar={toggleSidebar}
        onOpenSettings={openSettings}
        title="KIME CHAT"
        showBackButton={true}
        titleClassName="font-display-main text-theme-primary"
      />

      <main className="min-h-[calc(100vh-64px)] overflow-y-auto bg-[radial-gradient(circle_at_top,_rgba(108,92,231,0.12)_0%,transparent_65%)]">
        <div className="max-w-6xl mx-auto px-4 md:px-6 py-8 md:py-12 space-y-8">
          <section className="relative rounded-[36px] card-surface overflow-hidden">
            <div className="grid md:grid-cols-[1fr_1.2fr] gap-0">
              <div className="relative min-h-[320px] md:min-h-[420px]">
                <img
                  src={scenario.image}
                  alt={scenario.title}
                  className="absolute inset-0 w-full h-full object-cover object-center"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-white/85 via-white/35 to-transparent" />
                <div className="absolute inset-0 bg-gradient-to-br from-[#6c5ce7]/25 via-transparent to-[#ff7eb6]/20 mix-blend-screen" />
                <div className="absolute top-5 left-5 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-theme-surface border border-theme-card backdrop-blur-md text-xs font-semibold uppercase tracking-[0.15em] text-theme-primary">
                  Scenario
                </div>
                <div className="absolute top-5 right-5">
                  <Link
                    to="/"
                    className="inline-flex items-center justify-center rounded-full bg-white/70 border border-theme-card text-theme-primary hover:bg-white transition-colors w-10 h-10"
                    aria-label="홈으로 이동"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                  </Link>
                </div>
                <div className="absolute bottom-6 left-6 right-6 flex flex-wrap gap-2">
                  {scenario.tags.map((tag, index) => (
                    <span
                      key={`${tag}-${index}`}
                      className={`px-3 py-1 rounded-full text-[11px] border ${getTagBadgeTone(tag)}`}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              <div className="p-8 md:p-12 flex flex-col gap-8">
                <div className="space-y-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-theme-secondary">Story</p>
                  <h1 className="text-3xl md:text-[38px] font-hero-mincho text-theme-primary leading-tight drop-shadow-[0_10px_26px_rgba(108,92,231,0.2)]">
                    {scenario.title}
                  </h1>
                  <p className="text-theme-secondary text-base leading-relaxed">
                    {scenario.description}
                  </p>
                </div>

                {scenario.mood && scenario.mood.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {scenario.mood.map((mood, index) => (
                      <span
                        key={`${mood}-${index}`}
                        className="px-3 py-1 rounded-full chip-soft text-xs tracking-[0.1em] uppercase"
                      >
                        {mood}
                      </span>
                    ))}
                  </div>
                )}

                <div className="grid sm:grid-cols-3 gap-3">
                  {stats.map((stat) => {
                    const content = (
                      <>
                        <span className="text-xs uppercase tracking-[0.15em] text-theme-secondary block">{stat.label}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{stat.icon}</span>
                          <span className={`text-2xl font-semibold ${stat.highlightClass}`}>
                            {stat.value}
                          </span>
                        </div>
                      </>
                    );

                    if ((stat as { isInteractive?: boolean }).isInteractive) {
                      return (
                        <button
                          type="button"
                          key={stat.label}
                          onClick={handleLike}
                          className="relative overflow-hidden rounded-2xl card-surface px-4 py-5 flex flex-col items-start gap-2 text-left transition-transform duration-200 hover:-translate-y-1 focus:outline-none focus:ring-2 focus:ring-[rgba(108,92,231,0.35)]"
                        >
                          {content}
                          {isLiked && (
                            <span className="absolute top-3 right-3 text-[10px] uppercase tracking-[0.15em] text-rose-500/80">
                              Liked
                            </span>
                          )}
                        </button>
                      );
                    }

                    return (
                      <div
                        key={stat.label}
                        className="relative overflow-hidden rounded-2xl card-surface px-4 py-5 flex flex-col items-start gap-2 text-left"
                      >
                        {content}
                      </div>
                    );
                  })}
                </div>

                <div className="flex flex-col sm:flex-row gap-3 pt-2">
                  <button
                    onClick={handleStartChat}
                    className="flex-1 inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-[#2f1d83] via-[#4331c5] to-[#7a1fb9] py-4 text-white font-semibold text-base tracking-wide shadow-[0_18px_40px_rgba(47,29,131,0.35)] transition-transform hover:scale-[1.01] hover:shadow-[0_22px_48px_rgba(67,49,197,0.4)]"
                  >
                    <span>이 시나리오로 대화 시작</span>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                    </svg>
                  </button>
                  <Link
                    to="/"
                    className="flex-1 inline-flex items-center justify-center gap-2 rounded-2xl border border-theme-card bg-theme-surface py-4 text-theme-primary tracking-wide transition-colors hover:bg-theme-surface-strong"
                  >
                    홈으로 돌아가기
                  </Link>
                </div>
              </div>
            </div>
          </section>

          <section className="grid gap-6 md:grid-cols-[1.25fr_0.85fr]">
            <div
              className="relative overflow-hidden rounded-3xl card-surface p-8"
              style={{ backgroundImage: detailTexture }}
            >
              <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_top,rgba(108,92,231,0.18),transparent_60%),radial-gradient(circle_at_bottom,rgba(255,126,182,0.18),transparent_55%)] pointer-events-none" />
              <div className="relative space-y-5">
                <div>
                  <h2 className="text-xl font-hero-mincho text-theme-primary mb-1">시나리오 개요</h2>
                  <p className="text-xs uppercase tracking-[0.15em] text-theme-secondary">Summary Scroll</p>
                </div>
                <p
                  className="text-sm leading-relaxed text-theme-secondary"
                  style={{
                    display: '-webkit-box',
                    WebkitLineClamp: !detailExpanded && detailShouldToggle ? 7 : undefined,
                    WebkitBoxOrient: 'vertical',
                    overflow: detailShouldToggle && !detailExpanded ? 'hidden' : 'visible'
                  }}
                >
                  {detailText}
                </p>
                {detailShouldToggle && (
                  <button
                    onClick={() => setDetailExpanded((prev) => !prev)}
                    className="text-xs uppercase tracking-[0.15em] text-theme-primary hover:text-[#ff7eb6] transition-colors"
                  >
                    {detailExpanded ? '접기 ▲' : '자세히 보기 ▾'}
                  </button>
                )}
              </div>
            </div>

            <div className="rounded-3xl card-surface p-8 space-y-6">
              <div>
                <h2 className="text-xl font-hero-mincho text-theme-primary mb-1">시나리오 정보</h2>
                <p className="text-xs uppercase tracking-[0.18em] text-theme-secondary">Overview</p>
              </div>
              <div className="space-y-5 text-sm text-theme-secondary">
                <div>
                  <span className="text-xs uppercase tracking-[0.15em] text-theme-secondary">카테고리</span>
                  <p className="mt-1 text-base text-theme-primary font-medium">{scenario.category}</p>
                </div>
                <div>
                  <span className="text-xs uppercase tracking-[0.15em] text-theme-secondary">유형</span>
                  <p className="mt-1 text-base text-theme-primary font-medium">{scenario.type}</p>
                </div>
                <div>
                  <span className="text-xs uppercase tracking-[0.15em] text-theme-secondary">상태</span>
                  <p className="mt-1 text-base text-theme-primary font-medium">
                    {scenario.implemented ? '플레이 가능' : '준비 중'}
                  </p>
                </div>
                {scenario.mood && scenario.mood.length > 0 && (
                  <div>
                    <span className="text-xs uppercase tracking-[0.15em] text-theme-secondary block mb-2">분위기</span>
                    <div className="flex flex-wrap gap-2">
                      {scenario.mood.map((mood, index) => (
                        <span
                          key={`mood-chip-${mood}-${index}`}
                          className="px-3 py-1 rounded-full chip-soft text-xs tracking-[0.1em] uppercase"
                        >
                          {mood}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </section>

          {scenario.characters && scenario.characters.length > 0 && (
            <section className="rounded-[32px] card-surface p-8 space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-hero-mincho text-theme-primary">등장 인물</h2>
                  <p className="text-xs uppercase tracking-[0.15em] text-theme-secondary mt-1">
                    Allies & Rivals
                  </p>
                </div>
                <span className="text-[11px] uppercase tracking-[0.18em] text-theme-secondary">
                  {scenario.characters.length}명
                </span>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                {scenario.characters.map((chara, index) => (
                  <div
                    key={`${chara.name}-${index}`}
                    className="relative overflow-hidden rounded-2xl card-surface p-5 flex gap-4 transition-transform hover:-translate-y-1"
                  >
                    <div className="relative w-16 h-16 rounded-2xl overflow-hidden flex-shrink-0 ring-2 ring-[rgba(108,92,231,0.2)]">
                      <img
                        src={chara.image}
                        alt={chara.name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div className="flex-1 min-w-0 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <h3 className="text-lg font-hero-mincho text-theme-primary leading-tight">{chara.name}</h3>
                        <span className="text-[10px] uppercase tracking-[0.15em] text-theme-secondary">
                          {chara.status}
                        </span>
                      </div>
                      <p className="text-sm text-theme-secondary leading-relaxed">
                        {chara.greeting}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}
