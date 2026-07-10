/**
 * JobStatusBadge — reads ALL 23 job status colours from tokens.ts.
 * PROVEN: zero hardcoded hex values — all from tokens.colors.jobStatus.
 */
import React from "react";
import { tokens, type JobStatus } from "../../tokens/tokens";

export function JobStatusBadge({ status, size="md" }:{status:JobStatus; size?:"sm"|"md"|"lg"}) {
  const config = tokens.colors.jobStatus[status];
  if (!config) return <span>{status}</span>;

  const sizes = {
    sm: { fontSize:"10px", padding:"2px 7px",  borderRadius:"999px", fontWeight:700 },
    md: { fontSize:"11px", padding:"3px 10px", borderRadius:"999px", fontWeight:700 },
    lg: { fontSize:"12px", padding:"4px 13px", borderRadius:"999px", fontWeight:700 },
  };
  return (
    <span style={{
      display:"inline-flex", alignItems:"center", gap:"5px",
      background: config.bg, color: config.text,
      border: `1px solid ${config.border}`,
      letterSpacing:"0.03em", whiteSpace:"nowrap",
      ...sizes[size],
    }}>
      <span style={{ width:6, height:6, borderRadius:"50%", background:config.text, flexShrink:0 }}/>
      {config.label}
    </span>
  );
}

export { type JobStatus };
