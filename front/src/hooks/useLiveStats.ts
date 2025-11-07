import { useCallback, useEffect, useRef, useState } from 'react';
import { apiClient, LiveStats } from '@/services/api';

interface UseLiveStatsOptions {
  pollInterval?: number;
}

export function useLiveStats(options: UseLiveStatsOptions = {}) {
  const { pollInterval = 15000 } = options;
  const [stats, setStats] = useState<LiveStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isInitialFetch = useRef(true);

  const fetchStats = useCallback(
    async (silent: boolean = false) => {
      if (!silent) {
        setLoading(true);
      }
      try {
        const data = await apiClient.getLiveStats();
        setStats(data);
        setError(null);
      } catch (err) {
        console.error('Failed to load live stats:', err);
        setError('실시간 통계를 불러올 수 없습니다.');
      } finally {
        setLoading(false);
        isInitialFetch.current = false;
      }
    },
    []
  );

  useEffect(() => {
    fetchStats();

    if (pollInterval <= 0) {
      return;
    }

    const id = setInterval(() => {
      // Avoid flickering during background polling
      fetchStats(true);
    }, pollInterval);

    return () => clearInterval(id);
  }, [pollInterval, fetchStats]);

  return {
    stats,
    loading: loading && isInitialFetch.current,
    error,
    refresh: () => fetchStats(false),
  };
}
