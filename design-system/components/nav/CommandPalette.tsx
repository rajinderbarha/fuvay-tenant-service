"use client";
import React, { useState, useEffect, useRef } from "react";
export interface Command { id:string; label:string; description?:string; group?:string; shortcut?:string; icon?:string; action?:()=>void; }
export interface CommandPaletteProps { commands?: Command[]; onClose?: ()=>void; placeholder?: string; }
export function CommandPalette({ commands = [], onClose, placeholder = "Search commands…" }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => { inputRef.current?.focus(); }, []);
  useEffect(() => {
    function handle(e: KeyboardEvent) { if (e.key === "Escape") onClose?.(); }
    document.addEventListener("keydown", handle);
    return () => document.removeEventListener("keydown", handle);
  }, [onClose]);
  const filtered = commands.filter(c =>
    !query || c.label.toLowerCase().includes(query.toLowerCase()) ||
    c.description?.toLowerCase().includes(query.toLowerCase()) ||
    c.group?.toLowerCase().includes(query.toLowerCase())
  );
  const groups = [...new Set(filtered.map(c => c.group ?? ""))];
  return (
    <div className="cmd-overlay" onClick={e => e.target === e.currentTarget && onClose?.()}>
      <div style={{ width:"100%", maxWidth:560, background:"var(--color-surface-elevated)",
        borderRadius:"var(--radius-xl)", boxShadow:"var(--shadow-xl)",
        border:"1px solid var(--color-border)", overflow:"hidden",
        animation:"scaleIn 0.15s ease" }}>
        <div style={{ display:"flex", alignItems:"center", gap:10, padding:"0 16px",
          borderBottom:"1px solid var(--color-border)", height:52 }}>
          <span style={{ fontSize:16, color:"var(--color-text-tertiary)" }}>⌘</span>
          <input ref={inputRef} value={query} onChange={e => setQuery(e.target.value)}
            placeholder={placeholder} style={{ flex:1, border:"none", outline:"none",
              background:"transparent", fontSize:"var(--text-lg)",
              color:"var(--color-text-primary)", fontFamily:"var(--font-sans)" }}/>
          <kbd style={{ padding:"2px 6px", borderRadius:"var(--radius-sm)",
            background:"var(--kbd-bg)", border:"1px solid var(--kbd-border)",
            fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)" }}>Esc</kbd>
        </div>
        <div style={{ maxHeight:400, overflowY:"auto" }}>
          {filtered.length === 0 ? (
            <p style={{ padding:"32px 16px", textAlign:"center", color:"var(--color-text-tertiary)",
              fontSize:"var(--text-sm)", margin:0 }}>No commands found</p>
          ) : groups.map(group => (
            <div key={group}>
              {group && <p style={{ fontSize:10, fontWeight:"var(--font-bold)",
                color:"var(--color-text-tertiary)", padding:"10px 16px 4px",
                margin:0, textTransform:"uppercase", letterSpacing:"0.08em" }}>{group}</p>}
              {filtered.filter(c => (c.group ?? "") === group).map(cmd => (
                <div key={cmd.id} onClick={() => { cmd.action?.(); onClose?.(); }}
                  style={{ display:"flex", alignItems:"center", gap:12, padding:"9px 16px",
                    cursor:"pointer", borderRadius:0 }}
                  onMouseEnter={e=>(e.currentTarget as HTMLDivElement).style.background="var(--color-surface-sunken)"}
                  onMouseLeave={e=>(e.currentTarget as HTMLDivElement).style.background="transparent"}>
                  {cmd.icon && <span style={{ width:28, height:28, borderRadius:"var(--radius-sm)",
                    background:"var(--color-surface-sunken)", display:"flex", alignItems:"center",
                    justifyContent:"center", fontSize:14, flexShrink:0 }}>{cmd.icon}</span>}
                  <div style={{ flex:1, minWidth:0 }}>
                    <p style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-medium)",
                      color:"var(--color-text-primary)", margin:0 }}>{cmd.label}</p>
                    {cmd.description && <p style={{ fontSize:"var(--text-xs)",
                      color:"var(--color-text-tertiary)", margin:0 }}>{cmd.description}</p>}
                  </div>
                  {cmd.shortcut && (
                    <div style={{ display:"flex", gap:3 }}>
                      {cmd.shortcut.split("+").map((k,i) => (
                        <kbd key={i} style={{ padding:"2px 6px", borderRadius:"var(--radius-sm)",
                          background:"var(--kbd-bg)", border:"1px solid var(--kbd-border)",
                          fontSize:10, color:"var(--color-text-tertiary)", fontFamily:"var(--font-mono)" }}>{k}</kbd>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
