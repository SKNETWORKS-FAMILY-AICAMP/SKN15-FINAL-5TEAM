import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiClient, ScenarioComment } from '@/services/api';

interface UseScenarioCommentsOptions {
  pageSize?: number;
}

export function useScenarioComments(
  scenarioId?: string,
  options: UseScenarioCommentsOptions = {}
) {
  const { pageSize = 10 } = options;
  const [comments, setComments] = useState<ScenarioComment[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchComments = useCallback(
    async ({ cursor, reset = false }: { cursor?: string; reset?: boolean } = {}) => {
      if (!scenarioId) return;
      setLoading(true);
      try {
        const response = await apiClient.getScenarioComments(scenarioId, {
          limit: pageSize,
          cursor,
        });

        setComments((prev) =>
          reset
            ? response.items
            : [
                ...prev,
                ...response.items.filter(
                  (item) => !prev.some((p) => p.comment_id === item.comment_id)
                ),
              ]
        );
        setNextCursor(response.next_cursor ?? null);
        setTotalCount(response.total_count);
        setError(null);
      } catch (err) {
        console.error('Failed to load comments:', err);
        setError('댓글을 불러올 수 없습니다.');
      } finally {
        setLoading(false);
      }
    },
    [scenarioId, pageSize]
  );

  useEffect(() => {
    if (!scenarioId) {
      setComments([]);
      setNextCursor(null);
      setTotalCount(0);
      return;
    }

    fetchComments({ reset: true });
  }, [scenarioId, fetchComments]);

  const addComment = useCallback(
    async (content: string) => {
      if (!scenarioId) {
        throw new Error('시나리오 정보가 없습니다.');
      }
      setIsSubmitting(true);
      try {
        const newComment = await apiClient.createScenarioComment(scenarioId, { content });
        setComments((prev) => [newComment, ...prev]);
        setTotalCount((prev) => prev + 1);
        return newComment;
      } finally {
        setIsSubmitting(false);
      }
    },
    [scenarioId]
  );

  const removeComment = useCallback(
    async (commentId: number) => {
      if (!scenarioId) {
        return;
      }
      await apiClient.deleteScenarioComment(scenarioId, commentId);
      setComments((prev) => prev.filter((comment) => comment.id !== commentId));
      setTotalCount((prev) => Math.max(0, prev - 1));
    },
    [scenarioId]
  );

  const hasMore = useMemo(() => Boolean(nextCursor), [nextCursor]);

  return {
    comments,
    totalCount,
    loading,
    submitting: isSubmitting,
    error,
    hasMore,
    loadMore: () => {
      if (nextCursor && !loading) {
        return fetchComments({ cursor: nextCursor });
      }
      return Promise.resolve();
    },
    refresh: () => fetchComments({ reset: true }),
    addComment,
    removeComment,
  };
}
