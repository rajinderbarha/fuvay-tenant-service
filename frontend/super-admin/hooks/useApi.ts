"use client";
/**
 * useApi + useAction — proven data layer hooks.
 * PROVEN: every component fetches via these hooks — zero inline fetch().
 * useApi   → read (GET): loading / error / data / refetch
 * useAction → write (POST/PUT/DELETE): execute / loading / error
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { ServiceOSError } from "../lib/api";

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  requestId: string | null;
  refetch: () => void;
}

export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
): ApiState<T> {
  const [data,      setData]      = useState<T | null>(null);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState<string | null>(null);
  const [requestId, setRequestId] = useState<string | null>(null);
  const runRef = useRef(0);

  const run = useCallback(async () => {
    const id = ++runRef.current;
    setLoading(true); setError(null); setRequestId(null);
    try {
      const result = await fetcher();
      if (id === runRef.current) setData(result);
    } catch (e) {
      if (id === runRef.current) {
        setError(e instanceof ServiceOSError ? e.message : "An unexpected error occurred.");
        setRequestId(e instanceof ServiceOSError ? e.requestId ?? null : null);
      }
    } finally {
      if (id === runRef.current) setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => { run(); }, [run]);
  return { data, loading, error, requestId, refetch: run };
}

export function useAction<T, A extends unknown[]>(
  action: (...args: A) => Promise<T>,
) {
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [requestId, setRequestId] = useState<string | null>(null);
  const [context, setContext] = useState<Record<string, unknown> | null>(null);

  const execute = useCallback(async (...args: A): Promise<T | null> => {
    setLoading(true); setError(null); setErrorCode(null); setRequestId(null); setContext(null);
    try {
      const result = await action(...args);
      return result;
    } catch (e) {
      const msg = e instanceof ServiceOSError ? e.message
        : e instanceof Error ? e.message
        : "Action failed.";
      setError(msg);
      setErrorCode(e instanceof ServiceOSError ? e.code : null);
      setRequestId(e instanceof ServiceOSError ? e.requestId ?? null : null);
      setContext(e instanceof ServiceOSError ? e.context ?? null : null);
      return null;
    } finally {
      setLoading(false);
    }
  }, [action]);

  return { execute, loading, error, errorCode, requestId, context, clearError: () => setError(null) };
}
