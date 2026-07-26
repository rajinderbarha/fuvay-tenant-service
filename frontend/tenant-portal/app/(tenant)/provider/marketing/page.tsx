"use client";
import { useCallback, useState } from "react";
import Link from "next/link";
import {
  providerMarketingApi,
  type MarketingStatusData,
  type ProviderMarketingCampaign,
  type ProviderMarketingAsset,
  type MarketingBlocker,
} from "../../../../lib/api";
import { Card, Badge, Btn, Skeleton, Toaster, type ToastItem } from "../../../../components/shared/ui";
import { useApi, useAction } from "../../../../hooks/useApi";
import {
  Megaphone, CheckCircle2, XCircle, AlertCircle,
  Copy, Send, RefreshCw, ExternalLink,
} from "lucide-react";

function statusVariant(s: string): "success" | "warning" | "danger" | "info" | "default" {
  if (s === "published" || s === "manually_published" || s === "approved") return "success";
  if (s === "ready_to_publish") return "info";
  if (s === "pending_admin_review") return "warning";
  if (s === "rejected" || s === "cancelled") return "danger";
  return "default";
}

function AssetCard({
  asset,
  onNotesUpdate,
  onToast,
}: {
  asset: ProviderMarketingAsset;
  onNotesUpdate: () => void;
  onToast: (msg: string, variant?: ToastItem["variant"]) => void;
}) {
  const [notes, setNotes] = useState(asset.provider_notes ?? "");
  const [editingNotes, setEditingNotes] = useState(false);

  const updateNotesAction = useAction(
    useCallback(
      () => providerMarketingApi.updateProviderNotes(asset.id, notes),
      [asset.id, notes]
    ),
    {
      onSuccess: () => { onToast("Notes saved.", "success"); setEditingNotes(false); onNotesUpdate(); },
      onError: (msg) => onToast(msg, "danger"),
    }
  );

  const copyText = async (text: string) => {
    try { await navigator.clipboard.writeText(text); onToast("Copied!", "success"); }
    catch { onToast("Copy failed.", "danger"); }
  };

  return (
    <Card padding={16}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <Badge variant="default">{asset.asset_type}</Badge>
          <Badge variant="default">{asset.channel}</Badge>
          <Badge variant={statusVariant(asset.status)}>{asset.status.replace(/_/g, " ")}</Badge>
        </div>
        {(asset.asset_type === "whatsapp_message" || asset.asset_type === "social_caption") && asset.body && (
          <Btn size="sm" variant="ghost" onClick={() => copyText(asset.body!)}>
            <Copy size={12} /> Copy Text
          </Btn>
        )}
      </div>

      {asset.title && (
        <p style={{ fontWeight: 600, fontSize: 14, color: "var(--text-primary)", margin: "0 0 8px" }}>{asset.title}</p>
      )}
      {asset.body && (
        <div style={{ background: "var(--surface-sunken)", borderRadius: 8, padding: "10px 12px", fontSize: 13,
          whiteSpace: "pre-wrap", color: "var(--text-secondary)", marginBottom: 8 }}>
          {asset.body}
        </div>
      )}

      {asset.status === "rejected" && asset.rejection_reason && (
        <div style={{ display: "flex", alignItems: "flex-start", gap: 8, background: "var(--danger-bg)",
          borderRadius: 8, padding: "10px 12px", fontSize: 13, color: "var(--danger-text)", marginBottom: 8 }}>
          <XCircle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
          <div><strong>Rejected:</strong> {asset.rejection_reason}</div>
        </div>
      )}

      {asset.status === "pending_provider_review" && asset.admin_notes && (
        <div style={{ display: "flex", alignItems: "flex-start", gap: 8, background: "var(--warning-bg)",
          borderRadius: 8, padding: "10px 12px", fontSize: 13, color: "var(--warning-text)", marginBottom: 8 }}>
          <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
          <div><strong>Changes requested:</strong> {asset.admin_notes}</div>
        </div>
      )}

      {asset.publish_url && (
        <a href={asset.publish_url} target="_blank" rel="noopener noreferrer"
          style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12, color: "var(--brand)",
            textDecoration: "none", marginBottom: 8 }}>
          <ExternalLink size={12} /> View published post
        </a>
      )}

      {editingNotes ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <textarea
            rows={3}
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="Add notes for the admin..."
            style={{ width: "100%", padding: "8px 10px", fontSize: 13, border: "1px solid var(--border)",
              borderRadius: 8, background: "var(--surface)", color: "var(--text-primary)",
              resize: "vertical", fontFamily: "inherit", boxSizing: "border-box" }}
          />
          <div style={{ display: "flex", gap: 8 }}>
            <Btn size="sm" onClick={() => updateNotesAction.execute()} loading={updateNotesAction.loading}>Save Notes</Btn>
            <Btn size="sm" variant="ghost" onClick={() => setEditingNotes(false)}>Cancel</Btn>
          </div>
        </div>
      ) : (
        <div style={{ fontSize: 12, color: "var(--text-tertiary)", display: "flex", alignItems: "center", gap: 8 }}>
          {asset.provider_notes
            ? <span style={{ color: "var(--text-secondary)" }}>{asset.provider_notes}</span>
            : <span>No notes added.</span>
          }
          <button onClick={() => setEditingNotes(true)}
            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--brand)",
              fontSize: 12, padding: 0, textDecoration: "underline" }}>
            {asset.provider_notes ? "Edit" : "Add notes"}
          </button>
        </div>
      )}
    </Card>
  );
}

export default function ProviderMarketingPage() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const addToast = useCallback((title: string, variant: ToastItem["variant"] = "success") => {
    const id = Math.random().toString(36).slice(2);
    setToasts(prev => [...prev, { id, title, variant }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3500);
  }, []);

  const { data: statusData, loading: statusLoading, refetch: refetchStatus } = useApi(
    useCallback(() => providerMarketingApi.getStatus(), [])
  );
  const { data: campaignsData, loading: campaignsLoading, refetch: refetchCampaigns } = useApi(
    useCallback(() => providerMarketingApi.listCampaigns(), [])
  );
  const { data: assetsData, loading: assetsLoading, refetch: refetchAssets } = useApi(
    useCallback(() => providerMarketingApi.listAssets(), [])
  );

  const mktgStatus: MarketingStatusData | undefined = statusData ?? undefined;
  const campaigns: ProviderMarketingCampaign[] = campaignsData?.campaigns ?? [];
  const assets: ProviderMarketingAsset[] = assetsData?.assets ?? [];

  const generateAction = useAction(
    useCallback(() => providerMarketingApi.generateLaunchCampaign(), []),
    {
      onSuccess: (res) => {
        addToast(res.message ?? "Campaign generated.");
        refetchStatus(); refetchCampaigns(); refetchAssets();
      },
      onError: (msg) => addToast(msg, "danger"),
    }
  );

  const submitAction = useAction(
    useCallback((campaignId: string) => providerMarketingApi.submitForReview(campaignId), []),
    {
      onSuccess: () => { addToast("Submitted for admin review."); refetchCampaigns(); refetchAssets(); },
      onError: (msg) => addToast(msg, "danger"),
    }
  );

  const refetchAll = () => { refetchStatus(); refetchCampaigns(); refetchAssets(); };
  const activeCampaign = mktgStatus?.active_campaign;
  const blockers: MarketingBlocker[] = mktgStatus?.blockers ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 32, maxWidth: 900 }}>
      <Toaster toasts={toasts} onRemove={id => setToasts(p => p.filter(t => t.id !== id))} />

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0,
            display: "flex", alignItems: "center", gap: 10 }}>
            <Megaphone size={22} /> Marketing Launch
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "6px 0 0" }}>
            Manage your marketing launch campaign and assets.
          </p>
        </div>
        <Btn variant="ghost" onClick={refetchAll}>
          <RefreshCw size={14} /> Refresh
        </Btn>
      </div>

      {/* Marketing Status */}
      <Card padding={20}>
        <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 16px" }}>Marketing Status</p>
        {statusLoading ? (
          <Skeleton height={64} />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              {mktgStatus?.marketing_ready
                ? <CheckCircle2 size={20} style={{ color: "#059669", flexShrink: 0 }} />
                : <XCircle size={20} style={{ color: "#dc2626", flexShrink: 0 }} />}
              <div style={{ flex: 1 }}>
                <p style={{ fontWeight: 500, color: "var(--text-primary)", margin: 0 }}>
                  {mktgStatus?.marketing_ready ? "Ready for marketing launch" : "Not ready yet"}
                </p>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                  {mktgStatus?.status?.replace(/_/g, " ")}
                </p>
              </div>
              {!activeCampaign && (
                <Btn
                  onClick={() => generateAction.execute()}
                  disabled={generateAction.loading}
                  loading={generateAction.loading}
                >
                  Generate Launch Campaign
                </Btn>
              )}
            </div>

            {blockers.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", margin: 0 }}>
                  Blockers to resolve:
                </p>
                {blockers.map((b) => (
                  <div key={b.code} style={{ display: "flex", alignItems: "flex-start", gap: 8,
                    background: "var(--warning-bg)", borderRadius: 8, padding: "10px 12px",
                    fontSize: 13, color: "var(--warning-text)" }}>
                    <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
                    <div>
                      {b.message}
                      {b.route && (
                        <Link href={b.route} style={{ marginLeft: 8, color: "var(--brand)", textDecoration: "underline" }}>
                          Fix →
                        </Link>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Campaigns */}
      {(campaignsLoading || campaigns.length > 0) && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>Your Campaigns</p>
          {campaignsLoading ? (
            <Skeleton height={80} />
          ) : (
            campaigns.map((campaign) => (
              <Card key={campaign.id} padding={16}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start",
                  flexWrap: "wrap", gap: 10, marginBottom: 8 }}>
                  <div>
                    <p style={{ fontWeight: 500, color: "var(--text-primary)", margin: 0 }}>{campaign.campaign_name}</p>
                    <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{campaign.campaign_type}</p>
                  </div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
                    <Badge variant={statusVariant(campaign.status)}>{campaign.status.replace(/_/g, " ")}</Badge>
                    {campaign.admin_review_status && (
                      <Badge variant={statusVariant(campaign.admin_review_status)}>
                        Admin: {campaign.admin_review_status}
                      </Badge>
                    )}
                    {(campaign.status === "generated" || campaign.status === "draft") && (
                      <Btn size="sm" onClick={() => submitAction.execute(campaign.id)} loading={submitAction.loading}>
                        <Send size={12} /> Submit for Review
                      </Btn>
                    )}
                  </div>
                </div>
                {campaign.requested_changes && (
                  <div style={{ background: "var(--warning-bg)", borderRadius: 8, padding: "10px 12px",
                    fontSize: 13, color: "var(--warning-text)", marginTop: 8 }}>
                    <strong>Changes requested:</strong> {campaign.requested_changes}
                  </div>
                )}
                {campaign.rejection_reason && (
                  <div style={{ background: "var(--danger-bg)", borderRadius: 8, padding: "10px 12px",
                    fontSize: 13, color: "var(--danger-text)", marginTop: 8 }}>
                    <strong>Rejected:</strong> {campaign.rejection_reason}
                  </div>
                )}
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "8px 0 0" }}>
                  Created: {campaign.created_at ? new Date(campaign.created_at).toLocaleDateString() : "—"}
                </p>
              </Card>
            ))
          )}
        </div>
      )}

      {/* Assets */}
      {(assetsLoading || assets.length > 0) && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
            Marketing Assets {assets.length > 0 ? `(${assets.length})` : ""}
          </p>
          {assetsLoading ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {[0, 1, 2].map(i => <Skeleton key={i} height={96} />)}
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {assets.map(asset => (
                <AssetCard key={asset.id} asset={asset} onNotesUpdate={refetchAssets} onToast={addToast} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!statusLoading && !campaignsLoading && campaigns.length === 0 && (
        <Card padding={48} style={{ textAlign: "center" }}>
          <Megaphone size={32} style={{ color: "var(--text-tertiary)", margin: "0 auto 12px" }} />
          <p style={{ color: "var(--text-secondary)", margin: "0 0 8px" }}>No marketing campaigns yet.</p>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>
            Resolve any blockers above, then click &quot;Generate Launch Campaign&quot; to create your first campaign.
          </p>
        </Card>
      )}
    </div>
  );
}
