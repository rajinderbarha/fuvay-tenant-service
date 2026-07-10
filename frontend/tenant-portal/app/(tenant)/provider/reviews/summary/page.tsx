"use client";
import { useCallback } from "react";
import { providerReviewApi, type TenantRatingSummaryRecord } from "../../../../../lib/api";
import { Card, Skeleton } from "../../../../../components/shared/ui";
import { useApi } from "../../../../../hooks/useApi";
import { BarChart2, Star } from "lucide-react";

function Bar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div style={{ flex: 1, height: 8, background: "var(--surface-sunken)", borderRadius: 4, overflow: "hidden" }}>
      <div style={{ width: `${pct}%`, height: "100%", background: "var(--accent)", borderRadius: 4 }} />
    </div>
  );
}

export default function ProviderReviewSummaryPage() {
  const { data, loading } = useApi(useCallback(() => providerReviewApi.getSummary(), []));

  const summary = data as TenantRatingSummaryRecord | null;
  const total = summary?.total_reviews ?? 0;

  const breakdown = summary ? [
    { stars: 5, count: summary.five_star_count },
    { stars: 4, count: summary.four_star_count },
    { stars: 3, count: summary.three_star_count },
    { stars: 2, count: summary.two_star_count },
    { stars: 1, count: summary.one_star_count },
  ] : [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, maxWidth: 700 }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0,
        display: "flex", alignItems: "center", gap: 10 }}>
        <BarChart2 size={22} /> Rating Summary
      </h1>

      {loading ? <Skeleton height={200} /> : !summary ? (
        <Card padding={48} style={{ textAlign: "center" }}>
          <Star size={32} style={{ color: "var(--text-tertiary)", margin: "0 auto 12px" }} />
          <p style={{ color: "var(--text-secondary)", margin: 0 }}>No rating data yet.</p>
        </Card>
      ) : (
        <>
          <Card padding={24}>
            <div style={{ display: "flex", gap: 32, alignItems: "center", flexWrap: "wrap" }}>
              <div style={{ textAlign: "center" }}>
                <p style={{ fontSize: 48, fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>
                  {summary.average_rating}
                </p>
                <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "4px 0 0" }}>
                  Average Rating
                </p>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                  Based on {total} review{total !== 1 ? "s" : ""}
                </p>
              </div>
              <div style={{ flex: 1, minWidth: 200 }}>
                {breakdown.map(b => (
                  <div key={b.stars} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                    <span style={{ fontSize: 12, color: "var(--text-tertiary)", width: 16, textAlign: "right" }}>{b.stars}★</span>
                    <Bar value={b.count} max={total} />
                    <span style={{ fontSize: 12, color: "var(--text-tertiary)", width: 24, textAlign: "right" }}>{b.count}</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          <Card padding={20}>
            <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 12px" }}>
              Dimension Ratings
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12 }}>
              {[
                ["Provider",      summary.provider_average_rating],
                ["Communication", summary.communication_average_rating],
                ["Punctuality",   summary.punctuality_average_rating],
                ["Quality",       summary.quality_average_rating],
                ["Value",         summary.value_average_rating],
              ].map(([label, val]) => (
                <div key={label as string} style={{ background: "var(--surface-sunken)", borderRadius: 8, padding: 12, textAlign: "center" }}>
                  <p style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
                    {val ?? "—"}
                  </p>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>{label}</p>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
