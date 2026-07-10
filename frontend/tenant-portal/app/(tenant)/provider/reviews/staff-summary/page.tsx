"use client";
import { useCallback } from "react";
import { providerReviewApi, type StaffRatingSummaryRecord } from "../../../../../lib/api";
import { Card, Badge, Skeleton } from "../../../../../components/shared/ui";
import { useApi } from "../../../../../hooks/useApi";
import { Users } from "lucide-react";

export default function ProviderStaffSummaryPage() {
  const { data, loading } = useApi(useCallback(() => providerReviewApi.getStaffSummary(), []));
  const summaries: StaffRatingSummaryRecord[] = (Array.isArray(data) ? data : []) as StaffRatingSummaryRecord[];

  function ratingVariant(r: string): "success"|"warning"|"danger" {
    const n = parseFloat(r);
    if (n >= 4) return "success";
    if (n >= 3) return "warning";
    return "danger";
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, maxWidth: 800 }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0,
        display: "flex", alignItems: "center", gap: 10 }}>
        <Users size={22} /> Staff Rating Summary
      </h1>
      <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>
        Per-staff review averages aggregated from approved customer reviews.
      </p>

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {[0,1,2].map(i => <Skeleton key={i} height={80} />)}
        </div>
      ) : summaries.length === 0 ? (
        <Card padding={48} style={{ textAlign: "center" }}>
          <Users size={32} style={{ color: "var(--text-tertiary)", margin: "0 auto 12px" }} />
          <p style={{ color: "var(--text-secondary)", margin: 0 }}>No staff rating data yet.</p>
        </Card>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {summaries.map((s: StaffRatingSummaryRecord) => (
            <Card key={s.id} padding={16}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                <div>
                  <p style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)", margin: 0 }}>
                    Staff: {s.staff_member_id.slice(0, 12)}...
                  </p>
                  <div style={{ display: "flex", gap: 12, marginTop: 6, fontSize: 11, color: "var(--text-tertiary)", flexWrap: "wrap" }}>
                    <span>Comms: {s.communication_average_rating}</span>
                    <span>Punctual: {s.punctuality_average_rating}</span>
                    <span>Quality: {s.quality_average_rating}</span>
                    <span>{s.total_reviews} review{s.total_reviews !== 1 ? "s" : ""}</span>
                  </div>
                </div>
                <Badge variant={ratingVariant(s.average_rating)}>★ {s.average_rating}</Badge>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
