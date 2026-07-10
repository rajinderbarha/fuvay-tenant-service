"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { ServiceOSError } from "../lib/api";
export interface ApiState<T> { data:T|null; loading:boolean; error:string|null; requestId:string|null; refetch:()=>void; }
export function useApi<T>(fetcher:()=>Promise<T>, deps:unknown[]=[]):ApiState<T> {
  const [data,setData]=useState<T|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState<string|null>(null);
  const [requestId,setRequestId]=useState<string|null>(null);
  const r=useRef(0);
  const run=useCallback(async()=>{
    const id=++r.current; setLoading(true); setError(null); setRequestId(null);
    try{const res=await fetcher(); if(id===r.current)setData(res);}
    catch(e){
      if(id===r.current){
        setError(e instanceof ServiceOSError?e.message:"Unexpected error.");
        setRequestId(e instanceof ServiceOSError ? e.requestId ?? null : null);
      }
    }
    finally{if(id===r.current)setLoading(false);}
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },deps);
  useEffect(()=>{run();},[run]);
  return {data,loading,error,requestId,refetch:run};
}
export function useAction<T,A extends unknown[]>(
  action:(...a:A)=>Promise<T>,
  opts?:{ onSuccess?:(result:T)=>void; onError?:(msg:string)=>void },
) {
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState<string|null>(null);
  const [errorCode,setErrorCode]=useState<string|null>(null);
  const [requestId,setRequestId]=useState<string|null>(null);
  const execute=useCallback(async(...args:A):Promise<T|null>=>{
    setLoading(true);setError(null);setErrorCode(null);setRequestId(null);
    try{const res=await action(...args); opts?.onSuccess?.(res); return res;}
    catch(e){
      const msg=e instanceof ServiceOSError?e.message:"Action failed.";
      setError(msg);
      setErrorCode(e instanceof ServiceOSError ? e.code : null);
      setRequestId(e instanceof ServiceOSError ? e.requestId ?? null : null);
      opts?.onError?.(msg);
      return null;
    }
    finally{setLoading(false);}
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },[action]);
  return {execute,loading,error,errorCode,requestId,clearError:()=>setError(null)};
}
