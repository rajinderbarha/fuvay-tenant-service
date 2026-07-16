"use client";
import { useCallback, useState } from "react";
import {
  adminMarketingApi,
  MarketingAsset,
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
import { CheckCircle2, XCircle, AlertCircle, Send, Globe } from "lucide-react";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "generated", label: "Generated" },
  { value: "pending_admin_review", label: "Pending Review" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "ready_to_publish", label: "Ready to Publish" },
  { value: "manually_published", label: "Manually Published" },
  { value: "published", label: "Published" },
];

function statusVariant(s: string): "success" | "warning" | "danger" | "info" | "default" {
  if (s === "published" || s === "manually_published" || s === "approved") return "success";
  if (s === "ready_to_publish") return "info";
  if (s === "pending_admin_review" || s === "generated") return "warning";
  if (s === "rejected" || s === "cancelled" || s === "failed") return "danger";
  return "default";
}

export default function AdminMarketingAssetsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);

  const { data, loading, refetch } = useApi(
    useCallback(
      () => adminMarketingApi.listAssets({ status: statusFilter || undefined, page, page_size: 20 }),
      [statusFilter, page]
    )
  );

  const assets: MarketingAsset[] = data?.assets ?? [];

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

  const selectStyle: React.CSSProperties = {
    border: "1px solid var(--border)", borderRadius: 8, padding: "8px 12px",
    fontSize: 13, background: "var(--surface-sunken)", color: "var(--text-primary)",
    fontFamily: "inherit", outline: "none", minWidth: 200,
  };

  return (
    <div style={{ padding: "24px 32px", maxWidth: 1280, margin: "0 auto", display: "flex", flexDirection: "column", gap: 20 }}>
      {/* MODULE-L5-44: investigated (same audit that found L5-39..43) whether
          /v1/admin/marketing/assets* could be repointed to a real endpoint.
          MarketingAsset's fields (campaign_id, admin_notes, rejection_reason,
          publish_url, publish_proof_url) don't match any real table --
          marketing_post_assets (the only "asset" table) is a child-of-post AI
          generation record with no campaign_id/admin approval fields at all.
          The real admin marketing system is entirely posts-based
          (/v1/admin/marketing/posts, approve/reject/schedule/publish-now).
          This asset/campaign-approval concept was superseded, not renamed --
          rather than fabricate a fix, this page says so honestly. */}
      <div style={{ padding: "10px 16px", borderRadius: 10, background: "rgba(217,119,6,0.08)",
        border: "1px solid rgba(217,119,6,0.25)", fontSize: 13, color: "#b45309" }}>
        This page is not available in this build. The "marketing asset"
        approval workflow it assumes was superseded by the posts-based
        marketing system (Campaigns → Posts, with approve/reject/schedule);
        no backing table or endpoint for assets remains. Use the Posts admin
        surface instead.
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)" }}>Marketing Assets</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>Review and approve provider marketing assets.</p>
        </div>
        <Btn onClick={() => refetch()} disabled>Refresh</Btn>
      </div>

      <Card>
        <div style={{ padding: "12px 16px" }}>
          <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }} style={selectStyle}>
            {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </Card>

      <Card>
        {loading ? (
          <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 10 }}>
            {[...Array(5)].map((_, i) => <Skeleton key={i} height={48} />)}
          </div>
        ) : assets.length === 0 ? (
          <div style={{ padding: 48, textAlign: "center", color: "var(--text-tertiary)" }}>No assets found.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                  {["Type", "Channel", "Language", "Status", "Preview", "Actions"].map(h => (
                    <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {assets.map((asset) => (
                  <tr key={asset.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 16px" }}><Badge variant="default">{asset.asset_type}</Badge></td>
                    <td style={{ padding: "10px 16px", color: "var(--text-secondary)", fontSize: 12 }}>{asset.channel}</td>
                    <td style={{ padding: "10px 16px", color: "var(--text-secondary)", fontSize: 12 }}>{asset.language}</td>
                    <td style={{ padding: "10px 16px" }}><Badge variant={statusVariant(asset.status)}>{asset.status}</Badge></td>
                    <td style={{ padding: "10px 16px", maxWidth: 260 }}>
                      {asset.title && <p style={{ fontWeight: 500, fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{asset.title}</p>}
                      {asset.body  && <p style={{ fontSize: 11, color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{asset.body}</p>}
                    </td>
                    <td style={{ padding: "10px 16px" }}>
                      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                        {(asset.status === "pending_admin_review" || asset.status === "generated") && (
                          <>
                            <Btn size="sm" onClick={() => approveAction.execute(asset.id).then(() => refetch())} loading={approveAction.loading}>
                              <CheckCircle2 size={12} /> Approve
                            </Btn>
                            <Btn size="sm" variant="ghost" onClick={() => setRejectModal({ open: true, assetId: asset.id, reason: "" })}>
                              <XCircle size={12} /> Reject
                            </Btn>
                            <Btn size="sm" variant="ghost" onClick={() => setChangesModal({ open: true, assetId: asset.id, reason: "" })}>
                              <AlertCircle size={12} /> Changes
                            </Btn>
                          </>
                        )}
                        {asset.status === "approved" && (
                          <Btn size="sm" onClick={() => readyAction.execute(asset.id).then(() => refetch())} loading={readyAction.loading}>
                            <Send size={12} /> Ready
                          </Btn>
                        )}
                        {asset.status === "ready_to_publish" && (
                          <Btn size="sm" onClick={() => setPublishModal({ open: true, assetId: asset.id, url: "", proof: "", notes: "" })}>
                            <Globe size={12} /> Published
                          </Btn>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!loading && assets.length > 0 && (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 16px", borderTop: "1px solid var(--border)", fontSize: 12, color: "var(--text-tertiary)" }}>
            <span>Page {page}</span>
            <div style={{ display: "flex", gap: 8 }}>
              <Btn size="sm" variant="ghost" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Prev</Btn>
              <Btn size="sm" variant="ghost" onClick={() => setPage(p => p + 1)} disabled={assets.length < 20}>Next</Btn>
            </div>
          </div>
        )}
      </Card>

      <Modal open={rejectModal.open} onClose={() => setRejectModal({ open: false, assetId: null, reason: "" })} title="Reject Asset">
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Input placeholder="Rejection reason (required)..." value={rejectModal.reason} onChange={v => setRejectModal(s => ({ ...s, reason: v }))} />
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
          <Input placeholder="Changes required (required)..." value={changesModal.reason} onChange={v => setChangesModal(s => ({ ...s, reason: v }))} />
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <Btn variant="ghost" onClick={() => setChangesModal({ open: false, assetId: null, reason: "" })}>Cancel</Btn>
            <Btn
              onClick={() => changesAction.execute({ assetId: changesModal.assetId!, reason: changesModal.reason }).then(() => { setChangesModal({ open: false, assetId: null, reason: "" }); refetch(); })}
              loading={changesAction.loading}
              disabled={!changesModal.reason.trim()}>
              Request
            </Btn>
          </div>
        </div>
      </Modal>

      <Modal open={publishModal.open} onClose={() => setPublishModal({ open: false, assetId: null, url: "", proof: "", notes: "" })} title="Mark Manually Published">
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>At least one of Publish URL or Proof URL is required. No fake publishing.</p>
          <Input placeholder="Published URL" value={publishModal.url} onChange={v => setPublishModal(s => ({ ...s, url: v }))} />
          <Input placeholder="Proof URL (screenshot)" value={publishModal.proof} onChange={v => setPublishModal(s => ({ ...s, proof: v }))} />
          <Input placeholder="Notes (optional)" value={publishModal.notes} onChange={v => setPublishModal(s => ({ ...s, notes: v }))} />
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <Btn variant="ghost" onClick={() => setPublishModal({ open: false, assetId: null, url: "", proof: "", notes: "" })}>Cancel</Btn>
            <Btn
              onClick={() => publishAction.execute({ assetId: publishModal.assetId!, url: publishModal.url, proof: publishModal.proof, notes: publishModal.notes }).then(() => { setPublishModal({ open: false, assetId: null, url: "", proof: "", notes: "" }); refetch(); })}
              loading={publishAction.loading}
              disabled={!publishModal.url.trim() && !publishModal.proof.trim()}>
              Confirm
            </Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}
