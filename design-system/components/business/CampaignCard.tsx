"use client";
import React from "react";
export interface CampaignCardProps { campaignId:string; postType:string; platform:string; status:"scheduled"|"published"|"failed"|"draft"; scheduledAt?:string; publishedAt?:string; costInr?:number; followerCount?:number; caption?:string; imageUrl?:string; reused?:boolean; }
const PlatformIcon:Record<string,string> = { instagram:"📸", facebook:"📘", twitter:"🐦", linkedin:"💼" };
const StatusColor:Record<string,{bg:string,text:string,border:string}> = {
  scheduled:  {bg:"var(--color-info-bg)",    text:"var(--color-info-text)",    border:"var(--color-info-border)"},
  published:  {bg:"var(--color-success-bg)", text:"var(--color-success-text)", border:"var(--color-success-border)"},
  failed:     {bg:"var(--color-danger-bg)",  text:"var(--color-danger-text)",  border:"var(--color-danger-border)"},
  draft:      {bg:"var(--color-surface-sunken)", text:"var(--color-text-tertiary)", border:"var(--color-border)"},
};
export function CampaignCard({ campaignId, postType, platform, status, scheduledAt, publishedAt, costInr, followerCount, caption, imageUrl, reused }: CampaignCardProps) {
  const sc = StatusColor[status];
  const dateVal = publishedAt ?? scheduledAt;
  return (
    <div style={{ background:"var(--color-surface-base)", border:"1px solid var(--color-border)",
      borderRadius:"var(--radius-lg)", overflow:"hidden", boxShadow:"var(--shadow-sm)" }}>
      {imageUrl ? (
        <div style={{ height:120, background:"var(--color-surface-sunken)",
          backgroundImage:`url(${imageUrl})`, backgroundSize:"cover", backgroundPosition:"center",
          position:"relative" }}>
          <div style={{ position:"absolute", top:8, right:8 }}>
            <span style={{ ...sc, fontSize:"var(--text-xs)", padding:"3px 8px",
              borderRadius:"var(--radius-full)", fontWeight:"var(--font-bold)" }}>
              {status}
            </span>
          </div>
        </div>
      ) : (
        <div style={{ height:60, background:"var(--color-accent-muted)",
          display:"flex", alignItems:"center", justifyContent:"center",
          borderBottom:"1px solid var(--color-border)", position:"relative" }}>
          <span style={{ fontSize:24 }}>{PlatformIcon[platform]??"📣"}</span>
          <span style={{ position:"absolute", top:8, right:8, ...sc,
            fontSize:"var(--text-xs)", padding:"3px 8px", borderRadius:"var(--radius-full)",
            fontWeight:"var(--font-bold)" }}>{status}</span>
        </div>
      )}
      <div style={{ padding:"14px 16px" }}>
        <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:6 }}>
          <span style={{ fontSize:14 }}>{PlatformIcon[platform]??"📣"}</span>
          <p style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-semibold)",
            color:"var(--color-text-primary)", margin:0 }}>{postType.replace(/_/g," ")}</p>
          {reused && <span style={{ fontSize:"var(--text-xs)", padding:"1px 6px",
            borderRadius:"var(--radius-sm)", background:"var(--color-success-bg)",
            color:"var(--color-success-text)", fontWeight:"var(--font-semibold)" }}>Reused</span>}
        </div>
        {caption && <p style={{ fontSize:"var(--text-xs)", color:"var(--color-text-secondary)",
          margin:"0 0 8px", lineHeight:1.4,
          display:"-webkit-box", WebkitLineClamp:2, WebkitBoxOrient:"vertical",
          overflow:"hidden" }}>{caption}</p>}
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
          <div style={{ display:"flex", gap:10 }}>
            {costInr!=null && <span style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)" }}>
              ₹{costInr.toFixed(2)}
            </span>}
            {followerCount!=null && <span style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)" }}>
              {followerCount.toLocaleString()} followers
            </span>}
          </div>
          {dateVal && <span style={{ fontSize:"var(--text-xs)", color:"var(--color-text-tertiary)" }}>
            {new Date(dateVal).toLocaleDateString("en-IN",{day:"numeric",month:"short"})}
          </span>}
        </div>
      </div>
    </div>
  );
}
