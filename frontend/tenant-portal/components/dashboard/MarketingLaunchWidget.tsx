"use client";
import { useCallback } from "react";
import { providerMarketingApi } from "../../lib/api";
import { Card, Badge, Btn, Skeleton } from "../shared/ui";
import { useApi, useAction } from "../../hooks/useApi";
import { Megaphone, AlertCircle, CheckCircle2, ExternalLink } from "lucide-react";
import Link from "next/link";

function statusVariant(s: string): "success" | "info" | "warning" | "danger" | "default" {
  if (s === "published") return "success";
  if (s === "approved" || s === "ready_to_publish") return "info";
  if (s === "pending_admin_review") return "warning";
  if (s === "rejected") return "danger";
  return "default";
}

export function MarketingLaunchWidget() {
  const { data, loading, refetch } = useApi(
    useCallback(() => providerMarketingApi.getStatus(), [])
  );

  const generateAction = useAction(
    useCallback(() => providerMarketingApi.generateLaunchCampaign(), []),
    { onSuccess: () => refetch() }
  );

  if (loading) return <Skeleton height={90} />;
  if (!data) return null;

  const campaign = data.active_campaign;
  const blockers = data.blockers ?? [];

  return (
    <Card padding={16}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8,
            background: "rgba(147,51,234,0.1)",
            display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Megaphone size={16} style={{ color: "#7c3aed" }} />
          </div>
          <div>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>Marketing</p>
            <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: "2px 0 0" }}>Launch Status</p>
          </div>
        </div>
        <Link href="/provider/marketing" style={{ textDecoration: "none" }}>
          <Btn size="sm" variant="secondary">
            <ExternalLink size={12} /> Details
          </Btn>
        </Link>
      </div>

      {campaign ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <Badge variant={statusVariant(campaign.status)}>{campaign.status.replace(/_/g, " ")}</Badge>
            {campaign.admin_review_status && (
              <Badge variant={campaign.admin_review_status === "approved" ? "success" : "warning"}>
                Admin: {campaign.admin_review_status}
              </Badge>
            )}
          </div>
          {campaign.status === "pending_admin_review" && (
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
              Under admin review — you&apos;ll be notified on approval.
            </p>
          )}
          {campaign.status === "approved" && (
            <p style={{ fontSize: 12, color: "var(--success)", margin: 0, display: "flex", alignItems: "center", gap: 4 }}>
              <CheckCircle2 size={12} /> Campaign approved. Admin will publish soon.
            </p>
          )}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {blockers.length > 0 ? (
            <div style={{ display: "flex", alignItems: "flex-start", gap: 6, fontSize: 12, color: "var(--warning)" }}>
              <AlertCircle size={13} style={{ flexShrink: 0, marginTop: 1 }} />
              <span>{blockers.length} blocker{blockers.length > 1 ? "s" : ""} to resolve before launch.</span>
            </div>
          ) : (
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
              Ready to generate your launch campaign.
            </p>
          )}
          <Btn
            size="sm"
            onClick={() => generateAction.execute()}
            disabled={generateAction.loading || blockers.length > 0}
            loading={generateAction.loading}
          >
            Generate Launch Campaign
          </Btn>
        </div>
      )}
    </Card>
  );
}
