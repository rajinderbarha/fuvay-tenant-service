"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import React, { useCallback, useState } from "react";
import { ArrowLeft, Boxes, Clock3, ExternalLink, FolderTree, RotateCcw, ShieldCheck } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import HomeServicesCatalogNav from "../../../../components/catalog/HomeServicesCatalogNav";
import { Badge, Btn, Card, DataTable, Modal, SectionHeader, Skeleton, SummaryCard } from "../../../../components/shared/ui";
import { catalogApi, type MasterServiceEnriched } from "../../../../lib/api";
import { useAction, useApi } from "../../../../hooks/useApi";

type Tab = "overview" | "services" | "activity";

export default function ServiceGroupDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("overview");
  const [restoreOpen, setRestoreOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [servicePage, setServicePage] = useState(1);
  const [servicePageSize, setServicePageSize] = useState(25);
  const detail = useApi(useCallback(() => catalogApi.getServiceGroup(String(id)), [id]), [id]);
  const services = useApi(useCallback(() => catalogApi.listMasterServicesEnterprise({
    serviceGroupId: String(id),
    limit: servicePageSize,
    offset: (servicePage - 1) * servicePageSize,
  }), [id, servicePage, servicePageSize]), [id, servicePage, servicePageSize]);
  const audit = useApi(useCallback(() => catalogApi.getServiceGroupAudit(String(id)), [id]), [id]);
  const restore = useAction(useCallback(async () => {
    await catalogApi.restoreServiceGroup(String(id), reason);
    setRestoreOpen(false); setReason(""); await detail.refetch();
  }, [id, reason, detail]));
  const statusAction = useAction(useCallback(async (action: "activate" | "deactivate") => {
    if (action === "activate") await catalogApi.activateServiceGroup(String(id));
    else await catalogApi.deactivateServiceGroup(String(id));
    await detail.refetch();
    await audit.refetch();
  }, [id, detail, audit]));
  const group = detail.data;

  if (detail.loading) return <AdminLayout activeNav="service-groups"><Skeleton height={500}/></AdminLayout>;
  if (!group) return <AdminLayout activeNav="service-groups"><Card padding={32}>{detail.error ?? "Service group not found."}</Card></AdminLayout>;

  const retired = !!group.deleted_at;
  const serviceTotal = services.data?.total ?? 0;
  const servicePages = Math.max(1, Math.ceil(serviceTotal / servicePageSize));
  const columns = [
    { key: "name", label: "Master Service", render: (_: unknown, row: MasterServiceEnriched) => <span style={{ fontWeight: 700 }}>{row.name}</span> },
    { key: "job_type", label: "Legacy Job Type", render: (_: unknown, row: MasterServiceEnriched) => <Badge variant="muted">{row.job_type || "Blueprint owned"}</Badge> },
    { key: "runtime_readiness", label: "Readiness", render: (_: unknown, row: MasterServiceEnriched) => <Badge variant={row.runtime_readiness === "ready" ? "success" : "warning"}>{row.runtime_readiness.replaceAll("_", " ")}</Badge> },
    { key: "is_active", label: "Status", render: (_: unknown, row: MasterServiceEnriched) => <Badge variant={row.is_active ? "success" : "muted"}>{row.is_active ? "Active" : "Inactive"}</Badge> },
    { key: "id", label: "", render: (_: unknown, row: MasterServiceEnriched) => <Link href={`/admin/catalog-workspace?service_id=${row.id}`}><Btn size="xs" variant="ghost">Open blueprint <ExternalLink size={11}/></Btn></Link> },
  ];

  return <AdminLayout activeNav="service-groups">
    <Btn variant="ghost" size="sm" onClick={() => router.push(retired ? "/admin/service-groups/retired" : "/admin/service-groups")}><ArrowLeft size={13}/> Back to {retired ? "Retired Groups" : "Service Groups"}</Btn>
    <SectionHeader title={group.name} subtitle={`${group.category_name} · ${group.code}`} icon={<FolderTree/>} actions={<div style={{ display:"flex", gap:8 }}>
      <Badge variant={retired ? "muted" : group.status === "active" ? "success" : "warning"}>{retired ? "Retired" : group.status}</Badge>
      {!retired && group.status !== "active" && <Btn variant="primary" size="sm" loading={statusAction.loading} onClick={() => statusAction.execute("activate")}>Activate</Btn>}
      {!retired && group.status === "active" && <Btn variant="secondary" size="sm" loading={statusAction.loading} onClick={() => statusAction.execute("deactivate")}>Deactivate</Btn>}
      {retired && <Btn variant="primary" size="sm" onClick={() => setRestoreOpen(true)}><RotateCcw size={13}/> Restore</Btn>}
    </div>}/>
    {statusAction.error && <Card padding={12} style={{ marginBottom:12, borderColor:"var(--danger-border)", background:"var(--danger-bg)" }}><span style={{ color:"var(--danger-text)", fontSize:13 }}>{statusAction.error}</span></Card>}
    <HomeServicesCatalogNav active="groups"/>
    <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(170px,1fr))", gap:12, marginBottom:18 }}>
      <SummaryCard icon={<Boxes/>} label="Master services" value={group.linked_counts.services}/>
      <SummaryCard icon={<ShieldCheck/>} label="Active services" value={group.linked_counts.active_services}/>
      <SummaryCard icon={<FolderTree/>} label="Providers using" value={group.linked_counts.providers}/>
      <SummaryCard icon={<Clock3/>} label="Readiness" value={group.runtime_readiness.replaceAll("_", " ")}/>
    </div>
    <div style={{ display:"flex", gap:4, borderBottom:"1px solid var(--border)", marginBottom:16 }}>
      {(["overview","services","activity"] as Tab[]).map(key => <button key={key} onClick={() => setTab(key)} style={{ padding:"10px 16px", border:"none", borderBottom:tab===key?"2px solid var(--brand)":"2px solid transparent", background:"none", color:tab===key?"var(--brand)":"var(--text-secondary)", cursor:"pointer", fontWeight:650, textTransform:"capitalize" }}>{key}</button>)}
    </div>
    {tab === "overview" && <div style={{ display:"grid", gridTemplateColumns:"minmax(0,1.4fr) minmax(280px,.6fr)", gap:16 }}>
      <Card><h3 style={{ marginTop:0 }}>Group definition</h3>{[["Category",group.category_name],["Code",group.code],["Slug",group.slug],["Display order",String(group.display_order)],["Description",group.description||"Not provided"],[retired?"Retired":"Updated",retired?new Date(group.deleted_at!).toLocaleString():(group.updated_at?new Date(group.updated_at).toLocaleString():"—")]].map(([label,value]) => <div key={label} style={{ display:"grid", gridTemplateColumns:"140px 1fr", gap:16, padding:"10px 0", borderBottom:"1px solid var(--border)" }}><span style={{ color:"var(--text-tertiary)", fontSize:12 }}>{label}</span><span style={{ fontSize:13 }}>{value}</span></div>)}</Card>
      <Card><h3 style={{ marginTop:0 }}>Connected records</h3><p style={{ fontSize:13, color:"var(--text-secondary)" }}>Open authoritative downstream records with this group already applied.</p><div style={{ display:"grid", gap:8 }}><Link href={`/admin/categories/${group.category_id}`}><Btn variant="secondary" style={{ width:"100%" }}>Open parent category <ExternalLink size={12}/></Btn></Link><Link href={`/admin/master-services?service_group_id=${group.id}`}><Btn variant="secondary" style={{ width:"100%" }}>View master services <ExternalLink size={12}/></Btn></Link></div></Card>
    </div>}
    {tab === "services" && <div>
      <Card padding={0}><DataTable columns={columns as never} rows={(services.data?.services ?? []) as never} loading={services.loading} emptyText="No master services are linked to this group."/></Card>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", gap:12, marginTop:14 }}>
        <span style={{ fontSize:12, color:"var(--text-secondary)" }}>
          {serviceTotal ? `${(servicePage - 1) * servicePageSize + 1}-${Math.min(servicePage * servicePageSize, serviceTotal)} of ${serviceTotal}` : "0 services"}
        </span>
        <div style={{ display:"flex", alignItems:"center", gap:8 }}>
          <select value={servicePageSize} onChange={event => { setServicePageSize(Number(event.target.value)); setServicePage(1); }} style={{ height:32, border:"1px solid var(--border)", borderRadius:8, background:"var(--input-bg)", color:"var(--text-primary)", padding:"0 8px" }}>
            {[25, 50, 100].map(value => <option key={value} value={value}>{value} / page</option>)}
          </select>
          <Btn size="sm" variant="secondary" disabled={servicePage <= 1} onClick={() => setServicePage(page => page - 1)}>Previous</Btn>
          <Badge variant="muted">Page {servicePage} of {servicePages}</Badge>
          <Btn size="sm" variant="secondary" disabled={servicePage >= servicePages} onClick={() => setServicePage(page => page + 1)}>Next</Btn>
        </div>
      </div>
    </div>}
    {tab === "activity" && <Card><h3 style={{ marginTop:0 }}>Audit activity</h3>{(audit.data?.audit_log ?? []).length === 0 ? <p style={{ color:"var(--text-tertiary)", fontSize:13 }}>No audited changes yet.</p> : (audit.data?.audit_log ?? []).map(event => <div key={event.id} style={{ display:"grid", gridTemplateColumns:"130px 1fr auto", gap:12, padding:"11px 0", borderBottom:"1px solid var(--border)", alignItems:"center" }}><Badge variant="muted">{event.action}</Badge><div><div style={{ fontSize:13 }}>{event.change_summary || "Service group changed"}</div><div style={{ fontSize:11, color:"var(--text-tertiary)" }}>{event.actor_role || "system"}{event.request_id ? ` · ${event.request_id}`:""}</div></div><span style={{ fontSize:11, color:"var(--text-tertiary)" }}>{event.created_at ? new Date(event.created_at).toLocaleString():"—"}</span></div>)}</Card>}
    <Modal open={restoreOpen} onClose={() => setRestoreOpen(false)} title="Restore service group"><p style={{ color:"var(--text-secondary)", fontSize:13 }}>Restored groups return as inactive so an administrator can review them before activation.</p><textarea value={reason} onChange={e=>setReason(e.target.value)} placeholder="Reason for restoring (minimum 10 characters)" rows={3} style={{ width:"100%", boxSizing:"border-box", padding:10, borderRadius:8, border:"1px solid var(--border)", background:"var(--input-bg)", color:"var(--text-primary)" }}/>{restore.error && <p style={{ color:"var(--danger-text)", fontSize:12 }}>{restore.error}</p>}<div style={{ display:"flex", justifyContent:"flex-end", gap:8, marginTop:14 }}><Btn variant="secondary" onClick={()=>setRestoreOpen(false)}>Cancel</Btn><Btn variant="primary" disabled={reason.trim().length<10} loading={restore.loading} onClick={()=>restore.execute()}>Restore as inactive</Btn></div></Modal>
  </AdminLayout>;
}
