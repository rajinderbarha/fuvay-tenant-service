/** Sidebar — main navigation. Dark surface regardless of theme. */
import React, { useState } from "react";

export interface NavItem {
  id: string; label: string; icon: React.ReactNode;
  badge?: number; children?: NavItem[];
}

export function Sidebar({ items, activeId, onNavigate, collapsed, logo }:{
  items:NavItem[]; activeId:string; onNavigate:(id:string)=>void;
  collapsed?:boolean; logo?:React.ReactNode;
}) {
  const w = collapsed ? 64 : 240;
  return (
    <aside style={{
      width:w, minHeight:"100vh", flexShrink:0,
      background:"var(--color-surface-sidebar)",
      borderRight:"1px solid var(--sidebar-border)",
      display:"flex", flexDirection:"column",
      transition:"width 0.2s ease", overflow:"hidden",
    }}>
      <div style={{ padding: collapsed ? "20px 14px" : "20px 16px", borderBottom:"1px solid var(--sidebar-border)", minHeight:64 }}>
        {logo}
      </div>
      <nav style={{ flex:1, padding:"12px 8px", display:"flex", flexDirection:"column", gap:"2px" }}>
        {items.map(item => (
          <NavItemRow key={item.id} item={item} active={activeId===item.id}
            onNavigate={onNavigate} collapsed={collapsed}/>
        ))}
      </nav>
    </aside>
  );
}

function NavItemRow({ item, active, onNavigate, collapsed }:{
  item:NavItem; active:boolean; onNavigate:(id:string)=>void; collapsed?:boolean;
}) {
  const [hover, setHover] = useState(false);
  return (
    <button
      onClick={() => onNavigate(item.id)}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        width:"100%", display:"flex", alignItems:"center", gap:"10px",
        padding: collapsed ? "10px" : "10px 12px",
        borderRadius:"10px", border:"none", cursor:"pointer", textAlign:"left",
        background: active ? "var(--sidebar-item-active)" : hover ? "var(--sidebar-item-hover)" : "transparent",
        color: active ? "var(--sidebar-text-active)" : "var(--sidebar-text)",
        fontWeight: active ? 600 : 400, fontSize:"13px",
        transition:"all 0.12s ease",
        justifyContent: collapsed ? "center" : undefined,
      }}
    >
      <span style={{ flexShrink:0, width:18, height:18, display:"flex", alignItems:"center", justifyContent:"center" }}>
        {item.icon}
      </span>
      {!collapsed && <span style={{ flex:1, whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>{item.label}</span>}
      {!collapsed && item.badge != null && (
        <span style={{ background:"var(--color-accent)", color:"var(--color-text-on-brand)", borderRadius:"999px", fontSize:"10px", fontWeight:700, padding:"1px 6px", flexShrink:0 }}>
          {item.badge}
        </span>
      )}
    </button>
  );
}
