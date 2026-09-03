"use client";

import React, { useCallback, useState } from "react";
import { AlertTriangle, CheckCircle2, Clock, FileText, ShieldCheck, Upload, Users } from "lucide-react";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { Badge, Btn, Card, Skeleton } from "../../../../components/shared/ui";
import { MediaUploader } from "../../../../components/media/MediaUploader";
import { useApi } from "../../../../hooks/useApi";
import { useTenant } from "../../../../hooks/useTenant";
import { businessProfileApi, tenantVerificationDocumentsApi, type BusinessProfile } from "../../../../lib/api";

type Doc = {
  key: string; label: string; required: boolean; accepted_examples: string[];
  effective_status: string; allowed_actions: string[];
  activation_impact: { human_message: string };
  document: null | { id: string; version: number; uploaded_at: string | null };
};
type Workspace = {
  summary: { total_documents: number; verified: number; under_review: number; action_required: number };
  business_documents: { items: Doc[] };
  technicians: { items: Array<{ staff_member_id: string; full_name: string; role: string; verified: number; required_documents: number; assignment_eligible: boolean }> };
  permissions: { can_upload: boolean };
};
type PendingProfile = BusinessProfile & { pending_changes?: { fields?: Record<string, unknown>; documents_to_revalidate?: string[] } | null };

const statusMeta: Record<string, { label: string; variant: "success" | "warning" | "danger" | "info" }> = {
  verified: { label: "Verified", variant: "success" },
  pending_review: { label: "Under admin review", variant: "info" },
  changes_requested: { label: "Changes requested", variant: "warning" },
  rejected: { label: "Rejected", variant: "danger" },
  expired: { label: "Expired", variant: "danger" },
  not_uploaded: { label: "Not uploaded", variant: "warning" },
};

export default function VerificationDocumentsPage() {
  const tenant = useTenant();
  const [tab, setTab] = useState<"business" | "technicians">("business");
  const [uploadKey, setUploadKey] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const docs = useApi(useCallback(() => tenantVerificationDocumentsApi.workspace<Workspace>(), []), []);
  const profile = useApi(useCallback(() => businessProfileApi.get() as Promise<PendingProfile>, []), []);

  async function submit(docType: string, mediaAssetId: string) {
    setActionError(null);
    try {
      await tenantVerificationDocumentsApi.submit({ doc_type: docType, media_asset_id: mediaAssetId });
      setUploadKey(null);
      docs.refetch();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Could not submit this document.");
    }
  }

  const data = docs.data;
  const pending = profile.data?.pending_changes;
  return <TenantLayout activeNav="verification-documents">
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, flexWrap: "wrap", marginBottom: 18 }}>
      <div>
        <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", color: "var(--brand)", margin: "0 0 4px" }}>BUSINESS</p>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 5px" }}>Documents & Verification</h1>
        <p style={{ fontSize: 13.5, color: "var(--text-secondary)", margin: 0 }}>Manage the same verification records approved during setup.</p>
      </div>
      {data && <Badge variant={data.summary.action_required ? "warning" : "success"} size="lg">
        {data.summary.action_required ? `${data.summary.action_required} action required` : "Documents current"}
      </Badge>}
    </div>

    {pending && <Card style={{ marginBottom: 18, borderColor: "var(--warning-border)" }}>
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
        <ShieldCheck size={18} style={{ color: "var(--warning-text)", marginTop: 2 }}/>
        <div>
          <p style={{ margin: "0 0 4px", fontSize: 14, fontWeight: 700 }}>Fresh documents required for your profile change</p>
          <p style={{ margin: "0 0 8px", fontSize: 12.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>
            Your current approved details stay published. Upload the supporting documents below; Fuvay reviews them and the profile change together.
          </p>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>{(pending.documents_to_revalidate ?? []).map(key => <Badge key={key} variant="warning" size="sm">{key.replace(/_/g, " ")}</Badge>)}</div>
        </div>
      </div>
    </Card>}

    {actionError && <div role="alert" style={{ padding: "10px 14px", marginBottom: 14, borderRadius: 8, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", color: "var(--danger-text)", fontSize: 13 }}>{actionError}</div>}
    {docs.loading ? <Skeleton height={420}/> : docs.error || !data ? <Card><p role="alert" style={{ margin: 0, color: "var(--danger-text)" }}>{docs.error ?? "Could not load verification documents."}</p></Card> : <>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12, marginBottom: 18 }}>
        <Summary label="Total" value={data.summary.total_documents} icon={<FileText size={17}/>}/>
        <Summary label="Verified" value={data.summary.verified} icon={<CheckCircle2 size={17}/>}/>
        <Summary label="Under review" value={data.summary.under_review} icon={<Clock size={17}/>}/>
        <Summary label="Action required" value={data.summary.action_required} icon={<AlertTriangle size={17}/>}/>
      </div>
      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", marginBottom: 16 }}>
        <Tab active={tab === "business"} onClick={() => setTab("business")} icon={<FileText size={14}/>}>Business documents</Tab>
        <Tab active={tab === "technicians"} onClick={() => setTab("technicians")} icon={<Users size={14}/>}>Technician documents</Tab>
      </div>
      {tab === "business" ? <Card padding={0}>
        {data.business_documents.items.map((item, index) => {
          const meta = statusMeta[item.effective_status] ?? statusMeta.not_uploaded;
          const canUpload = data.permissions.can_upload && item.effective_status !== "pending_review";
          return <div key={item.key} style={{ borderBottom: index < data.business_documents.items.length - 1 ? "1px solid var(--border)" : "none" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "16px 18px", flexWrap: "wrap" }}>
              <div style={{ width: 40, height: 40, borderRadius: 9, background: "var(--surface-sunken)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-tertiary)" }}><FileText size={18}/></div>
              <div style={{ flex: 1, minWidth: 220 }}><p style={{ margin: "0 0 3px", fontSize: 13.5, fontWeight: 700 }}>{item.label}</p><p style={{ margin: 0, fontSize: 11.5, color: "var(--text-tertiary)" }}>{item.activation_impact.human_message}</p></div>
              <Badge variant="muted" size="sm">{item.required ? "Required" : "Optional"}</Badge>
              <Badge variant={meta.variant} size="sm">{meta.label}</Badge>
              {canUpload && <Btn variant="secondary" size="sm" icon={<Upload size={13}/>} onClick={() => setUploadKey(uploadKey === item.key ? null : item.key)}>{item.document ? "Replace" : "Upload"}</Btn>}
            </div>
            {uploadKey === item.key && <div style={{ padding: "0 18px 18px 72px" }}>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 10px" }}>Accepted: {item.accepted_examples.join(", ")}</p>
              <MediaUploader mediaContext="provider_document" ownerType="tenant" ownerId={tenant.tenantId ?? ""} accept="application/pdf,image/jpeg,image/png,image/webp" multiple={false} canDelete={false} label="Choose replacement document" onUploaded={asset => submit(item.key, asset.id)}/>
            </div>}
          </div>;
        })}
      </Card> : <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 12 }}>
        {data.technicians.items.map(person => <Card key={person.staff_member_id}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}><div><p style={{ margin: "0 0 3px", fontSize: 14, fontWeight: 700 }}>{person.full_name}</p><p style={{ margin: 0, fontSize: 12, color: "var(--text-tertiary)" }}>{person.role}</p></div><Badge variant={person.assignment_eligible ? "success" : "warning"}>{person.assignment_eligible ? "Eligible" : "Needs attention"}</Badge></div>
          <p style={{ margin: "14px 0 0", fontSize: 12.5, color: "var(--text-secondary)" }}>{person.verified} of {person.required_documents} required documents verified</p>
        </Card>)}
      </div>}
    </>}
  </TenantLayout>;
}

function Summary({ label, value, icon }: { label: string; value: number; icon: React.ReactNode }) {
  return <Card><div style={{ display: "flex", alignItems: "center", gap: 10 }}><span style={{ color: "var(--brand)" }}>{icon}</span><div><p style={{ margin: 0, fontSize: 11.5, color: "var(--text-tertiary)" }}>{label}</p><p style={{ margin: "2px 0 0", fontSize: 21, fontWeight: 800 }}>{value}</p></div></div></Card>;
}
function Tab({ active, onClick, icon, children }: { active: boolean; onClick: () => void; icon: React.ReactNode; children: React.ReactNode }) {
  return <button type="button" onClick={onClick} style={{ display: "flex", alignItems: "center", gap: 7, padding: "10px 14px", border: "none", borderBottom: active ? "2px solid var(--brand)" : "2px solid transparent", background: "none", color: active ? "var(--brand)" : "var(--text-secondary)", font: "inherit", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>{icon}{children}</button>;
}
