import type { LiveStats } from '@/services/api';

interface LiveStatsBarProps {
  stats: LiveStats | null;
  loading: boolean;
  error: string | null;
  bubbleBalance: number;
  onRefresh: () => void;
}

type StatField = 'total_likes' | 'total_comments' | 'total_chats' | 'avg_affinity_score';

const STAT_CARDS: Array<{
  key: string;
  label: string;
  icon: string;
  field: StatField;
  accent: string;
}> = [
  {
    key: 'likes',
    label: '좋아요',
    icon: '❤️',
    field: 'total_likes',
    accent: 'from-rose-500/30 via-rose-400/15 to-transparent',
  },
  {
    key: 'comments',
    label: '댓글',
    icon: '💬',
    field: 'total_comments',
    accent: 'from-sky-500/30 via-sky-400/15 to-transparent',
  },
  {
    key: 'chats',
    label: '채팅 수',
    icon: '🗣️',
    field: 'total_chats',
    accent: 'from-amber-500/30 via-amber-400/15 to-transparent',
  },
  {
    key: 'affinity',
    label: '평균 친밀도',
    icon: '🤝',
    field: 'avg_affinity_score',
    accent: 'from-emerald-500/30 via-emerald-400/15 to-transparent',
  },
];

export default function LiveStatsBar({ stats, loading, error, bubbleBalance, onRefresh }: LiveStatsBarProps) {
  const formatNumber = (value?: number) => {
    if (value === undefined || value === null) return '-';
    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
    return value.toLocaleString('ko-KR');
  };

  const affinityValue =
    stats?.avg_affinity_score !== undefined
      ? `${stats.avg_affinity_score.toFixed(1)}%`
      : '-';

  return (
    <section className="relative z-20 mb-6">
      <div className="rounded-3xl bg-white/80 backdrop-blur-xl border border-white/40 shadow-[0_20px_60px_rgba(15,23,42,0.18)] px-6 py-5">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-purple-400">Live Status</p>
            <h2 className="text-xl font-semibold text-theme-primary">실시간 활동 지표</h2>
          </div>
          <div className="flex items-center gap-2 text-sm text-theme-secondary">
            {stats?.last_updated && (
              <span>업데이트 {new Date(stats.last_updated).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</span>
            )}
            <button
              type="button"
              onClick={onRefresh}
              className="inline-flex items-center gap-1 rounded-full border border-theme-card px-3 py-1 text-xs font-medium text-theme-primary hover:bg-theme-surface transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582M20 20v-5h-.581M5 9a7.003 7.003 0 0111.293-5H21M19 15a7.003 7.003 0 01-11.293 5H3" />
              </svg>
              새로고침
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-2xl bg-rose-50 text-rose-700 px-4 py-3 text-sm border border-rose-100">
            {error}
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-5">
          {STAT_CARDS.map((card) => {
            const rawValue = stats ? stats[card.field] : undefined;
            const value =
              card.field === 'avg_affinity_score'
                ? affinityValue
                : formatNumber(typeof rawValue === 'number' ? rawValue : undefined);

            return (
              <div
                key={card.key}
                className={`rounded-2xl border border-white/40 bg-gradient-to-br ${card.accent} px-4 py-3 shadow-inner`}
              >
                <div className="flex items-center gap-2 text-sm text-theme-secondary mb-1">
              <span role="img" aria-hidden="true">
                {card.icon}
              </span>
                  <span className="font-medium">{card.label}</span>
                </div>
                <p className="text-2xl font-semibold text-theme-primary">
                  {loading ? '–––' : value}
                </p>
              </div>
            );
          })}

          <div className="rounded-2xl border border-white/40 bg-gradient-to-br from-cyan-500/20 via-slate-100 to-white px-4 py-3 shadow-inner">
            <div className="flex items-center gap-2 text-sm text-theme-secondary mb-1">
              <span role="img" aria-hidden="true">
                🫧
              </span>
              <span className="font-medium">내 버블 잔액</span>
            </div>
            <p className="text-2xl font-semibold text-cyan-700">
              {bubbleBalance.toLocaleString('ko-KR')}
              <span className="text-sm text-cyan-600 ml-1">개</span>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
