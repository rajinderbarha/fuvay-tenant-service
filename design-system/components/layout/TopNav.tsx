/** TopNav — top navigation bar. */
import React from "react";
import { Avatar } from "../ui/Avatar";

export function TopNav({ title, user, onMenuToggle, actions }:{
  title?:string; user?:{name:string;role:string};
  onMenuToggle?:()=>void; actions?:React.ReactNode;
}) {
  return (
    <header style={{
      height:60, display:"flex", alignItems:"center", gap:"16px",
      padding:"0 24px", background:"var(--color-surface-base)",
      borderBottom:"1px solid var(--color-border)",
      boxShadow:"var(--shadow-xs)", position:"sticky", top:0, zIndex:200,
    }}>
      {onMenuToggle && (
        <button onClick={onMenuToggle} style={{
          background:"none", border:"none", cursor:"pointer", padding:"6px",
          color:"var(--color-text-secondary)", borderRadius:"8px", display:"flex",
        }}>
          ☰
        </button>
      )}
      {title && <h1 style={{ fontSize:"16px", fontWeight:600, color:"var(--color-text-primary)", margin:0 }}>{title}</h1>}
      <div style={{ flex:1 }}/>
      {actions}
      {user && (
        <div style={{ display:"flex", alignItems:"center", gap:"10px" }}>
          <div style={{ textAlign:"right" }}>
            <p style={{ fontSize:"13px", fontWeight:600, color:"var(--color-text-primary)", margin:0, lineHeight:1.2 }}>{user.name}</p>
            <p style={{ fontSize:"11px", color:"var(--color-text-tertiary)", margin:0, textTransform:"uppercase", letterSpacing:"0.05em" }}>{user.role}</p>
          </div>
          <Avatar name={user.name} size={34}/>
        </div>
      )}
    </header>
  );
}
