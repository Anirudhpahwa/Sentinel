"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface PollingState<T> {
  data: T | null;
  error: Error | null;
  isLoading: boolean;
  lastUpdatedAt: Date | null;
  refetch: () => void;
}

/**
 * Phase 1 has no WebSockets or server push, so every live view is driven by
 * fixed-interval polling. `lastUpdatedAt` exists so views can surface
 * staleness explicitly instead of silently lagging behind real state.
 */
export function usePolling<T>(fetcher: () => Promise<T>, intervalMs: number, deps: unknown[] = []): PollingState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const fetcherRef = useRef(fetcher);

  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  const load = useCallback(() => {
    fetcherRef
      .current()
      .then((result) => {
        setData(result);
        setError(null);
        setLastUpdatedAt(new Date());
      })
      .catch((err) => setError(err instanceof Error ? err : new Error(String(err))));
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, intervalMs);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, load, ...deps]);

  // Loading only describes the initial fetch; background polls refresh silently.
  const isLoading = data === null && error === null;

  return { data, error, isLoading, lastUpdatedAt, refetch: load };
}
