"use client";
import React, { useState } from "react";
export interface Notification { id:string; title:string; body?:string; time?:string; read?:boolean; variant?:"info"|"success"|"warning"|"danger"; }
export interface NotificationBellProps { notifications?: Notification[]; onRead?: (id:string)=>void; onReadAll?: ()=>void; }
export function NotificationBell({ notifications = [], onRead, onReadAll }: NotificationBellProps) {
  const [open, setOpen] = useState(false);
  const unread = notifications.filter(n => !n.read).length;
  const VDot: Record<string,string> = { info:"var(--color-info)", success:"var(--color-success)", warning:"var(--color-warning)", danger:"var(--color-danger)" };
  return (
    <div style={{ position:"relative" }}>
      <button onClick={() => setOpen(!open)} aria-label={`${unread} unread notifications`}
        style={{ width:36, height:36, borderRadius:"var(--radius-md)",
          border:"1px solid var(--color-border)", background:"var(--color-surface-base)",
          display:"flex", alignItems:"center", justifyContent:"center",
          cursor:"pointer", position:"relative", fontSize:16 }}>
        🔔
        {unread > 0 && (
          <span style={{ position:"absolute", top:3, right:3, width:16, height:16,
            borderRadius:"var(--radius-full)", background:"var(--color-danger)",
            border:"2px solid var(--color-surface-base)", display:"flex",
            alignItems:"center", justifyContent:"center",
            fontSize:9, fontWeight:"var(--font-bold)", color:"white", lineHeight:1 }}>
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>
      {open && (
        <div style={{ position:"absolute", top:"calc(100% + 4px)", right:0, width:340,
          background:"var(--color-surface-elevated)", border:"1px solid var(--color-border)",
          borderRadius:"var(--radius-lg)", boxShadow:"var(--shadow-xl)",
          zIndex:"var(--z-dropdown)" as unknown as number, overflow:"hidden",
          animation:"slideDown 0.15s ease" }}>
          <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
            padding:"12px 16px", borderBottom:"1px solid var(--color-border)" }}>
            <h3 style={{ fontSize:"var(--text-base)", fontWeight:"var(--font-semibold)",
              color:"var(--color-text-primary)", margin:0 }}>Notifications</h3>
            {unread > 0 && onReadAll && (
              <button onClick={onReadAll} style={{ background:"none", border:"none",
                fontSize:"var(--text-xs)", color:"var(--color-accent)", cursor:"pointer",
                fontFamily:"var(--font-sans)" }}>Mark all read</button>
            )}
          </div>
          <div style={{ maxHeight:360, overflowY:"auto" }}>
            {notifications.length === 0 ? (
              <p style={{ padding:"32px 16px", textAlign:"center", color:"var(--color-text-tertiary)",
                fontSize:"var(--text-sm)", margin:0 }}>No notifications</p>
            ) : notifications.map(n => (
              <div key={n.id} onClick={() => onRead?.(n.id)}
                style={{ display:"flex", gap:10, padding:"12px 16px",
                  background: n.read ? "transparent" : "var(--color-accent-muted)",
                  borderBottom:"1px solid var(--color-border)", cursor:"pointer",
                  opacity: n.read ? 0.7 : 1 }}
                onMouseEnter={e=>(e.currentTarget as HTMLDivElement).style.background="var(--color-surface-sunken)"}
                onMouseLeave={e=>(e.currentTarget as HTMLDivElement).style.background=n.read?"transparent":"var(--color-accent-muted)"}>
                <span style={{ width:7, height:7, borderRadius:"50%", flexShrink:0, marginTop:5,
                  background: n.read ? "transparent" : VDot[n.variant??"info"] }}/>
                <div style={{ flex:1, minWidth:0 }}>
                  <p style={{ fontSize:"var(--text-sm)", fontWeight: n.read ? "var(--font-regular)" : "var(--font-semibold)",
                    color:"var(--color-text-primary)", margin:0 }}>{n.title}</p>
                  {n.body && <p style={{ fontSize:"var(--text-xs)", color:"var(--color-text-secondary)",
                    margin:"3px 0 0", lineHeight:1.4 }}>{n.body}</p>}
                  {n.time && <p style={{ fontSize:10, color:"var(--color-text-tertiary)",
                    margin:"4px 0 0" }}>{n.time}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
