"use client";
import { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import {
  adminMarketingApi,
  MarketingAsset,
  MarketingCampaign,
} from "@/lib/api";
import {
  Card,
  Badge,
  Btn,
  Modal,
  Input,
  Skeleton,
} from "@/components/shared/ui";
import { useApi, useAction } from "@/hooks/useApi";
import { CheckCircle2, XCircle, AlertCircle, Send, Globe, ArrowLeft } from "lucide-react";
import Link from "next/link";

function statusVariant(s: string): "success" | "warning" | "danger" | "info" | "default" {
  if (s === "published" || s === "manually_published" || s === "approved") return "success";
  if (s === "ready_to_publish") return "info";
  if (s === "pending_admin_review" || s === "generated") return "warning";
  if (s === "rejected" || s === "cancelled") return "danger";
  return "default";
}

export default function AdminCampaignDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data, loading, refetch } = useApi(
    useCallback(() => adminMarketingApi.getCampaign(id), [id])
  );

  const campaign: MarketingCampaign | undefined = data?.campaign;

  const [rejectModal,  setRejectModal]  = useState<{ open: boolean; assetId: string | null; reason: string }>({ open: false, assetId: null, reason: "" });
  const [changesModal, setChangesModal] = useState<{ open: boolean; assetId: string | null; reason: string }>({ open: false, assetId: null, reason: "" });
  const [publishModal, setPublishModal] = useState<{ open: boolean; assetId: string | null; url: string; proof: string; notes: string }>({ open: false, assetId: null, url: "", proof: "", notes: "" });

  const approveAction  = useAction(useCallback((assetId: string) => adminMarketingApi.approveAsset(assetId), []));
  const rejectAction   = useAction(useCallback((args: { assetId: string; reason: string }) => adminMarketingApi.rejectAsset(args.assetId, args.reason), []));
  const changesAction  = useAction(useCallback((args: { assetId: string; reason: string }) => adminMarketingApi.requestChanges(args.assetId, args.reason), []));
  const readyAction    = useAction(useCallback((assetId: string) => adminMarketingApi.markReadyToPublish(assetId), []));
  const publishAction  = useAction(useCallback((args: { assetId: string; url: string; proof: string; notes: string }) =>
    adminMarketingApi.markManuallyPublished(args.assetId, {
      publish_url: args.url || undefined,
      publish_proof_url: args.proof || undefined,
      notes: args.notes || undefined,
    }), []));

  if (loading) return (
    <div style={{ padding: 24 }}><Skeleton height={160} /></div>
  );
  if (!campaign) return (
    <div style={{ padding: 24, color: "var(--text-secondary)" }}>Campaign not found.</div>
  );

  return (
    <div style={{ padding: "24px 32px", maxWidth: 1280, margin: "0 auto", display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <Link href="/admin/marketing/campaigns">
          <Btn variant="ghost" size="sm"><ArrowLeft size={14} /> Back</Btn>
        </Link>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)" }}>{campaign.campaign_name}</h1>
          <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Campaign ID: {campaign.id}</p>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <Badge variant={statusVariant(campaign.status)}>{campaign.status}</Badge>
          {campaign.admin_review_status && (
            <Badge variant={statusVariant(campaign.admin_review_status)}>Admin: {campaign.admin_review_status}</Badge>
          )}
        </div>
      </div>

      <Card>
        <div style={{ padding: "14px 16px", display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, fontSize: 13 }}>
          <div><p style={{ color: "var(--text-tertiary)", fontSize: 11 }}>Type</p><p style={{ fontWeight: 500 }}>{campaign.campaign_type}</p></div>
          <div><p style={{ color: "var(--text-tertiary)", fontSize: 11 }}>Marketing Ready</p><Badge variant={campaign.marketing_ready ? "success" : "warning"}>{campaign.marketing_ready ? "Yes" : "No"}</Badge></div>
          <div><p style={{ color: "var(--text-tertiary)", fontSize: 11 }}>Created</p><p>{campaign.created_at ? new Date(campaign.created_at).toLocaleDateString() : "—"}</p></div>
          <div><p style={{ color: "var(--text-tertiary)", fontSize: 11 }}>Published</p><p>{campaign.published_at ? new Date(campaign.published_at).toLocaleDateString() : "—"}</p></div>
        </div>
      </Card>

      <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)" }}>Assets ({campaign.assets?.length ?? 0})</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {(campaign.assets ?? []).map((asset: MarketingAsset) => (
          <Card key={asset.id}>
            <div style={{ padding: "14px 16px", display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  <Badge variant="default">{asset.asset_type}</Badge>
                  <Badge variant="default">{asset.channel}</Badge>
                  <Badge variant={statusVariant(asset.status)}>{asset.status}</Badge>
                  <Badge variant="default">{asset.language}</Badge>
                </div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {(asset.status === "pending_admin_review" || asset.status === "generated") && (
                    <>
                      <Btn size="sm" onClick={() => approveAction.execute(asset.id).then(() => refetch())} loading={approveAction.loading}>
                        <CheckCircle2 size={13} /> Approve
                      </Btn>
                      <Btn size="sm" variant="ghost" onClick={() => setRejectModal({ open: true, assetId: asset.id, reason: "" })}>
                        <XCircle size={13} /> Reject
                      </Btn>
                      <Btn size="sm" variant="ghost" onClick={() => setChangesModal({ open: true, assetId: asset.id, reason: "" })}>
                        <AlertCircle size={13} /> Request Changes
                      </Btn>
                    </>
                  )}
                  {asset.status === "approved" && (
                    <Btn size="sm" onClick={() => readyAction.execute(asset.id).then(() => refetch())} loading={readyAction.loading}>
                      <Send size={13} /> Mark Ready to Publish
                    </Btn>
                  )}
                  {asset.status === "ready_to_publish" && (
                    <Btn size="sm" onClick={() => setPublishModal({ open: true, assetId: asset.id, url: "", proof: "", notes: "" })}>
                      <Globe size={13} /> Mark Manually Published
                    </Btn>
                  )}
                </div>
              </div>
              {asset.title && <p style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)" }}>{asset.title}</p>}
              {asset.body && (
                <div style={{ background: "var(--surface-sunken)", borderRadius: 6, padding: "10px 12px", fontSize: 12, color: "var(--text-primary)", whiteSpace: "pre-wrap" }}>
                  {asset.body}
                </div>
              )}
              {asset.rejection_reason && (
                <p style={{ fontSize: 11, color: "var(--danger-text)" }}>Rejection: {asset.rejection_reason}</p>
              )}
              {asset.admin_notes && (
                <p style={{ fontSize: 11, color: "var(--warning-text, #92400e)" }}>Admin notes: {asset.admin_notes}</p>
              )}
              {asset.publish_url && (
                <a href={asset.publish_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 11, color: "var(--brand)" }}>
                  Published URL
                </a>
              )}
            </div>
          </Card>
        ))}
      </div>

      <Modal open={rejectModal.open} onClose={() => setRejectModal({ open: false, assetId: null, reason: "" })} title="Reject Asset">
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>Provide a rejection reason (required).</p>
          <Input placeholder="Rejection reason..." value={rejectModal.reason} onChange={v => setRejectModal(s => ({ ...s, reason: v }))} />
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <Btn variant="ghost" onClick={() => setRejectModal({ open: false, assetId: null, reason: "" })}>Cancel</Btn>
            <Btn variant="danger"
              onClick={() => rejectAction.execute({ assetId: rejectModal.assetId!, reason: rejectModal.reason }).then(() => { setRejectModal({ open: false, assetId: null, reason: "" }); refetch(); })}
              loading={rejectAction.loading}
              disabled={!rejectModal.reason.trim()}>
              Reject
            </Btn>
          </div>
        </div>
      </Modal>

      <Modal open={changesModal.open} onClose={() => setChangesModal({ open: false, assetId: null, reason: "" })} title="Request Changes">
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>Describe the required changes (required).</p>
          <Input placeholder="Describe changes needed..." value={changesModal.reason} onChange={v => setChangesModal(s => ({ ...s, reason: v }))} />
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <Btn variant="ghost" onClick={() => setChangesModal({ open: false, assetId: null, reason: "" })}>Cancel</Btn>
            <Btn
              onClick={() => changesAction.execute({ assetId: changesModal.assetId!, reason: changesModal.reason }).then(() => { setChangesModal({ open: false, assetId: null, reason: "" }); refetch(); })}
              loading={changesAction.loading}
              disabled={!changesModal.reason.trim()}>
              Send Request
            </Btn>
          </div>
        </div>
      </Modal>

      <Modal open={publishModal.open} onClose={() => setPublishModal({ open: false, assetId: null, url: "", proof: "", notes: "" })} title="Mark Manually Published">
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            Provide at least a Publish URL or Proof URL. Fake publishing without evidence is blocked.
          </p>
          <Input placeholder="Published URL" value={publishModal.url} onChange={v => setPublishModal(s => ({ ...s, url: v }))} />
          <Input placeholder="Proof URL (screenshot)" value={publishModal.proof} onChange={v => setPublishModal(s => ({ ...s, proof: v }))} />
          <Input placeholder="Notes (optional)" value={publishModal.notes} onChange={v => setPublishModal(s => ({ ...s, notes: v }))} />
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <Btn variant="ghost" onClick={() => setPublishModal({ open: false, assetId: null, url: "", proof: "", notes: "" })}>Cancel</Btn>
            <Btn
              onClick={() => publishAction.execute({ assetId: publishModal.assetId!, url: publishModal.url, proof: publishModal.proof, notes: publishModal.notes }).then(() => { setPublishModal({ open: false, assetId: null, url: "", proof: "", notes: "" }); refetch(); })}
              loading={publishAction.loading}
              disabled={!publishModal.url.trim() && !publishModal.proof.trim()}>
              Confirm Published
            </Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}
