import { useState } from 'react';
import type { ScenarioComment } from '@/services/api';

interface ScenarioCommentsProps {
  scenarioTitle: string;
  comments: ScenarioComment[];
  totalCount: number;
  loading: boolean;
  submitting: boolean;
  error: string | null;
  hasMore: boolean;
  onLoadMore: () => Promise<void>;
  onSubmit: (content: string) => Promise<void>;
  onDelete: (commentId: string) => Promise<void>;
  isLoggedIn: boolean;
  onRequireLogin: () => void;
}

export default function ScenarioComments({
  scenarioTitle,
  comments,
  totalCount,
  loading,
  submitting,
  error,
  hasMore,
  onLoadMore,
  onSubmit,
  onDelete,
  isLoggedIn,
  onRequireLogin,
}: ScenarioCommentsProps) {
  const [value, setValue] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!isLoggedIn) {
      onRequireLogin();
      return;
    }
    if (!value.trim()) {
      setFeedback('댓글 내용을 입력해주세요.');
      return;
    }
    try {
      await onSubmit(value.trim());
      setValue('');
      setFeedback(null);
    } catch (err) {
      console.error('Failed to submit comment:', err);
      setFeedback('댓글 등록에 실패했습니다. 잠시 후 다시 시도해주세요.');
    }
  };

  const handleDelete = async (commentId: string) => {
    if (!window.confirm('이 댓글을 삭제할까요?')) return;
    try {
      await onDelete(commentId);
    } catch (err) {
      console.error('Failed to delete comment:', err);
      setFeedback('댓글 삭제에 실패했습니다.');
    }
  };

  const formattedCount = totalCount.toLocaleString('ko-KR');

  return (
    <section className="rounded-[32px] bg-[#0b0715]/80 border border-white/10 shadow-[0_26px_80px_rgba(5,2,14,0.6)] backdrop-blur-2xl p-8 space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.15em] text-indigo-200/70">Community</p>
          <h2 className="text-2xl font-hero-mincho text-white">댓글 ({formattedCount})</h2>
          <p className="text-sm text-slate-300">
            {scenarioTitle}를 플레이한 이용자들과 이야기를 나눠보세요.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={isLoggedIn ? '응원, 피드백, 질문을 남겨보세요.' : '로그인 후 댓글을 작성할 수 있습니다.'}
          className="w-full rounded-2xl border border-white/15 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500/50 min-h-[90px]"
          disabled={!isLoggedIn || submitting}
        />
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>{value.length}/500</span>
          <button
            type="submit"
            disabled={submitting || !isLoggedIn}
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 px-4 py-2 text-sm font-semibold text-white shadow-[0_12px_30px_rgba(129,140,248,0.45)] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? '등록 중...' : '댓글 등록'}
          </button>
        </div>
        {feedback && <p className="text-sm text-rose-300">{feedback}</p>}
      </form>

      {error && (
        <div className="rounded-2xl border border-rose-400/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      )}

      <div className="space-y-4">
        {comments.length === 0 && !loading && (
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-6 text-center text-sm text-slate-400">
            첫 번째 댓글을 남겨보세요!
          </div>
        )}

        {comments.map((comment) => (
          <article
            key={comment.comment_id}
            className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-100"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-white">
                  {comment.display_name || comment.username || '익명'}
                </p>
                <time className="text-xs text-slate-400">
                  {new Date(comment.created_at).toLocaleString('ko-KR')}
                </time>
              </div>
              {comment.is_owner && (
                <button
                  type="button"
                  onClick={() => handleDelete(comment.comment_id)}
                  className="text-xs text-rose-300 hover:text-rose-200"
                >
                  삭제
                </button>
              )}
            </div>
            <p className="mt-3 whitespace-pre-line leading-relaxed text-slate-200">
              {comment.content}
            </p>
          </article>
        ))}

        {loading && (
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-6 text-center text-sm text-slate-300">
            댓글을 불러오는 중입니다...
          </div>
        )}

        {hasMore && !loading && (
          <button
            type="button"
            onClick={onLoadMore}
            className="w-full rounded-2xl border border-white/15 bg-transparent px-4 py-3 text-sm font-medium text-white hover:bg-white/5 transition-colors"
          >
            더 보기
          </button>
        )}
      </div>
    </section>
  );
}
