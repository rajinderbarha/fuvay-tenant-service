"use client";
import { useState, useEffect, useCallback } from "react";
const KEY = "serviceos-tenant-theme";
type M = "light"|"dark";
export function useTheme() {
  const [theme,setS]=useState<M>("light");
  useEffect(()=>{
    const s=localStorage.getItem(KEY) as M|null;
    const p=window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";
    const i=s??p; setS(i); document.documentElement.setAttribute("data-theme",i);
  },[]);
  const setTheme=useCallback((m:M)=>{setS(m);document.documentElement.setAttribute("data-theme",m);localStorage.setItem(KEY,m);},[]);
  const toggle=useCallback(()=>setTheme(theme==="light"?"dark":"light"),[theme,setTheme]);
  return {theme,setTheme,toggle,isDark:theme==="dark"};
}
