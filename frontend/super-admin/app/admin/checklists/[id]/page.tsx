"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import React, { useCallback, useState } from "react";
import { ArrowLeft, CheckCircle2, ClipboardList, Clock3, Layers3, ListChecks, RotateCcw } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import HomeServicesCatalogNav from "../../../../components/catalog/HomeServicesCatalogNav";
import { Badge, Btn, Card, Modal, SectionHeader, Skeleton, SummaryCard } from "../../../../components/shared/ui";
import { checklistCatalogApi } from "../../../../lib/api";
import { useAction, useApi } from "../../../../hooks/useApi";

type Tab = "overview"|"content"|"versions"|"activity";

export default function ChecklistDetailPage(){
  const {id}=useParams<{id:string}>(); const router=useRouter(); const [tab,setTab]=useState<Tab>("overview");
  const [restoreOpen,setRestoreOpen]=useState(false); const [reason,setReason]=useState("");
  const detail=useApi(useCallback(()=>checklistCatalogApi.getTemplate(String(id)),[id]),[id]);
  const latest=useApi(useCallback(()=>checklistCatalogApi.getLatestVersion(String(id)),[id]),[id]);
  const audit=useApi(useCallback(()=>checklistCatalogApi.getTemplateAudit(String(id)),[id]),[id]);
  const restore=useAction(useCallback(async()=>{await checklistCatalogApi.restoreTemplate(String(id),reason);setRestoreOpen(false);setReason("");await detail.refetch();},[id,reason,detail]));
  if(detail.loading)return <AdminLayout activeNav="checklist-templates"><Skeleton height={520}/></AdminLayout>;
  const template=detail.data; if(!template)return <AdminLayout activeNav="checklist-templates"><Card padding={32}>{detail.error??"Checklist not found."}</Card></AdminLayout>;
  const retired=template.status==="archived"; const content=latest.data;
  return <AdminLayout activeNav="checklist-templates">
    <Btn variant="ghost" size="sm" onClick={()=>router.push(retired?"/admin/checklists?status=archived":"/admin/checklists")}><ArrowLeft size={13}/> Back to checklist library</Btn>
    <SectionHeader title={template.name} subtitle={`${template.code} · ${template.purpose.replaceAll("_"," ")}`} icon={<ClipboardList/>} actions={<div style={{display:"flex",gap:8,alignItems:"center"}}><Badge variant={retired?"muted":template.latest_version?.status==="PUBLISHED"?"success":"warning"}>{retired?"Retired":template.latest_version?.status??"Draft"}</Badge>{retired&&<Btn variant="primary" size="sm" onClick={()=>setRestoreOpen(true)}><RotateCcw size={13}/> Restore</Btn>}</div>}/>
    <HomeServicesCatalogNav active="checklists"/>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(170px,1fr))",gap:12,marginBottom:18}}>
      <SummaryCard icon={<Layers3/>} label="Versions" value={template.versions.length}/>
      <SummaryCard icon={<ListChecks/>} label="All mappings" value={template.mapping_count}/>
      <SummaryCard icon={<CheckCircle2/>} label="Active mappings" value={template.active_mapping_count??0}/>
      <SummaryCard icon={<Clock3/>} label="Historical instances" value={template.instance_count}/>
    </div>
    <div style={{display:"flex",gap:4,borderBottom:"1px solid var(--border)",marginBottom:16}}>{(["overview","content","versions","activity"] as Tab[]).map(key=><button key={key} onClick={()=>setTab(key)} style={{padding:"10px 16px",border:"none",borderBottom:tab===key?"2px solid var(--brand)":"2px solid transparent",background:"none",color:tab===key?"var(--brand)":"var(--text-secondary)",cursor:"pointer",fontWeight:650,textTransform:"capitalize"}}>{key}</button>)}</div>
    {tab==="overview"&&<div style={{display:"grid",gridTemplateColumns:"minmax(0,1.35fr) minmax(280px,.65fr)",gap:16}}>
      <Card><h3 style={{marginTop:0}}>Template governance</h3>{[["Code",template.code],["Purpose",template.purpose.replaceAll("_"," ")],["Owner scope",template.owner_scope],["Description",template.description||"Not provided"],["Created",template.created_at?new Date(template.created_at).toLocaleString():"—"],["Updated",template.updated_at?new Date(template.updated_at).toLocaleString():"—"]].map(([label,value])=><div key={label} style={{display:"grid",gridTemplateColumns:"130px 1fr",gap:16,padding:"10px 0",borderBottom:"1px solid var(--border)"}}><span style={{fontSize:12,color:"var(--text-tertiary)"}}>{label}</span><span style={{fontSize:13}}>{value}</span></div>)}</Card>
      <Card><h3 style={{marginTop:0}}>Runtime contract</h3><p style={{fontSize:13,color:"var(--text-secondary)"}}>Only published versions on active mappings reach native staff jobs. Existing job instances retain their exact version snapshot forever.</p>{retired&&<div style={{padding:12,border:"1px solid var(--warning-border)",background:"var(--warning-bg)",borderRadius:8,fontSize:12,color:"var(--warning-text)"}}><strong>Retired:</strong> {template.archive_reason||"No reason captured"}<br/>{template.archived_at?new Date(template.archived_at).toLocaleString():""}</div>}<Link href="/admin/catalog-workspace"><Btn variant="secondary" style={{width:"100%",marginTop:12}}>Open job-type blueprint workspace</Btn></Link></Card>
    </div>}
    {tab==="content"&&<Card><h3 style={{marginTop:0}}>Latest version content</h3>{latest.loading?<Skeleton height={180}/>:!content?<p>{latest.error??"No version content."}</p>:content.sections.length===0?<p style={{color:"var(--text-tertiary)",fontSize:13}}>No sections authored.</p>:content.sections.map(section=><div key={section.id} style={{marginBottom:18}}><div style={{fontWeight:700,fontSize:13,marginBottom:8}}>{section.title} <Badge variant="muted">{section.items.length} items</Badge></div>{section.items.map(item=><div key={item.id} style={{display:"flex",gap:8,alignItems:"center",padding:"9px 11px",border:"1px solid var(--border)",borderRadius:8,marginBottom:6}}><Badge variant="info">{item.item_type}</Badge><span style={{flex:1,fontSize:13}}>{item.label}</span>{item.is_required&&<Badge variant="warning">Required</Badge>}{item.evidence_required&&<Badge variant="muted">Evidence</Badge>}{item.customer_visible&&<Badge variant="success">Customer visible</Badge>}</div>)}</div>)}</Card>}
    {tab==="versions"&&<Card><h3 style={{marginTop:0}}>Immutable version history</h3>{template.versions.map(version=><div key={version.id} style={{display:"grid",gridTemplateColumns:"80px 120px 1fr auto",gap:12,alignItems:"center",padding:"11px 0",borderBottom:"1px solid var(--border)"}}><strong>v{version.version_number}</strong><Badge variant={version.status==="PUBLISHED"?"success":version.status==="DRAFT"?"warning":"muted"}>{version.status}</Badge><span style={{fontSize:13,color:"var(--text-secondary)"}}>{version.change_summary||"No change summary"}</span><span style={{fontSize:11,color:"var(--text-tertiary)"}}>{version.published_at?new Date(version.published_at).toLocaleString():"Not published"}</span></div>)}</Card>}
    {tab==="activity"&&<Card><h3 style={{marginTop:0}}>Audit activity</h3>{(audit.data?.items??[]).length===0?<p style={{fontSize:13,color:"var(--text-tertiary)"}}>No audited changes yet.</p>:(audit.data?.items??[]).map(event=><div key={event.id} style={{display:"grid",gridTemplateColumns:"140px 1fr auto",gap:12,padding:"11px 0",borderBottom:"1px solid var(--border)",alignItems:"center"}}><Badge variant="muted">{event.action}</Badge><div><div style={{fontSize:13}}>{event.change_summary||"Checklist changed"}</div><div style={{fontSize:11,color:"var(--text-tertiary)"}}>{event.actor_role||"system"}{event.request_id?` · ${event.request_id}`:""}</div></div><span style={{fontSize:11,color:"var(--text-tertiary)"}}>{event.created_at?new Date(event.created_at).toLocaleString():"—"}</span></div>)}</Card>}
    <Modal open={restoreOpen} onClose={()=>setRestoreOpen(false)} title="Restore checklist"><p style={{fontSize:13,color:"var(--text-secondary)"}}>Previously disabled mappings remain disabled; review and enable each intended runtime mapping explicitly.</p><textarea value={reason} onChange={event=>setReason(event.target.value)} rows={3} placeholder="Reason for restoring (minimum 5 characters)" style={{width:"100%",boxSizing:"border-box",padding:10,borderRadius:8,border:"1px solid var(--border)",background:"var(--input-bg)",color:"var(--text-primary)"}}/>{restore.error&&<p style={{fontSize:12,color:"var(--danger-text)"}}>{restore.error}</p>}<div style={{display:"flex",justifyContent:"flex-end",gap:8,marginTop:14}}><Btn variant="secondary" onClick={()=>setRestoreOpen(false)}>Cancel</Btn><Btn variant="primary" disabled={reason.trim().length<5} loading={restore.loading} onClick={()=>restore.execute()}>Restore</Btn></div></Modal>
  </AdminLayout>;
}
