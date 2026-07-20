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

// UX-06 ROUND 2 fix: the original `(...args:unknown[])=>Promise<R>` signature could
// not correctly infer R or the argument types when callers passed a concretely-typed
// multi-arg function (e.g. `(reason:string)=>Promise<Quote>`), producing cascading
// "[never, never]" / "unknown is not assignable to string" errors at every call site
// across ~9 screens. Generalizing over the args tuple `A` fixes inference for all of
// them at once.
export function useAction<A extends unknown[], R>(fn:(...args:A)=>Promise<R>) {
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string|null>(null);
  async function execute(...args:A): Promise<R|null> {
    setLoading(true); setError(null);
    try { const r = await fn(...args); setLoading(false); return r; }
    catch(e:unknown) { setError(e instanceof Error?e.message:"Error"); setLoading(false); return null; }
  }
  return { execute, loading, error };
}
