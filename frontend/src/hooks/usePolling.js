import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Poll an async fetcher on an interval. Pauses while a request is in flight.
 */
export function usePolling(fetcher, intervalMs = 4000, enabled = true) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState(null);
  const fetcherRef = useRef(fetcher);

  useEffect(() => {
    fetcherRef.current = fetcher;
  }, [fetcher]);

  const refresh = useCallback(async () => {
    try {
      const result = await fetcherRef.current();
      setData(result);
      setError(null);
      setUpdatedAt(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) return undefined;

    let cancelled = false;
    let timer;

    const tick = async () => {
      if (cancelled) return;
      await refresh();
      if (!cancelled) {
        timer = window.setTimeout(tick, intervalMs);
      }
    };

    tick();

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [enabled, intervalMs, refresh]);

  return { data, error, loading, updatedAt, refresh };
}
