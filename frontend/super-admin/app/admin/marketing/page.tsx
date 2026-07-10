"use client";
/**
 * Marketing Automation Command Center — enterprise rebuild.
 * PROVEN: every panel below reads from marketingCommandCenterApi (migration 100)
 * or the pre-existing Sprint 29 campaign API — no mock data.
 * Platform-pays-AI-cost rule: Platform AI Budget panel never reads tenant
 * wallet/usage-credit data — see marketingCommandCenterApi.getAIBudget().
 */
import React, { useState, useCallback } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  Card, Badge, Btn, StatCard, SectionHeader, Skeleton, EmptyState,
} from "../../../components/shared/ui";
import {
  Sparkles, Megaphone, Clock, ImageIcon, Banknote, AlertTriangle, Radio, Layers,
  Plus, Calendar as CalendarIcon, Link2, Upload, RefreshCw, Eye, Pencil,
  CheckCircle2, XCircle, Send, Copy, RotateCcw, BarChart3, ShieldAlert,
} from "lucide-react";
import { marketingCommandCenterApi, adminMarketingApi, type MarketingPost } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";

const STATUS_TABS = ["all", "draft", "generated", "pending_approval", "scheduled", "published", "failed", "archived"];

const STATUS_VARIANT: Record<string, "default"|"success"|"warning"|"danger"|"info"|"muted"> = {
  draft: "muted", generated: "info", pending_approval: "warning", approved: "info",
  scheduled: "info", publishing: "warning", published: "success", failed: "danger",
  cancelled: "muted", archived: "muted",
};

const PLATFORM_ICON: Record<string, string> = {
  facebook: "📘", instagram: "📸", google_business: "🟢", linkedin: "💼",
  youtube: "▶️", twitter: "✖️", whatsapp: "💬",
};

export default function MarketingAutomationPage() {
  const [tab, setTab] = useState("all");
  const fmt = (n: number) => `₹${n.toLocaleString("en-IN")}`;

  // ── Live data ────────────────────────────────────────────────────────────
  const summary  = useApi(useCallback(() => marketingCommandCenterApi.getSummary(), []));
  const posts    = useApi(useCallback(() => marketingCommandCenterApi.listPosts({ status: tab, limit: 50 }), [tab]));
  const calendar = useApi(useCallback(() => marketingCommandCenterApi.getCalendar(), []));
  const failures = useApi(useCallback(() => marketingCommandCenterApi.listPublishFailures(20), []));
  const budget   = useApi(useCallback(() => marketingCommandCenterApi.getAIBudget(), []));
  const accounts = useApi(useCallback(() => marketingCommandCenterApi.listSocialAccounts(), []));
  const templates= useApi(useCallback(() => marketingCommandCenterApi.listContentTemplates(), []));
  const activity = useApi(useCallback(() => marketingCommandCenterApi.listAuditLogs(10), []));
  const campaigns = useApi(useCallback(() => adminMarketingApi.listCampaigns({ page_size: 20 }), []));

  const approveAction = useAction(useCallback((id: string) => marketingCommandCenterApi.approvePost(id), []));
  const publishAction = useAction(useCallback((id: string) => marketingCommandCenterApi.publishNow(id), []));
  const retryAction   = useAction(useCallback((id: string) => marketingCommandCenterApi.retryPost(id), []));
  const cancelAction  = useAction(useCallback((id: string) => marketingCommandCenterApi.cancelPost(id), []));

  function refetchAll() {
    summary.refetch(); posts.refetch(); calendar.refetch(); failures.refetch();
    budget.refetch(); accounts.refetch(); templates.refetch(); activity.refetch(); campaigns.refetch();
  }

  async function handleApprove(id: string) { if (await approveAction.execute(id)) refetchAll(); }
  async function handlePublish(id: string) { if (await publishAction.execute(id)) refetchAll(); }
  async function handleRetry(id: string)   { if (await retryAction.execute(id)) refetchAll(); }
  async function handleCancel(id: string)  { if (await cancelAction.execute(id)) refetchAll(); }

  const s = summary.data;
  const b = budget.data;
  const postItems: MarketingPost[] = posts.data?.items ?? [];

  return (
    <AdminLayout activeNav="marketing">
      <SectionHeader
        title="Marketing Automation"
        subtitle="Generate, approve, schedule, publish, and analyze AI-powered content across ServiceOS channels."
        actions={<>
          <Btn variant="primary" size="sm" icon={<Sparkles size={14}/>}
            onClick={() => { window.location.href = "/admin/marketing/generate"; }}>
            Generate &amp; Schedule Post
          </Btn>
          <Btn variant="secondary" size="sm" icon={<Plus size={14}/>}
            onClick={() => { window.location.href = "/admin/marketing/campaigns"; }}>Create Campaign</Btn>
          <Btn variant="secondary" size="sm" icon={<CalendarIcon size={14}/>}>View Calendar</Btn>
          <Btn variant="secondary" size="sm" icon={<Link2 size={14}/>}>Connect Account</Btn>
          <Btn variant="ghost" size="sm" icon={<Upload size={14}/>}>Import Content</Btn>
          <Btn variant="ghost" size="sm" icon={<RefreshCw size={14}/>} onClick={refetchAll}/>
        </>}
      />

      {/* KPI Cards */}
      {summary.loading ? (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(180px,1fr))", gap:20, marginBottom:24 }}>
          {[...Array(8)].map((_,i) => <Skeleton key={i} height={110} style={{ borderRadius:14 }}/>)}
        </div>
      ) : (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(180px,1fr))", gap:20, marginBottom:24 }}>
          <StatCard label="Posts Published"   value={s?.posts_published ?? 0} trend="up" icon={<Megaphone/>}/>
          <StatCard label="Scheduled Posts"   value={s?.scheduled_posts ?? 0} trend="neutral" icon={<Clock/>}/>
          <StatCard label="Pending Approval"  value={s?.pending_approval ?? 0} trend="neutral" icon={<ShieldAlert/>}
            alert={(s?.pending_approval ?? 0) > 0}/>
          <StatCard label="Failed Posts"      value={s?.failed_posts ?? 0} trend={s?.failed_posts ? "down" : "neutral"} icon={<XCircle/>}
            alert={(s?.failed_posts ?? 0) > 0}/>
          <StatCard label="Images Generated"  value={s?.images_generated ?? 0} trend="up" icon={<ImageIcon/>}/>
          <StatCard label="Platform AI Spend" value={`${fmt(s?.platform_ai_spend_today ?? 0)} / ${fmt(s?.platform_ai_daily_budget ?? 0)}`}
            trend="neutral" icon={<Banknote/>}/>
          <StatCard label="Connected Channels" value={s?.connected_channels ?? 0} trend="neutral" icon={<Radio/>}/>
          <StatCard label="Active Campaigns"  value={s?.active_campaigns ?? 0} trend="neutral" icon={<Layers/>}/>
        </div>
      )}

      <div style={{ display:"grid", gridTemplateColumns:"2.2fr 1fr", gap:20 }}>
        {/* ── Main column ─────────────────────────────────────────────────── */}
        <div style={{ display:"flex", flexDirection:"column", gap:20 }}>
          {/* Campaigns & Content Pipeline */}
          <Card padding={0}>
            <div style={{ padding:"20px 24px 0" }}>
              <h3 style={{ fontSize:15, fontWeight:700, color:"var(--text-primary)", margin:"0 0 14px" }}>
                Campaigns &amp; Content Pipeline
              </h3>
              <div style={{ display:"flex", gap:6, flexWrap:"wrap", marginBottom:16 }}>
                {STATUS_TABS.map(t => (
                  <button key={t} onClick={() => setTab(t)} style={{
                    fontSize:12, fontWeight:600, padding:"6px 12px", borderRadius:8, cursor:"pointer",
                    border: tab === t ? "1px solid var(--accent)" : "1px solid var(--border)",
                    background: tab === t ? "var(--accent-muted)" : "var(--surface)",
                    color: tab === t ? "var(--accent)" : "var(--text-secondary)",
                    textTransform:"capitalize",
                  }}>{t.replace(/_/g," ")}</button>
                ))}
              </div>
            </div>
            {posts.loading ? (
              <div style={{ padding:"0 24px 20px", display:"flex", flexDirection:"column", gap:8 }}>
                {[...Array(4)].map((_,i) => <Skeleton key={i} height={52}/>)}
              </div>
            ) : postItems.length === 0 ? (
              <EmptyState icon={<Megaphone/>} title="No posts scheduled."
                description="Generate content or create a campaign schedule to fill your calendar."
                action={<Btn variant="primary" size="sm" icon={<Sparkles size={14}/>}
                  onClick={() => { window.location.href = "/admin/marketing/generate"; }}>Generate First Post</Btn>}/>
            ) : (
              <div style={{ overflowX:"auto" }}>
                <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
                  <thead>
                    <tr style={{ background:"var(--surface-sunken)", borderTop:"1px solid var(--border)", borderBottom:"1px solid var(--border)" }}>
                      {["Content","Target","Channels","Status","Schedule","AI Cost","Actions"].map(h => (
                        <th key={h} style={{ padding:"10px 16px", textAlign:"left", fontSize:11, fontWeight:700,
                          color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {postItems.map((p, i, arr) => (
                      <tr key={p.id} style={{ borderBottom: i < arr.length-1 ? "1px solid var(--border)" : "none" }}>
                        <td style={{ padding:"12px 16px", maxWidth:220 }}>
                          <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:0 }}>{p.title}</p>
                          <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"2px 0 0" }}>{p.post_type.replace(/_/g," ")}</p>
                        </td>
                        <td style={{ padding:"12px 16px", fontSize:12, color:"var(--text-secondary)" }}>
                          {p.vertical_key ? p.vertical_key.replace(/_/g," ") : "Platform-wide"}
                        </td>
                        <td style={{ padding:"12px 16px", fontSize:12, color:"var(--text-secondary)" }}>
                          {p.channels.length ? p.channels.map(c => PLATFORM_ICON[c] ?? c).join(" ") : "—"}
                        </td>
                        <td style={{ padding:"12px 16px" }}>
                          <Badge variant={STATUS_VARIANT[p.status] ?? "muted"} size="sm">{p.status.replace(/_/g," ")}</Badge>
                        </td>
                        <td style={{ padding:"12px 16px", fontSize:11, color:"var(--text-tertiary)" }}>
                          {p.scheduled_at ? new Date(p.scheduled_at).toLocaleString("en-IN",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}) : "—"}
                        </td>
                        <td style={{ padding:"12px 16px", fontSize:12, color:"var(--text-primary)", fontWeight:600 }}>
                          {p.assets?.reduce((sum,a)=>sum+(a.cost_amount??0),0) ? fmt(p.assets.reduce((sum,a)=>sum+(a.cost_amount??0),0)) : "—"}
                        </td>
                        <td style={{ padding:"12px 16px" }}>
                          <div style={{ display:"flex", gap:6, flexWrap:"wrap" }}>
                            <Btn size="xs" variant="ghost" icon={<Eye size={12}/>} onClick={() => { window.location.href = `/admin/marketing/generate?post_id=${p.id}`; }}>Preview</Btn>
                            {p.approval_status === "pending" && (
                              <Btn size="xs" variant="success" icon={<CheckCircle2 size={12}/>} loading={approveAction.loading} onClick={() => handleApprove(p.id)}>Approve</Btn>
                            )}
                            {p.status === "approved" && (
                              <Btn size="xs" variant="primary" icon={<Send size={12}/>} loading={publishAction.loading} onClick={() => handlePublish(p.id)}>Publish Now</Btn>
                            )}
                            {p.status === "failed" && (
                              <Btn size="xs" variant="secondary" icon={<RotateCcw size={12}/>} loading={retryAction.loading} onClick={() => handleRetry(p.id)}>Retry</Btn>
                            )}
                            {!["published","cancelled","archived"].includes(p.status) && (
                              <Btn size="xs" variant="danger" icon={<XCircle size={12}/>} loading={cancelAction.loading} onClick={() => handleCancel(p.id)}>Cancel</Btn>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          {/* Content Calendar */}
          <Card padding={0}>
            <div style={{ padding:"16px 20px", borderBottom:"1px solid var(--border)",
              display:"flex", alignItems:"center", justifyContent:"space-between" }}>
              <h3 style={{ fontSize:14, fontWeight:600, color:"var(--text-primary)", margin:0 }}>
                Content Calendar — Next 7 Days
              </h3>
              <span style={{ fontSize:12, color:"var(--text-tertiary)" }}>
                {calendar.data?.items.length ?? 0} posts scheduled
              </span>
            </div>
            {calendar.loading ? (
              <div style={{ padding:"16px 20px", display:"flex", flexDirection:"column", gap:8 }}>
                {[...Array(3)].map((_,i) => <Skeleton key={i} height={36}/>)}
              </div>
            ) : (calendar.data?.items ?? []).length === 0 ? (
              <EmptyState icon={<CalendarIcon/>} title="No posts scheduled for this period."
                description="Generate content or create a campaign schedule to fill the calendar."
                action={<div style={{ display:"flex", gap:8 }}>
                  <Btn variant="primary" size="sm" onClick={() => { window.location.href = "/admin/marketing/generate"; }}>Generate First Post</Btn>
                  <Btn variant="secondary" size="sm" onClick={() => { window.location.href = "/admin/marketing/campaigns"; }}>Create Campaign</Btn>
                </div>}/>
            ) : (calendar.data?.items ?? []).map((p, i, arr) => (
              <div key={p.id} style={{ display:"flex", alignItems:"center", gap:12, padding:"10px 20px",
                borderBottom: i < arr.length-1 ? "1px solid var(--border)" : "none" }}>
                <div style={{ width:52, textAlign:"center", flexShrink:0 }}>
                  <p style={{ fontSize:12, fontWeight:700, color:"var(--text-primary)", margin:0 }}>
                    {p.scheduled_at ? new Date(p.scheduled_at).getDate() : "—"}
                  </p>
                  <p style={{ fontSize:10, color:"var(--text-tertiary)", margin:0 }}>
                    {p.scheduled_at ? new Date(p.scheduled_at).toLocaleString("en-IN",{month:"short"}) : ""}
                  </p>
                </div>
                <div style={{ flex:1, minWidth:0 }}>
                  <p style={{ fontSize:12, fontWeight:500, color:"var(--text-primary)", margin:0 }}>{p.title}</p>
                  <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"2px 0 0",
                    overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{p.short_caption ?? p.caption ?? ""}</p>
                </div>
                <Badge variant={STATUS_VARIANT[p.status] ?? "muted"} size="sm">{p.status.replace(/_/g," ")}</Badge>
              </div>
            ))}
          </Card>

          {/* Failed / Retry Queue */}
          <Card padding={0}>
            <div style={{ padding:"16px 20px", borderBottom:"1px solid var(--border)" }}>
              <h3 style={{ fontSize:14, fontWeight:600, color:"var(--text-primary)", margin:0 }}>Failed / Retry Queue</h3>
            </div>
            {failures.loading ? (
              <div style={{ padding:"16px 20px" }}><Skeleton height={60}/></div>
            ) : (failures.data?.items ?? []).length === 0 ? (
              <p style={{ padding:"28px 20px", textAlign:"center", color:"var(--text-tertiary)", fontSize:13, margin:0 }}>
                No failed posts. Everything is publishing cleanly.
              </p>
            ) : (
              <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
                <thead>
                  <tr style={{ background:"var(--surface-sunken)" }}>
                    {["Post","Channel","Failure Reason","Retry Count","Actions"].map(h => (
                      <th key={h} style={{ padding:"8px 16px", textAlign:"left", fontSize:11, fontWeight:700, color:"var(--text-tertiary)" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(failures.data?.items ?? []).map((f, i, arr) => (
                    <tr key={f.id} style={{ borderBottom: i < arr.length-1 ? "1px solid var(--border)" : "none" }}>
                      <td style={{ padding:"10px 16px", fontFamily:"monospace", fontSize:11, color:"var(--text-tertiary)" }}>{f.post_id.slice(0,8)}…</td>
                      <td style={{ padding:"10px 16px", fontSize:12 }}>{PLATFORM_ICON[f.channel] ?? f.channel} {f.channel}</td>
                      <td style={{ padding:"10px 16px", fontSize:12, color:"var(--danger-text)" }}>{f.error_code ?? f.error_message ?? "unknown_error"}</td>
                      <td style={{ padding:"10px 16px", fontSize:12 }}>{f.attempt_number}</td>
                      <td style={{ padding:"10px 16px" }}>
                        <Btn size="xs" variant="secondary" icon={<RotateCcw size={12}/>} onClick={() => handleRetry(f.post_id)}>Retry</Btn>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>

        {/* ── Right sidebar ────────────────────────────────────────────────── */}
        <div style={{ display:"flex", flexDirection:"column", gap:20 }}>
          {/* Platform AI Budget */}
          <Card padding={20}>
            <h3 style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:"0 0 14px" }}>Platform AI Budget</h3>
            {budget.loading ? <Skeleton height={140}/> : b && (
              <>
                <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:8 }}>
                  <span style={{ fontSize:13, color:"var(--text-secondary)" }}>Today</span>
                  <span style={{ fontSize:15, fontWeight:700, color:"var(--text-primary)" }}>
                    {fmt(b.daily_used)} / {fmt(b.daily_budget)}
                  </span>
                </div>
                <div style={{ height:10, background:"var(--border)", borderRadius:999, overflow:"hidden", marginBottom:10 }}>
                  <div style={{ height:"100%", width:`${Math.min(100,(b.daily_used/b.daily_budget)*100)}%`,
                    background: (b.daily_used/b.daily_budget) > 0.8 ? "var(--danger)" : (b.daily_used/b.daily_budget) > 0.6 ? "var(--warning)" : "var(--success)",
                    borderRadius:999, transition:"width 0.5s ease" }}/>
                </div>
                <div style={{ display:"flex", justifyContent:"space-between", marginBottom:14 }}>
                  <span style={{ fontSize:11, color:"var(--text-tertiary)" }}>Remaining: {fmt(b.daily_remaining)}</span>
                  <span style={{ fontSize:11, color:"var(--text-tertiary)" }}>{b.images_generated} images</span>
                </div>
                <div style={{ display:"flex", flexDirection:"column", gap:4, marginBottom:12 }}>
                  <div style={{ display:"flex", justifyContent:"space-between", fontSize:11, color:"var(--text-tertiary)" }}>
                    <span>Monthly Spend</span><span>{fmt(b.monthly_used)} / {fmt(b.monthly_budget)}</span>
                  </div>
                  <div style={{ display:"flex", justifyContent:"space-between", fontSize:11, color:"var(--text-tertiary)" }}>
                    <span>Avg Cost / Image</span><span>{fmt(b.average_cost_per_image)}</span>
                  </div>
                </div>
                <div style={{ padding:"10px 14px", borderRadius:9, background:"var(--info-bg)", border:"1px solid var(--info-border)" }}>
                  <p style={{ fontSize:11, color:"var(--info-text)", margin:0 }}>{b.platform_pays_note}</p>
                </div>
              </>
            )}
          </Card>

          {/* Connected Social Accounts */}
          <Card padding={20}>
            <h3 style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:"0 0 14px" }}>Connected Social Accounts</h3>
            {accounts.loading ? (
              <div style={{ display:"flex", flexDirection:"column", gap:10 }}>{[...Array(2)].map((_,i)=><Skeleton key={i} height={56}/>)}</div>
            ) : (accounts.data?.items ?? []).length === 0 ? (
              <EmptyState icon={<Link2/>} title="No social accounts connected."
                description="Connect a Facebook Page, Instagram Business account, or Google Business Profile to publish scheduled content."
                action={<div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                  <Btn variant="primary" size="sm">Connect Meta Account</Btn>
                  <Btn variant="secondary" size="sm">Connect Google Business Profile</Btn>
                </div>}/>
            ) : (accounts.data?.items ?? []).map(a => (
              <div key={a.id} style={{ display:"flex", alignItems:"center", gap:10, padding:"10px 0", borderBottom:"1px solid var(--border)" }}>
                <span style={{ fontSize:18 }}>{PLATFORM_ICON[a.platform] ?? "🔗"}</span>
                <div style={{ flex:1, minWidth:0 }}>
                  <p style={{ fontSize:12, fontWeight:600, color:"var(--text-primary)", margin:0 }}>{a.account_name}</p>
                  <p style={{ fontSize:10, color:"var(--text-tertiary)", margin:"2px 0 0" }}>
                    Limit {a.daily_post_limit}/day · {a.last_sync_at ? `Synced ${new Date(a.last_sync_at).toLocaleDateString("en-IN")}` : "Never synced"}
                  </p>
                </div>
                <Badge variant={a.token_status === "valid" ? "success" : "warning"} size="sm">{a.token_status}</Badge>
              </div>
            ))}
          </Card>

          {/* Quick Templates */}
          <Card padding={20}>
            <h3 style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:"0 0 14px" }}>Quick Templates</h3>
            {templates.loading ? <Skeleton height={80}/> : (templates.data?.items ?? []).length === 0 ? (
              <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:0 }}>No templates yet.</p>
            ) : (templates.data?.items ?? []).slice(0,5).map(t => (
              <div key={t.id} style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
                padding:"7px 0", borderBottom:"1px solid var(--border)" }}>
                <span style={{ fontSize:12, color:"var(--text-primary)" }}>{t.template_name}</span>
                <Btn size="xs" variant="ghost" onClick={() => { window.location.href = `/admin/marketing/generate?template_id=${t.id}`; }}>Use</Btn>
              </div>
            ))}
          </Card>

          {/* Recent Activity */}
          <Card padding={20}>
            <h3 style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:"0 0 14px" }}>Recent Activity</h3>
            {activity.loading ? <Skeleton height={100}/> : (activity.data?.items ?? []).length === 0 ? (
              <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:0 }}>No activity yet.</p>
            ) : (activity.data?.items ?? []).slice(0,8).map(ev => (
              <div key={ev.id} style={{ padding:"6px 0", borderBottom:"1px solid var(--border)" }}>
                <p style={{ fontSize:11, color:"var(--text-secondary)", margin:0 }}>
                  {ev.action_type.replace(/^marketing\./,"").replace(/[._]/g," ")}
                </p>
                <p style={{ fontSize:10, color:"var(--text-tertiary)", margin:"2px 0 0" }}>
                  {ev.created_at ? new Date(ev.created_at).toLocaleString("en-IN",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}) : ""}
                </p>
              </div>
            ))}
          </Card>
        </div>
      </div>
    </AdminLayout>
  );
}
