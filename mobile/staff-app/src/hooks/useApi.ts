import { useCallback, useEffect, useRef, useState } from "react";

interface ApiState<T> {
  data:     T | null;
  loading:  boolean;
  error:    string | null;
  refetch:  () => void;
}

export function useApi<T>(fn: () => Promise<T>, deps: unknown[] = []): ApiState<T> {
  const [data,    setData]    = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);
  const counter = useRef(0);

  const load = useCallback(() => {
    const id = ++counter.current;
    setLoading(true); setError(null);
    fn().then(d => { if (counter.current === id) { setData(d); setLoading(false); } })
        .catch(e => { if (counter.current === id) { setError(e.message ?? "Error"); setLoading(false); } });
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load(); }, [load]);
  return { data, loading, error, refetch: load };
}

interface ActionState<Args extends unknown[], R> {
  execute:  (...args: Args) => Promise<R | null>;
  loading:  boolean;
  error:    string | null;
}

// Generic over the real argument tuple (not just `unknown[]`) so callers can
// pass concretely-typed functions (e.g. `(id: string) => Promise<T>`) and
// get a correctly-typed `execute` back, instead of every call site being
// forced through an `unknown[]`-erased signature that never actually
// matched what was being passed (was a real type-check failure, not just
// noise -- every call site had silently widened its argument types).
export function useAction<Args extends unknown[], R>(fn: (...args: Args) => Promise<R>): ActionState<Args, R> {
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);
  async function execute(...args: Args): Promise<R | null> {
    setLoading(true); setError(null);
    try { const r = await fn(...args); setLoading(false); return r; }
    catch (e: unknown) { setError(e instanceof Error ? e.message : "Error"); setLoading(false); return null; }
  }
  return { execute, loading, error };
}
