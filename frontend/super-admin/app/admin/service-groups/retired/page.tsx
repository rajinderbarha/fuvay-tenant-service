"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import React, { useCallback, useState } from "react";
import { Archive, ArrowLeft, Eye, RotateCcw, Search } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import HomeServicesCatalogNav from "../../../../components/catalog/HomeServicesCatalogNav";
import OperationsDirectoryControls from "../../../../components/enterprise/OperationsDirectoryControls";
import type { ColumnDef } from "../../../../components/enterprise/EnterpriseColumnManager";
import { Badge, Btn, Card, DataTable, Modal, SectionHeader } from "../../../../components/shared/ui";
import { catalogApi, type ServiceGroupEnriched } from "../../../../lib/api";
import { useAction, useApi } from "../../../../hooks/useApi";

const DEFAULT_COLUMNS: ColumnDef[] = [
  { key:"name", label:"Retired Group", visible:true, order:0 },
  { key:"category_name", label:"Category", visible:true, order:1 },
  { key:"linked_counts", label:"Linked Records", visible:true, order:2 },
  { key:"deleted_at", label:"Retired", visible:true, order:3 },
  { key:"id", label:"Actions", visible:true, order:4 },
];

export default function RetiredServiceGroupsPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [columnsConfig, setColumnsConfig] = useState<ColumnDef[]>(DEFAULT_COLUMNS);
  const [restore, setRestore] = useState<ServiceGroupEnriched | null>(null);
  const [reason, setReason] = useState("");
  const groups = useApi(useCallback(() => catalogApi.listServiceGroups({ q:query||undefined, retired:true, sortBy:"updated_at", sortDir:"desc", limit:pageSize, offset:(page-1)*pageSize }), [query,page,pageSize]), [query,page,pageSize]);
  const restoreAction = useAction(useCallback(async () => {
    if (!restore) return;
    await catalogApi.restoreServiceGroup(restore.id, reason);
    setRestore(null); setReason(""); groups.refetch();
  }, [restore, reason, groups]));
  const rows = groups.data?.groups ?? [];
  const pages = Math.max(1, Math.ceil((groups.data?.total ?? 0)/pageSize));
  const allColumns = [
    { key:"name", label:"Retired Group", render:(_:unknown,row:ServiceGroupEnriched)=><div><b>{row.name}</b><div style={{fontSize:11,color:"var(--text-tertiary)"}}>{row.code} · {row.slug}</div></div> },
    { key:"category_name", label:"Category" },
    { key:"linked_counts", label:"Linked records", render:(_:unknown,row:ServiceGroupEnriched)=><span>{row.linked_counts.services} services · {row.linked_counts.providers} providers</span> },
    { key:"deleted_at", label:"Retired", render:(_:unknown,row:ServiceGroupEnriched)=><span>{row.deleted_at?new Date(row.deleted_at).toLocaleString():"—"}</span> },
    { key:"id", label:"Actions", render:(_:unknown,row:ServiceGroupEnriched)=><div style={{display:"flex",gap:6}} onClick={e=>e.stopPropagation()}><Link href={`/admin/service-groups/${row.id}`}><Btn size="xs" variant="ghost"><Eye size={11}/> View</Btn></Link><Btn size="xs" variant="primary" onClick={()=>setRestore(row)}><RotateCcw size={11}/> Restore</Btn></div> },
  ];
  const visibleKeys = new Set(columnsConfig.filter(column => column.visible).map(column => column.key));
  const columns = allColumns.filter(column => visibleKeys.has(column.key));
  return <AdminLayout activeNav="service-groups">
    <Link href="/admin/service-groups"><Btn variant="ghost" size="sm"><ArrowLeft size={13}/> Active Service Groups</Btn></Link>
    <SectionHeader title="Retired Service Groups" subtitle="Recoverable catalog records removed from active configuration." icon={<Archive/>}/>
    <HomeServicesCatalogNav active="groups"/>
    <OperationsDirectoryControls
      resourceKey="admin_service_groups"
      filters={{ q: query, retired: true }}
      sort={{ sort_by: "updated_at", sort_direction: "desc" }}
      columns={columnsConfig}
      onColumnsChange={setColumnsConfig}
      onApplyView={(filters) => { setQuery(String(filters.q ?? filters.search ?? "")); setPage(1); }}
    />
    <Card padding={14} style={{marginBottom:14}}><div style={{position:"relative"}}><Search size={14} style={{position:"absolute",left:11,top:10,color:"var(--text-tertiary)"}}/><input value={query} onChange={e=>{setQuery(e.target.value);setPage(1)}} placeholder="Search retired name, code, or slug…" style={{width:"100%",boxSizing:"border-box",height:36,padding:"0 10px 0 34px",border:"1px solid var(--border)",borderRadius:8,background:"var(--input-bg)",color:"var(--text-primary)"}}/></div></Card>
    <Card padding={0}><DataTable columns={columns as never} rows={rows as never} loading={groups.loading} emptyText="No retired service groups." onRowClick={row=>router.push(`/admin/service-groups/${(row as unknown as ServiceGroupEnriched).id}`)}/></Card>
    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginTop:14}}><span style={{fontSize:12,color:"var(--text-secondary)"}}>{groups.data?.total??0} retired groups</span><div style={{display:"flex",gap:8,alignItems:"center"}}><select value={pageSize} onChange={e=>{setPageSize(Number(e.target.value));setPage(1)}} style={{height:32,border:"1px solid var(--border)",borderRadius:8,background:"var(--input-bg)",color:"var(--text-primary)",padding:"0 8px"}}>{[25,50,100].map(value=><option key={value} value={value}>{value} / page</option>)}</select><Btn variant="secondary" size="sm" disabled={page<=1} onClick={()=>setPage(p=>p-1)}>Previous</Btn><Badge variant="muted">Page {page} of {pages}</Badge><Btn variant="secondary" size="sm" disabled={page>=pages} onClick={()=>setPage(p=>p+1)}>Next</Btn></div></div>
    <Modal open={!!restore} onClose={()=>setRestore(null)} title={`Restore ${restore?.name??"group"}`}><p style={{fontSize:13,color:"var(--text-secondary)"}}>The group will return as inactive. Review linked services before activating it.</p><textarea rows={3} value={reason} onChange={e=>setReason(e.target.value)} placeholder="Restore reason (minimum 10 characters)" style={{width:"100%",boxSizing:"border-box",padding:10,border:"1px solid var(--border)",borderRadius:8,background:"var(--input-bg)",color:"var(--text-primary)"}}/>{restoreAction.error&&<p style={{fontSize:12,color:"var(--danger-text)"}}>{restoreAction.error}</p>}<div style={{display:"flex",justifyContent:"flex-end",gap:8,marginTop:14}}><Btn variant="secondary" onClick={()=>setRestore(null)}>Cancel</Btn><Btn variant="primary" disabled={reason.trim().length<10} loading={restoreAction.loading} onClick={()=>restoreAction.execute()}>Restore as inactive</Btn></div></Modal>
  </AdminLayout>;
}
