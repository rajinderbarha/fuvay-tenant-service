"use client";
import { useCallback, useState } from "react";
import {
  adminMarketingApi,
  MarketingCampaign,
} from "@/lib/api";
import {
  Card,
  Badge,
  Btn,
  Input,
  Select,
  Skeleton,
} from "@/components/shared/ui";
import { useApi } from "@/hooks/useApi";
import { RefreshCw, Eye, Smartphone } from "lucide-react";
import Link from "next/link";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "draft", label: "Draft" },
  { value: "generated", label: "Generated" },
  { value: "pending_admin_review", label: "Pending Review" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "ready_to_publish", label: "Ready to Publish" },
  { value: "published", label: "Published" },
  { value: "cancelled", label: "Cancelled" },
];

function statusVariant(s: string): "success" | "warning" | "danger" | "info" | "default" {
  if (s === "published") return "success";
  if (s === "approved" || s === "ready_to_publish") return "info";
  if (s === "pending_admin_review") return "warning";
  if (s === "rejected" || s === "cancelled") return "danger";
  return "default";
}

const th: React.CSSProperties = {
  padding: "8px 14px", fontSize: 11, fontWeight: 700, textTransform: "uppercase",
  letterSpacing: "0.07em", color: "var(--text-tertiary)", textAlign: "left",
};

export default function AdminMarketingCampaignsPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const { data, loading, refetch } = useApi(
    useCallback(
      () => adminMarketingApi.listCampaigns({ status: status || undefined, search: search || undefined, page, page_size: 20 }),
      [status, search, page]
    )
  );

  const campaigns: MarketingCampaign[] = data?.campaigns ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Marketing Campaigns</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            Provider launch campaigns and their review status.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Link href="/admin/marketing/home"><Btn variant="secondary"><Smartphone size={14} /> Customer Home</Btn></Link>
          <Btn onClick={() => refetch()}><RefreshCw size={14} /> Refresh</Btn>
        </div>
      </div>

      <Card>
        <div style={{ padding: "12px 16px", display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Input
            placeholder="Search campaign name..."
            value={search}
            onChange={setSearch}
          />
          <Select
            value={status}
            onChange={setStatus}
            options={STATUS_OPTIONS}
          />
        </div>
      </Card>

      <Card>
        {loading ? (
          <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 10 }}>
            {[...Array(5)].map((_, i) => <Skeleton key={i} height={40} />)}
          </div>
        ) : campaigns.length === 0 ? (
          <div style={{ padding: 48, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No campaigns found.</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                {["Campaign Name", "Type", "Status", "Marketing Ready", "Provider Review", "Admin Review", "Created", ""].map(h => (
                  <th key={h} style={th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {campaigns.map((c) => (
                <tr key={c.id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "10px 14px", fontWeight: 500 }}>{c.campaign_name}</td>
                  <td style={{ padding: "10px 14px", color: "var(--text-tertiary)" }}>{c.campaign_type}</td>
                  <td style={{ padding: "10px 14px" }}>
                    <Badge variant={statusVariant(c.status)}>{c.status}</Badge>
                  </td>
                  <td style={{ padding: "10px 14px" }}>
                    <Badge variant={c.marketing_ready ? "success" : "warning"}>
                      {c.marketing_ready ? "Ready" : "Not Ready"}
                    </Badge>
                  </td>
                  <td style={{ padding: "10px 14px", color: "var(--text-tertiary)" }}>{c.provider_review_status ?? "—"}</td>
                  <td style={{ padding: "10px 14px" }}>
                    {c.admin_review_status ? (
                      <Badge variant={c.admin_review_status === "approved" ? "success" : c.admin_review_status === "rejected" ? "danger" : "warning"}>
                        {c.admin_review_status}
                      </Badge>
                    ) : "—"}
                  </td>
                  <td style={{ padding: "10px 14px", fontSize: 11, color: "var(--text-tertiary)" }}>
                    {c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}
                  </td>
                  <td style={{ padding: "10px 14px" }}>
                    <Link href={`/admin/marketing/campaigns/${c.id}`}>
                      <Btn size="sm" variant="ghost">
                        <Eye size={14} /> View
                      </Btn>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {!loading && campaigns.length > 0 && (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "10px 14px", borderTop: "1px solid var(--border)", background: "var(--surface-sunken)",
            fontSize: 13, color: "var(--text-tertiary)" }}>
            <span>Page {page}</span>
            <div style={{ display: "flex", gap: 8 }}>
              <Btn size="sm" variant="ghost" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Prev</Btn>
              <Btn size="sm" variant="ghost" onClick={() => setPage(p => p + 1)} disabled={campaigns.length < 20}>Next</Btn>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
