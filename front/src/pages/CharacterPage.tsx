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

const TAG_BADGE_STYLES = {
  intense:
    'bg-gradient-to-r from-rose-500/25 via-rose-500/10 to-transparent border border-rose-400/35 text-rose-100 shadow-[0_0_25px_rgba(244,63,94,0.25)]',
  noble:
    'bg-gradient-to-r from-indigo-500/25 via-purple-500/15 to-transparent border border-indigo-400/35 text-indigo-100 shadow-[0_0_25px_rgba(99,102,241,0.25)]',
  serene:
    'bg-gradient-to-r from-sky-500/25 via-cyan-500/15 to-transparent border border-sky-400/30 text-sky-100 shadow-[0_0_25px_rgba(56,189,248,0.25)]'
} as const;

const detailTexture =
  'linear-gradient(160deg, rgba(88,28,135,0.35) 0%, rgba(30,64,175,0.22) 55%, rgba(15,23,42,0.65) 100%)';

const PRIMARY_PANEL =
  'bg-[#120b24]/85 border border-white/10 shadow-[0_32px_90px_rgba(6,3,18,0.65)] backdrop-blur-2xl';
const SECONDARY_PANEL =
  'bg-[#0c0719]/85 border border-white/10 shadow-[0_26px_80px_rgba(5,2,14,0.6)] backdrop-blur-2xl';
const TERTIARY_PANEL =
  'bg-[#0b0715]/80 border border-white/10 shadow-[0_20px_70px_rgba(5,2,15,0.55)] backdrop-blur-2xl';
const CHIP_CLASS =
  'px-3 py-1 rounded-full border border-white/15 bg-white/5 text-xs tracking-[0.1em] uppercase text-slate-200';

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
  const scenario = characterId ? scenarios[characterId] : null;

  if (!scenario) {
    return (
      <div className="min-h-screen bg-[#04010f] text-slate-100">
        <ChatHeader
          onToggleSidebar={toggleSidebar}
          onOpenSettings={openSettings}
          title="알 수 없는 시나리오"
          showBackButton={true}
          variant="dark"
          className="border-white/10 shadow-[0_18px_60px_rgba(4,1,12,0.55)]"
          titleClassName="font-display-main tracking-[0.2em]"
        />
        <main className="min-h-[calc(100vh-64px)] flex items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(88,28,135,0.35)_0%,transparent_65%)]">
          <div className={`text-center p-10 rounded-3xl max-w-md space-y-4 ${PRIMARY_PANEL}`}>
            <div className="text-6xl mb-2">❓</div>
            <h1 className="text-3xl font-hero-mincho text-white">존재하지 않는 시나리오</h1>
            <p className="text-slate-300">요청하신 시나리오를 찾을 수 없습니다.</p>
            <Link
              to="/"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 text-white font-semibold tracking-wide transition-transform hover:scale-[1.03] hover:shadow-[0_18px_36px_rgba(99,102,241,0.45)]"
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
        highlightClass: 'text-rose-200 drop-shadow-[0_0_18px_rgba(244,63,94,0.45)]',
        isInteractive: true
      },
      {
        label: '댓글',
        value: scenario.comments.toLocaleString('ko-KR'),
        icon: '💬',
        highlightClass: 'text-sky-200 drop-shadow-[0_0_18px_rgba(125,211,252,0.4)]'
      },
      {
        label: '조회수',
        value: scenario.views.toLocaleString('ko-KR'),
        icon: '👁️',
        highlightClass: 'text-amber-200 drop-shadow-[0_0_20px_rgba(251,191,36,0.4)]'
      }
    ],
    [scenario.comments, scenario.views, likeCount]
  );

  const detailText = scenario.detailDescription || scenario.description;
 const detailShouldToggle = detailText.length > 260;

  return (
    <div className="min-h-screen bg-[#04010f] text-slate-100">
      <ChatHeader
        onToggleSidebar={toggleSidebar}
        onOpenSettings={openSettings}
        title="KIME CHAT"
        showBackButton={true}
        titleClassName="font-display-main text-theme-primary"
      />

      <main className="min-h-[calc(100vh-64px)] overflow-y-auto bg-[radial-gradient(circle_at_top,_rgba(88,28,135,0.35)_0%,transparent_65%)]">
        <div className="max-w-6xl mx-auto px-4 md:px-6 py-8 md:py-12 space-y-8">
          <section className={`relative rounded-[36px] overflow-hidden ${PRIMARY_PANEL}`}>
            <div className="grid md:grid-cols-[1fr_1.2fr] gap-0">
              <div className="relative min-h-[320px] md:min-h-[420px]">
                <img
                  src={scenario.image}
                  alt={scenario.title}
                  className="absolute inset-0 w-full h-full object-cover object-center"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-[#05010d]/85 via-[#05010d]/25 to-transparent" />
                <div className="absolute inset-0 bg-gradient-to-br from-purple-600/20 via-transparent to-sky-500/20 mix-blend-screen" />
                <div className={`absolute top-5 left-5 inline-flex items-center gap-2 ${CHIP_CLASS}`}>
                  Scenario
                </div>
                <div className="absolute top-5 right-5">
                  <Link
                    to="/"
                    className="inline-flex items-center justify-center rounded-full bg-white/10 border border-white/15 text-slate-100 hover:bg-white/20 transition-colors w-10 h-10"
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
                      className={`text-[11px] ${getTagBadgeTone(tag)}`}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              <div className="p-8 md:p-12 flex flex-col gap-8">
                <div className="space-y-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-indigo-200/70">Story</p>
                  <h1 className="text-3xl md:text-[38px] font-hero-mincho text-white leading-tight drop-shadow-[0_15px_32px_rgba(129,140,248,0.45)]">
                    {scenario.title}
                  </h1>
                  <p className="text-slate-300 text-base leading-relaxed">
                    {scenario.description}
                  </p>
                </div>

                {scenario.mood && scenario.mood.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {scenario.mood.map((mood, index) => (
                      <span
                        key={`${mood}-${index}`}
                        className={`${CHIP_CLASS} text-[11px]`}
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
                        <span className="text-xs uppercase tracking-[0.15em] text-slate-300 block">{stat.label}</span>
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
                          className={`relative overflow-hidden rounded-2xl px-4 py-5 flex flex-col items-start gap-2 text-left transition-transform duration-200 hover:-translate-y-1 focus:outline-none focus:ring-2 focus:ring-purple-500/40 ${SECONDARY_PANEL}`}
                        >
                          {content}
                          {isLiked && (
                            <span className="absolute top-3 right-3 text-[10px] uppercase tracking-[0.15em] text-rose-300">
                              Liked
                            </span>
                          )}
                        </button>
                      );
                    }

                    return (
                      <div
                        key={stat.label}
                        className={`relative overflow-hidden rounded-2xl px-4 py-5 flex flex-col items-start gap-2 text-left ${SECONDARY_PANEL}`}
                      >
                        {content}
                      </div>
                    );
                  })}
                </div>

                <div className="flex flex-col sm:flex-row gap-3 pt-2">
                  <button
                    onClick={handleStartChat}
                    className="flex-1 inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 py-4 text-white font-semibold text-base tracking-wide shadow-[0_22px_52px_rgba(129,140,248,0.45)] transition-transform hover:scale-[1.02] hover:shadow-[0_26px_60px_rgba(236,72,153,0.5)]"
                  >
                    <span>이 시나리오로 대화 시작</span>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                    </svg>
                  </button>
                  <Link
                    to="/"
                    className="flex-1 inline-flex items-center justify-center gap-2 rounded-2xl border border-white/15 bg-white/5 py-4 text-slate-100 tracking-wide transition-colors hover:bg-white/10"
                  >
                    홈으로 돌아가기
                  </Link>
                </div>
              </div>
            </div>
          </section>

          <section className="grid gap-6 md:grid-cols-[1.25fr_0.85fr]">
            <div
              className={`relative overflow-hidden rounded-3xl p-8 ${SECONDARY_PANEL}`}
              style={{ backgroundImage: detailTexture }}
            >
              <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_top,rgba(108,92,231,0.18),transparent_60%),radial-gradient(circle_at_bottom,rgba(255,126,182,0.18),transparent_55%)] pointer-events-none" />
              <div className="relative space-y-5">
                <div>
                  <h2 className="text-xl font-hero-mincho text-white mb-1">시나리오 개요</h2>
                  <p className="text-xs uppercase tracking-[0.15em] text-indigo-200/70">Summary Scroll</p>
                </div>
                <p
                  className="text-sm leading-relaxed text-slate-300"
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
                    className="text-xs uppercase tracking-[0.15em] text-indigo-200 hover:text-pink-200 transition-colors"
                  >
                    {detailExpanded ? '접기 ▲' : '자세히 보기 ▾'}
                  </button>
                )}
              </div>
            </div>

            <div className={`rounded-3xl p-8 space-y-6 ${TERTIARY_PANEL}`}>
              <div>
                <h2 className="text-xl font-hero-mincho text-white mb-1">시나리오 정보</h2>
                <p className="text-xs uppercase tracking-[0.18em] text-indigo-200/70">Overview</p>
              </div>
              <div className="space-y-5 text-sm text-slate-300">
                <div>
                  <span className="text-xs uppercase tracking-[0.15em] text-indigo-200/70">카테고리</span>
                  <p className="mt-1 text-base text-white font-medium">{scenario.category}</p>
                </div>
                <div>
                  <span className="text-xs uppercase tracking-[0.15em] text-indigo-200/70">유형</span>
                  <p className="mt-1 text-base text-white font-medium">{scenario.type}</p>
                </div>
                <div>
                  <span className="text-xs uppercase tracking-[0.15em] text-indigo-200/70">상태</span>
                  <p className="mt-1 text-base text-white font-medium">
                    {scenario.implemented ? '플레이 가능' : '준비 중'}
                  </p>
                </div>
                {scenario.mood && scenario.mood.length > 0 && (
                  <div>
                    <span className="text-xs uppercase tracking-[0.15em] text-indigo-200/70 block mb-2">분위기</span>
                    <div className="flex flex-wrap gap-2">
                      {scenario.mood.map((mood, index) => (
                        <span
                          key={`mood-chip-${mood}-${index}`}
                          className={`${CHIP_CLASS} text-[11px]`}
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
            <section className={`rounded-[32px] p-8 space-y-6 ${TERTIARY_PANEL}`}>
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-hero-mincho text-white">등장 인물</h2>
                  <p className="text-xs uppercase tracking-[0.15em] text-indigo-200/70 mt-1">
                    Allies & Rivals
                  </p>
                </div>
                <span className="text-[11px] uppercase tracking-[0.18em] text-indigo-200/70">
                  {scenario.characters.length}명
                </span>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                {scenario.characters.map((chara, index) => (
                  <div
                    key={`${chara.name}-${index}`}
                    className={`relative overflow-hidden rounded-2xl p-5 flex gap-4 transition-transform hover:-translate-y-1 ${SECONDARY_PANEL}`}
                  >
                    <div className="relative w-16 h-16 rounded-2xl overflow-hidden flex-shrink-0 ring-2 ring-indigo-400/40">
                      <img
                        src={chara.image}
                        alt={chara.name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div className="flex-1 min-w-0 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <h3 className="text-lg font-hero-mincho text-white leading-tight">{chara.name}</h3>
                        <span className="text-[10px] uppercase tracking-[0.15em] text-indigo-200/70">
                          {chara.status}
                        </span>
                      </div>
                      <p className="text-sm text-slate-300 leading-relaxed">
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
