"use client";
/**
 * Tenant Onboarding — Verification Documents (step 2 of 8).
 * Requirement manifest is entirely backend-resolved (vertical + business_type)
 * via tenantDocumentsApi.getRequirements() — no hardcoded frontend document list.
 * File bytes go through the canonical Media Engine (mediaAssetApi/MediaUploader,
 * media_context="provider_document"); this page only links the resulting
 * media_asset_id to a requirement slot via tenantDocumentsApi.submitDocument().
 */
import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  FileText, CheckCircle2, Clock, XCircle, AlertTriangle, ChevronRight,
  Upload, ShieldCheck, Info, X, Plus,
} from "lucide-react";
import { OnboardingShell } from "../../../../../../components/onboarding/OnboardingShell";
import { ProgressRing } from "../../../../../../components/onboarding/ProgressRing";
import { StepProgressBar } from "../../../../../../components/onboarding/StepProgressBar";
import { Card, Btn, Badge, Skeleton } from "../../../../../../components/shared/ui";
import { MediaUploader } from "../../../../../../components/media/MediaUploader";
import { useTenant } from "../../../../../../hooks/useTenant";
import {
  tenantDocumentsApi, ServiceOSError,
  type VerificationDocumentsManifest, type VerificationRequirement, type MediaAsset,
} from "../../../../../../lib/api";

const STATUS_META: Record<string, { label: string; variant: "default" | "success" | "warning" | "danger" | "info"; icon: React.ReactNode }> = {
  not_uploaded:       { label: "Needs upload",     variant: "warning", icon: <AlertTriangle size={13}/> },
  pending_review:     { label: "Pending review",   variant: "info",    icon: <Clock size={13}/> },
  verified:           { label: "Verified",         variant: "success", icon: <CheckCircle2 size={13}/> },
  rejected:           { label: "Rejected",         variant: "danger",  icon: <XCircle size={13}/> },
  changes_requested:  { label: "Changes requested",variant: "danger",  icon: <AlertTriangle size={13}/> },
  expired:            { label: "Expired",          variant: "warning", icon: <AlertTriangle size={13}/> },
  superseded:         { label: "Replaced",         variant: "default", icon: <CheckCircle2 size={13}/> },
};

export default function VerificationDocumentsPage() {
  const router = useRouter();
  const tenant = useTenant();
  const [manifest, setManifest] = useState<VerificationDocumentsManifest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [addingExtra, setAddingExtra] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    tenantDocumentsApi.getRequirements()
      .then(setManifest)
      .catch(e => setError(e instanceof ServiceOSError ? e.message : "We couldn't load your document requirements."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleUploaded(docType: string, asset: MediaAsset, extraLabel?: string) {
    try {
      await tenantDocumentsApi.submitDocument({ doc_type: docType, media_asset_id: asset.id, label: extraLabel });
      setActiveKey(null);
      setAddingExtra(false);
      load();
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Could not save this document. Please try again.");
    }
  }

  if (loading) {
    return (
      <OnboardingShell activeNav="documents">
        <Skeleton height={60} style={{ marginBottom: 16 }}/>
        <Skeleton height={320} style={{ marginBottom: 16 }}/>
        <Skeleton height={200}/>
      </OnboardingShell>
    );
  }

  if (manifest && !manifest.business_profile_complete) {
    return (
      <OnboardingShell activeNav="documents">
        <Card>
          <div style={{ textAlign: "center", padding: "40px 20px" }}>
            <Info size={28} style={{ color: "var(--text-tertiary)", marginBottom: 12 }}/>
            <h1 style={{ fontSize: 17, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px" }}>
              Complete your Business Profile first
            </h1>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 20px", maxWidth: 420, marginLeft: "auto", marginRight: "auto" }}>
              We need your legal business name, address and contact details before we can tell you which documents to upload.
            </p>
            <Link href="/tenant/home-services/setup/business-profile">
              <Btn variant="primary">Go to Business Profile <ChevronRight size={15}/></Btn>
            </Link>
          </div>
        </Card>
      </OnboardingShell>
    );
  }

  const readiness = manifest?.readiness;
  const statusLine = !readiness ? "" :
    readiness.missing === 0 && readiness.rejected === 0 ? "All required documents uploaded" :
    readiness.rejected > 0 ? "Changes required" :
    `${readiness.uploaded} of ${readiness.required_total} uploaded`;

  return (
    <OnboardingShell activeNav="documents">
      <style>{`
        .docs-grid { display: grid; grid-template-columns: minmax(0,1fr) 360px; gap: 28px; align-items: start; }
        .docs-req-row { display: flex; align-items: center; gap: 12px; padding: 14px 16px; }
        .docs-req-badges { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
        @media (max-width: 1000px) {
          .docs-grid { grid-template-columns: 1fr; }
        }
        @media (max-width: 640px) {
          .docs-req-row { flex-wrap: wrap; }
          .docs-req-badges { width: 100%; padding-left: 48px; }
        }
      `}</style>
      {error && (
        <div role="alert" style={{ display: "flex", gap: 8, padding: "12px 14px", borderRadius: 10, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", color: "var(--danger-text)", fontSize: 13, marginBottom: 16 }}>
          <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 1 }}/><span>{error}</span>
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12, marginBottom: 6 }}>
        <div>
          <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.06em", color: "var(--brand)", margin: "0 0 6px", textTransform: "uppercase" }}>Tenant Onboarding</p>
          <h1 style={{ fontSize: 32, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>Verification documents</h1>
          <p style={{ fontSize: 13.5, color: "var(--text-secondary)", margin: 0 }}>Upload the documents required to verify your business.</p>
        </div>
        {readiness && (
          <Badge variant={readiness.missing === 0 ? "success" : readiness.rejected > 0 ? "danger" : "warning"}>
            <Upload size={12}/> {statusLine}
          </Badge>
        )}
      </div>

      <StepProgressBar step={3} total={8} />

      <div className="docs-grid">
        <div>
          <Card>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
              <div>
                <p style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Required documents</p>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
                  Requirements for: <strong style={{ color: "var(--text-secondary)" }}>{manifest?.requirements_context?.business_type?.replace(/_/g, " ") ?? "—"}</strong>
                  {" · "}<strong style={{ color: "var(--text-secondary)" }}>{manifest?.requirements_context?.vertical?.replace(/_/g, " ") ?? "—"}</strong>
                </p>
              </div>
              <Link href="/tenant/home-services/setup/business-profile" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", textDecoration: "none" }}>
                Change business profile
              </Link>
            </div>

            <div style={{ border: "1px solid var(--border)", borderRadius: 10, overflow: "hidden" }}>
              {manifest?.requirements.map((req, i) => (
                <RequirementRow
                  key={req.key}
                  req={req}
                  isLast={i === (manifest.requirements.length - 1)}
                  active={activeKey === req.key}
                  onToggle={() => setActiveKey(activeKey === req.key ? null : req.key)}
                  tenantId={tenant.tenantId ?? ""}
                  onUploaded={asset => handleUploaded(req.key, asset)}
                />
              ))}
            </div>
          </Card>

          <Card style={{ marginTop: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Additional documents</p>
              <Btn variant="secondary" size="sm" onClick={() => setAddingExtra(a => !a)}>
                {addingExtra ? <X size={14}/> : <Plus size={14}/>} Add document
              </Btn>
            </div>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 12px" }}>
              Upload any other documents that support your business verification.
            </p>
            {addingExtra && (
              <ExtraDocumentForm tenantId={tenant.tenantId ?? ""} onSaved={(asset, label) => handleUploaded("additional", asset, label)}/>
            )}
            {manifest?.additional_documents.map(doc => (
              <div key={doc.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 0", borderTop: "1px solid var(--border)", fontSize: 13 }}>
                <span style={{ color: "var(--text-primary)" }}>{doc.label || "Additional document"}</span>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <StatusBadge status={doc.status}/>
                  <button onClick={async () => { await tenantDocumentsApi.removeDocument(doc.id).catch(() => {}); load(); }}
                    aria-label="Remove document" style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)" }}>
                    <X size={14}/>
                  </button>
                </div>
              </div>
            ))}
          </Card>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 16px" }}>Verification readiness</p>
            {readiness && (
              <>
                <div style={{ display: "flex", justifyContent: "center", marginBottom: 16 }}>
                  <ProgressRing
                    pct={readiness.required_total ? (readiness.uploaded / readiness.required_total) * 100 : 0}
                    tone={readiness.rejected > 0 ? "warning" : readiness.missing === 0 ? "success" : "brand"}
                  />
                </div>
                <div style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                  <ReadinessLine label="Uploaded" value={readiness.uploaded} icon={<CheckCircle2 size={13} style={{ color: "var(--success)" }}/>}/>
                  <ReadinessLine label="Pending review" value={readiness.pending_review} icon={<Clock size={13} style={{ color: "var(--warning)" }}/>}/>
                  <ReadinessLine label="Missing" value={readiness.missing} icon={<AlertTriangle size={13} style={{ color: "var(--text-tertiary)" }}/>}/>
                </div>
              </>
            )}
          </Card>

          <Card>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Upload guidelines</p>
            {[
              `Acceptable formats: ${manifest?.upload_policy?.allowed_mime_types.map(m => m.split("/")[1]?.toUpperCase()).join(", ") ?? "—"}`,
              `Maximum file size: ${manifest?.upload_policy?.max_file_size_mb ?? "—"} MB`,
              "Ensure the document is clear and all edges are visible",
              "Avoid password-protected files",
            ].map(g => (
              <p key={g} style={{ display: "flex", gap: 8, fontSize: 12, color: "var(--text-secondary)", margin: "0 0 10px", lineHeight: 1.5 }}>
                <FileText size={13} style={{ flexShrink: 0, marginTop: 2, color: "var(--text-tertiary)" }}/> {g}
              </p>
            ))}
          </Card>

          <Card>
            <div style={{ display: "flex", gap: 10 }}>
              <ShieldCheck size={22} style={{ color: "var(--brand)", flexShrink: 0 }}/>
              <div>
                <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Your documents are private</p>
                <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>
                  Your documents are restricted to authorized verification workflows. Access, retention and disclosure are governed by platform policy.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>

      <div style={{ position: "sticky", bottom: 0, display: "flex", justifyContent: "space-between", padding: "16px 0", marginTop: 24, background: "var(--bg-gradient)" }}>
        <Link href="/tenant/home-services/setup/business-profile"><Btn variant="secondary">Back</Btn></Link>
        <div style={{ display: "flex", gap: 10 }}>
          <Btn variant="secondary" onClick={load}>Save draft</Btn>
          <Btn variant="primary"
            disabled={!readiness || !readiness.all_required_uploaded}
            onClick={() => router.push("/tenant/home-services/setup/services-pricing")}>
            Save &amp; continue <ChevronRight size={15}/>
          </Btn>
        </div>
      </div>
    </OnboardingShell>
  );
}

function ReadinessLine({ label, value, icon }: { label: string; value: number; icon: React.ReactNode }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12, color: "var(--text-secondary)", marginBottom: 8 }}>
      <span style={{ display: "flex", alignItems: "center", gap: 6 }}>{icon} {label}</span>
      <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>{value}</span>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const meta = STATUS_META[status] ?? STATUS_META.not_uploaded;
  return <Badge variant={meta.variant} size="sm">{meta.icon} {meta.label}</Badge>;
}

function RequirementRow({ req, isLast, active, onToggle, tenantId, onUploaded }: {
  req: VerificationRequirement; isLast: boolean; active: boolean; onToggle: () => void;
  tenantId: string; onUploaded: (asset: MediaAsset) => void;
}) {
  const meta = STATUS_META[req.status] ?? STATUS_META.not_uploaded;
  return (
    <div style={{ borderBottom: isLast ? "none" : "1px solid var(--border)" }}>
      <button onClick={onToggle} className="docs-req-row" style={{
        width: "100%", background: "none", border: "none", cursor: "pointer", textAlign: "left", fontFamily: "inherit",
      }}>
        <div style={{ width: 36, height: 36, borderRadius: 8, background: "var(--surface-sunken)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
          <FileText size={16} style={{ color: "var(--text-tertiary)" }}/>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 2px" }}>{req.label}</p>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            Accepted: {req.accepted_examples.join(", ")}
          </p>
        </div>
        <div className="docs-req-badges">
          <Badge variant={req.required ? "default" : "default"} size="sm">{req.required ? "Required" : "Optional"}</Badge>
          <StatusBadge status={req.status}/>
          <ChevronRight size={16} style={{ color: "var(--text-tertiary)", flexShrink: 0, transform: active ? "rotate(90deg)" : "none", transition: "transform 0.15s" }}/>
        </div>
      </button>

      {active && (
        <div style={{ padding: "0 16px 20px 64px" }}>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 12px" }}>{req.why}</p>
          {req.status === "rejected" || req.status === "changes_requested" ? (
            <div style={{ padding: "10px 12px", borderRadius: 8, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", marginBottom: 12, fontSize: 12, color: "var(--danger-text)" }}>
              {req.document?.rejection_reason || "This document needs to be replaced."}
            </div>
          ) : null}
          <MediaUploader
            mediaContext="provider_document"
            ownerType="tenant"
            ownerId={tenantId}
            accept="application/pdf,image/jpeg,image/png,image/webp"
            multiple={false}
            canDelete={false}
            label={req.document ? "Replace document" : "Upload document"}
            onUploaded={onUploaded}
          />
        </div>
      )}
    </div>
  );
}

function ExtraDocumentForm({ tenantId, onSaved }: { tenantId: string; onSaved: (asset: MediaAsset, label: string) => void }) {
  const [label, setLabel] = useState("");
  return (
    <div style={{ padding: "12px", borderRadius: 8, border: "1px solid var(--border)", marginBottom: 12 }}>
      <input value={label} onChange={e => setLabel(e.target.value)} placeholder="Document label (e.g. Trade license)"
        style={{ width: "100%", height: 36, padding: "0 10px", fontSize: 13, borderRadius: 6, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", marginBottom: 10, boxSizing: "border-box", fontFamily: "inherit" }}/>
      <MediaUploader
        mediaContext="provider_document"
        ownerType="tenant"
        ownerId={tenantId}
        multiple={false}
        canDelete={false}
        label="Upload"
        onUploaded={asset => label.trim() && onSaved(asset, label.trim())}
      />
    </div>
  );
}
