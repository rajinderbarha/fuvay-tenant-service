"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import React, { useCallback, useState } from "react";
import { ArrowLeft, Boxes, Clock3, ExternalLink, Layers3, RotateCcw, ShieldCheck, Users } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import HomeServicesCatalogNav from "../../../../components/catalog/HomeServicesCatalogNav";
import { Badge, Btn, Card, Modal, SectionHeader, Skeleton, SummaryCard } from "../../../../components/shared/ui";
import { catalogApi } from "../../../../lib/api";
import { useAction, useApi } from "../../../../hooks/useApi";

type Tab = "overview" | "configuration" | "activity";

const readinessTone = (value: string) => value === "ready" ? "success" : value === "inactive" ? "muted" : "warning";

export default function MasterServiceDetailPage() {
  const { id } = useParams<{ id:string }>();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("overview");
  const [restoreOpen, setRestoreOpen] = useState(false);
  const [reason, setReason] = useState("");
  const detail = useApi(useCallback(()=>catalogApi.getMasterService(String(id), true),[id]),[id]);
  const audit = useApi(useCallback(()=>catalogApi.getMasterServiceAudit(String(id)),[id]),[id]);
  const statusAction = useAction(useCallback(async(action:"activate"|"deactivate")=>{
    if(action === "activate") await catalogApi.activateMasterService(String(id));
    else await catalogApi.deactivateMasterService(String(id));
    await detail.refetch(); await audit.refetch();
  },[id,detail,audit]));
  const restore = useAction(useCallback(async()=>{
    await catalogApi.restoreMasterService(String(id),reason);
    setRestoreOpen(false); setReason(""); await detail.refetch(); await audit.refetch();
  },[id,reason,detail,audit]));

  if(detail.loading) return <AdminLayout activeNav="master-services"><Skeleton height={520}/></AdminLayout>;
  const service = detail.data;
  if(!service) return <AdminLayout activeNav="master-services"><Card padding={32}>{detail.error ?? "Master service not found."}</Card></AdminLayout>;
  const retired = !!service.deleted_at;
  const counts = service.linked_counts;

  return <AdminLayout activeNav="master-services">
    <div className="catalog-admin-page catalog-detail-page">
    <Btn variant="ghost" size="sm" onClick={()=>router.push(retired?"/admin/master-services?lifecycle=retired":"/admin/master-services")}><ArrowLeft size={13}/> Back to Master Services</Btn>
    <SectionHeader title={service.name} subtitle={`${service.category_name} · ${service.group_name ?? "No service group"}`} icon={<Boxes/>} actions={<div style={{display:"flex",gap:8,alignItems:"center"}}>
      <Badge variant={retired?"muted":service.is_active?"success":"warning"}>{retired?"Retired":service.is_active?"Active":"Inactive"}</Badge>
      {!retired && !service.is_active && <Btn variant="primary" size="sm" loading={statusAction.loading} onClick={()=>statusAction.execute("activate")}>Activate</Btn>}
      {!retired && service.is_active && <Btn variant="secondary" size="sm" loading={statusAction.loading} onClick={()=>statusAction.execute("deactivate")}>Deactivate</Btn>}
      {retired && <Btn variant="primary" size="sm" onClick={()=>setRestoreOpen(true)}><RotateCcw size={13}/> Restore</Btn>}
    </div>}/>
    {statusAction.error && <Card padding={12} style={{marginBottom:12,borderColor:"var(--danger-border)",background:"var(--danger-bg)"}}><span style={{color:"var(--danger-text)",fontSize:13}}>{statusAction.error}</span></Card>}
    <HomeServicesCatalogNav active="services"/>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(165px,1fr))",gap:12,marginBottom:18}}>
      <SummaryCard icon={<Layers3/>} label="Job types" value={counts.job_types}/>
      <SummaryCard icon={<ShieldCheck/>} label="Published workflows" value={counts.workflows}/>
      <SummaryCard icon={<Users/>} label="Provider workspaces" value={counts.providers}/>
      <SummaryCard icon={<Boxes/>} label="Options / problems" value={`${counts.options} / ${counts.issues}`}/>
      <SummaryCard icon={<Clock3/>} label="Runtime readiness" value={service.runtime_readiness.replaceAll("_"," ")}/>
    </div>
    <div style={{display:"flex",gap:4,borderBottom:"1px solid var(--border)",marginBottom:16}}>{(["overview","configuration","activity"] as Tab[]).map(key=><button key={key} onClick={()=>setTab(key)} style={{padding:"10px 16px",border:"none",borderBottom:tab===key?"2px solid var(--brand)":"2px solid transparent",background:"none",color:tab===key?"var(--brand)":"var(--text-secondary)",cursor:"pointer",fontWeight:650,textTransform:"capitalize"}}>{key}</button>)}</div>
    {tab === "overview" && <div style={{display:"grid",gridTemplateColumns:"minmax(0,1.35fr) minmax(290px,.65fr)",gap:16}}>
      <Card><h3 style={{marginTop:0}}>Service identity</h3>{[["Category",service.category_name],["Service group",service.group_name??"Not assigned"],["Slug",service.slug],["Display order",String(service.display_order??0)],["Description",service.description||"Not provided"],[retired?"Retired":"Updated",retired?new Date(service.deleted_at!).toLocaleString():(service.updated_at?new Date(service.updated_at).toLocaleString():"—")]].map(([label,value])=><div key={label} style={{display:"grid",gridTemplateColumns:"140px 1fr",gap:16,padding:"10px 0",borderBottom:"1px solid var(--border)"}}><span style={{color:"var(--text-tertiary)",fontSize:12}}>{label}</span><span style={{fontSize:13}}>{value}</span></div>)}</Card>
      <Card><h3 style={{marginTop:0}}>Authoritative workspaces</h3><p style={{fontSize:13,color:"var(--text-secondary)"}}>Identity lives here. Job behavior lives in Catalog Workspace. Provider prices remain tenant-owned.</p><div style={{display:"grid",gap:8}}><Link href={`/admin/categories/${service.category_id}`}><Btn variant="secondary" style={{width:"100%"}}>Open parent category <ExternalLink size={12}/></Btn></Link>{service.service_group_id&&<Link href={`/admin/service-groups/${service.service_group_id}`}><Btn variant="secondary" style={{width:"100%"}}>Open service group <ExternalLink size={12}/></Btn></Link>}<Link href={`/admin/catalog-workspace?service_id=${service.id}`}><Btn variant="primary" style={{width:"100%"}}>Configure job-type blueprint <ExternalLink size={12}/></Btn></Link></div></Card>
    </div>}
    {tab === "configuration" && <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(280px,1fr))",gap:16}}>
      <Card><h3 style={{marginTop:0}}>Blueprint readiness</h3><Badge variant={readinessTone(service.runtime_readiness)}>{service.runtime_readiness.replaceAll("_"," ")}</Badge><p style={{fontSize:13,color:"var(--text-secondary)"}}>A service needs at least one active job type and a published current workflow before tenant setup and native booking can safely consume it.</p><Link href={`/admin/catalog-workspace?service_id=${service.id}`}><Btn variant="primary">Resolve in Catalog Workspace</Btn></Link></Card>
      <Card><h3 style={{marginTop:0}}>Mapped catalog data</h3>{[["Service types",counts.service_types],["Brands",counts.brands],["Options",counts.options],["Problems",counts.issues],["Job types",counts.job_types],["Published workflows",counts.workflows]].map(([label,value])=><div key={label} style={{display:"flex",justifyContent:"space-between",padding:"9px 0",borderBottom:"1px solid var(--border)",fontSize:13}}><span style={{color:"var(--text-secondary)"}}>{label}</span><strong>{value}</strong></div>)}</Card>
      <Card><h3 style={{marginTop:0}}>Provider adoption</h3><strong style={{fontSize:30}}>{counts.providers}</strong><p style={{fontSize:13,color:"var(--text-secondary)"}}>Active provider workspaces currently enabling this service. Retirement is blocked until this reaches zero.</p></Card>
    </div>}
    {tab === "activity" && <Card><h3 style={{marginTop:0}}>Audit activity</h3>{(audit.data?.audit_log??[]).length===0?<p style={{fontSize:13,color:"var(--text-tertiary)"}}>No audited changes yet.</p>:(audit.data?.audit_log??[]).map(event=><div key={event.id} style={{display:"grid",gridTemplateColumns:"120px 1fr auto",gap:12,padding:"11px 0",borderBottom:"1px solid var(--border)",alignItems:"center"}}><Badge variant="muted">{event.action}</Badge><div><div style={{fontSize:13}}>{event.change_summary||"Master service changed"}</div><div style={{fontSize:11,color:"var(--text-tertiary)"}}>{event.actor_role||"system"}{event.request_id?` · ${event.request_id}`:""}</div></div><span style={{fontSize:11,color:"var(--text-tertiary)"}}>{event.created_at?new Date(event.created_at).toLocaleString():"—"}</span></div>)}</Card>}
    <Modal open={restoreOpen} onClose={()=>setRestoreOpen(false)} title="Restore master service"><p style={{fontSize:13,color:"var(--text-secondary)"}}>The service returns as inactive. Review its parent hierarchy and blueprint before activation.</p><textarea value={reason} onChange={event=>setReason(event.target.value)} rows={3} placeholder="Reason for restoring (minimum 10 characters)" style={{width:"100%",boxSizing:"border-box",padding:10,borderRadius:8,border:"1px solid var(--border)",background:"var(--input-bg)",color:"var(--text-primary)"}}/>{restore.error&&<p style={{fontSize:12,color:"var(--danger-text)"}}>{restore.error}</p>}<div style={{display:"flex",justifyContent:"flex-end",gap:8,marginTop:14}}><Btn variant="secondary" onClick={()=>setRestoreOpen(false)}>Cancel</Btn><Btn variant="primary" disabled={reason.trim().length<10} loading={restore.loading} onClick={()=>restore.execute()}>Restore as inactive</Btn></div></Modal>
    </div>
  </AdminLayout>;
}
