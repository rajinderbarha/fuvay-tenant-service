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
  /** Domain error code behind `error` (e.g. "UNAUTHORIZED"), when the failure
   *  came from the API rather than the network. Callers that must tell "the
   *  server refused you" apart from "the server could not be reached" need
   *  this -- the message string alone cannot distinguish them. */
  errorCode: string | null;
  requestId: string | null;
  refetch: () => void;
}

export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
  options?: { enabled?: boolean },
): ApiState<T> {
  // FINAL-L5-05O Part 5: when enabled=false (permission already known to be
  // denied), never fire the request -- no restricted request starts before
  // known denial, and no skeleton/error-box flash for content the caller
  // will never be allowed to see. Defaults to true so all pre-existing call
  // sites are unaffected.
  const enabled = options?.enabled ?? true;
  const [data,      setData]      = useState<T | null>(null);
  const [loading,   setLoading]   = useState(enabled);
  const [error,     setError]     = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [requestId, setRequestId] = useState<string | null>(null);
  const runRef = useRef(0);

  const run = useCallback(async () => {
    if (!enabled) { setLoading(false); setData(null); setError(null); setErrorCode(null); return; }
    const id = ++runRef.current;
    setLoading(true); setError(null); setErrorCode(null); setRequestId(null);
    try {
      let result: T;
      try {
        result = await fetcher();
      } catch (firstError) {
        // A browser-level failure (offline transition, aborted socket, dev
        // server warm-up) has no domain error code and is safe to retry once
        // because useApi is only used for reads. Never retry a backend verdict.
        if (firstError instanceof ServiceOSError) throw firstError;
        await new Promise(resolve => window.setTimeout(resolve, 250));
        result = await fetcher();
      }
      if (id === runRef.current) setData(result);
    } catch (e) {
      if (id === runRef.current) {
        setError(e instanceof ServiceOSError ? e.message : "An unexpected error occurred.");
        setErrorCode(e instanceof ServiceOSError ? e.code : null);
        setRequestId(e instanceof ServiceOSError ? e.requestId ?? null : null);
      }
    } finally {
      if (id === runRef.current) setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, ...deps]);

  // Schedule the automatic load one tick later. React development Strict Mode
  // mounts an effect, immediately cleans it up, then mounts it again; firing
  // synchronously here launched two identical requests and the slower failure
  // could replace a successful response with an error card. The cleanup
  // cancels that throwaway pass while manual refetch remains immediate.
  useEffect(() => {
    const timer = window.setTimeout(() => { void run(); }, 0);
    return () => window.clearTimeout(timer);
  }, [run]);
  return { data, loading, error, errorCode, requestId, refetch: run };
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
