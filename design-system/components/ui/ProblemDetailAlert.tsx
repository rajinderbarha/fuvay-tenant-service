"use client";
/**
 * ProblemDetailAlert — renders RFC 7807 Problem Details object.
 * Matches the ServiceOSError shape from lib/api.ts.
 */
import React, { useState } from "react";
export interface ProblemDetail {
  type?:      string;
  title?:     string;
  status?:    number;
  detail?:    string;
  instance?:  string;
  error_code?: string;
  message?:   string;
  resolution?: string;
  context?:   Record<string, unknown>;
  request_id?: string;
}
export interface ProblemDetailAlertProps { problem: ProblemDetail; onClose?: () => void; onRetry?: () => void; }
export function ProblemDetailAlert({ problem, onClose, onRetry }: ProblemDetailAlertProps) {
  const [showCtx, setShowCtx] = useState(false);
  const title   = problem.title   ?? problem.error_code ?? "Request Failed";
  const message = problem.detail  ?? problem.message    ?? "An unexpected error occurred.";
  const code    = problem.error_code ?? (problem.status ? `HTTP ${problem.status}` : "ERROR");
  const hasCtx  = problem.context && Object.keys(problem.context).length > 0;
  return (
    <div role="alert" style={{ borderRadius:"var(--radius-lg)", overflow:"hidden",
      border:"1px solid var(--color-danger-border)", boxShadow:"var(--shadow-sm)" }}>
      <div style={{ display:"flex", gap:12, padding:"14px 16px",
        background:"var(--color-danger-bg)", borderLeft:"3px solid var(--color-danger)" }}>
        <span style={{ fontSize:16, color:"var(--color-danger-text)", fontWeight:"var(--font-bold)", flexShrink:0 }}>✕</span>
        <div style={{ flex:1, minWidth:0 }}>
          <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:4 }}>
            <p style={{ fontSize:"var(--text-base)", fontWeight:"var(--font-semibold)",
              color:"var(--color-danger-text)", margin:0 }}>{title}</p>
            <code style={{ fontSize:"var(--text-xs)", padding:"1px 6px", borderRadius:"var(--radius-sm)",
              background:"var(--color-danger-border)", color:"var(--color-danger-text)", fontFamily:"var(--font-mono)" }}>
              {code}
            </code>
          </div>
          <p style={{ fontSize:"var(--text-sm)", color:"var(--color-danger-text)", margin:0, lineHeight:1.5 }}>
            {message}
          </p>
          {problem.resolution && (
            <p style={{ fontSize:"var(--text-sm)", color:"var(--color-danger-text)", margin:"6px 0 0",
              opacity:0.85 }}>Suggestion: {problem.resolution}</p>
          )}
          {problem.request_id && (
            <p style={{ fontSize:"var(--text-xs)", color:"var(--color-danger-text)", margin:"6px 0 0",
              opacity:0.6, fontFamily:"var(--font-mono)" }}>request_id: {problem.request_id}</p>
          )}
          {hasCtx && (
            <button onClick={() => setShowCtx(!showCtx)}
              style={{ background:"none", border:"none", cursor:"pointer", padding:0,
                fontSize:"var(--text-xs)", color:"var(--color-danger-text)", margin:"6px 0 0",
                textDecoration:"underline", fontFamily:"var(--font-sans)" }}>
              {showCtx ? "Hide" : "Show"} context ↓
            </button>
          )}
          {showCtx && hasCtx && (
            <pre style={{ fontSize:"var(--text-xs)", fontFamily:"var(--font-mono)",
              background:"rgba(0,0,0,0.06)", padding:"8px 10px", borderRadius:"var(--radius-sm)",
              margin:"8px 0 0", overflow:"auto", maxHeight:120,
              color:"var(--color-danger-text)" }}>
              {JSON.stringify(problem.context, null, 2)}
            </pre>
          )}
        </div>
        <div style={{ display:"flex", gap:6, flexShrink:0 }}>
          {onRetry && (
            <button onClick={onRetry} style={{ fontSize:"var(--text-xs)", padding:"4px 10px",
              borderRadius:"var(--radius-sm)", border:"1px solid var(--color-danger-border)",
              background:"transparent", color:"var(--color-danger-text)", cursor:"pointer",
              fontFamily:"var(--font-sans)", fontWeight:"var(--font-medium)" }}>
              Retry
            </button>
          )}
          {onClose && (
            <button onClick={onClose} style={{ background:"none", border:"none", cursor:"pointer",
              color:"var(--color-danger-text)", fontSize:16, padding:0, opacity:0.6 }}>✕</button>
          )}
        </div>
      </div>
    </div>
  );
}
