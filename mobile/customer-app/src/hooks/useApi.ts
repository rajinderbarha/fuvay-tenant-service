import { useCallback, useEffect, useRef, useState } from "react";

export function useApi<T>(fn: ()=>Promise<T>, deps: unknown[]=[]) {
  const [data,    setData]    = useState<T|null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string|null>(null);
  const counter = useRef(0);
  const load = useCallback(() => {
    const id = ++counter.current; setLoading(true); setError(null);
    fn().then(d=>{ if(counter.current===id){ setData(d); setLoading(false); }})
        .catch(e=>{ if(counter.current===id){ setError(e.message??"Error"); setLoading(false); }});
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(()=>{ load(); },[load]);
  return { data, loading, error, refetch:load };
}

export function useAction<R>(fn:(...args:unknown[])=>Promise<R>) {
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string|null>(null);
  async function execute(...args:unknown[]): Promise<R|null> {
    setLoading(true); setError(null);
    try { const r = await fn(...args); setLoading(false); return r; }
    catch(e:unknown) { setError(e instanceof Error?e.message:"Error"); setLoading(false); return null; }
  }
  return { execute, loading, error };
}
