"use client";
/**
 * Complaints & Resolution Center -- Phase 1: queue + case Overview/Job
 * Context/Activity, wired to the real tenant-scoped complaints API.
 * Conversation/Evidence/Resolution/revisit/escalation actions ship in a
 * later phase (see delivery report) -- not fabricated here.
 */
import React, { useCallback, Suspense } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { Skeleton } from "../../../../components/shared/ui";
import { ComplaintKpis } from "../../../../components/complaints/ComplaintKpis";
import { ComplaintFilters } from "../../../../components/complaints/ComplaintFilters";
import { ComplaintQueueList } from "../../../../components/complaints/ComplaintQueueList";
import { ComplaintCaseDetail, type ComplaintTab } from "../../../../components/complaints/ComplaintCaseDetail";
import { tenantComplaintsApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

function ComplaintsPageInner() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const selectedId = searchParams.get("complaint");
  const tab = (searchParams.get("tab") as ComplaintTab) || "overview";
  const search = searchParams.get("q") ?? "";
  const status = searchParams.get("status") ?? "";
  const severity = searchParams.get("severity") ?? "";
  const slaState = searchParams.get("sla") ?? "";

  function updateParams(patch: Record<string, string | null>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [k, v] of Object.entries(patch)) {
      if (v) params.set(k, v); else params.delete(k);
    }
    router.replace(`${pathname}?${params.toString()}`);
  }

  const queue = useApi(useCallback(() => tenantComplaintsApi.list({
    search: search || undefined,
    status: status || undefined,
    severity: severity || undefined,
    sla_state: slaState || undefined,
  }), [search, status, severity, slaState]));

  return (
    <TenantLayout activeNav="provider-complaints">
      <div>
        <p style={{ fontSize: 11, fontWeight: 700, color: "var(--brand)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 4px" }}>Customers</p>
        <h1 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Complaints & Resolution Center</h1>
        <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>
          Resolve customer issues with complete job context, clear ownership and SLA control.
        </p>
      </div>

      {queue.loading ? <Skeleton height={100}/> : queue.data && <ComplaintKpis summary={queue.data.summary}/>}

      <ComplaintFilters
        search={search} onSearch={v => updateParams({ q: v || null })}
        status={status} onStatus={v => updateParams({ status: v || null })}
        severity={severity} onSeverity={v => updateParams({ severity: v || null })}
        slaState={slaState} onSlaState={v => updateParams({ sla: v || null })}
        statusOptions={queue.data?.available_filters?.status ?? []}
      />

      <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
        {queue.loading ? <Skeleton height={500} style={{ flex: 1 }}/> : (
          <ComplaintQueueList
            items={queue.data?.complaints ?? []}
            selectedId={selectedId}
            onSelect={id => updateParams({ complaint: id, tab: "overview" })}
          />
        )}
        {selectedId && (
          <ComplaintCaseDetail
            complaintId={selectedId}
            tab={tab}
            onTabChange={t => updateParams({ tab: t })}
          />
        )}
      </div>
    </TenantLayout>
  );
}

/**
 * Real build failure fixed here: this page calls `useSearchParams()`, which
 * Next.js requires to sit inside a Suspense boundary. Without one, static
 * prerendering threw "useSearchParams() should be wrapped in a suspense
 * boundary" and FAILED THE WHOLE PRODUCTION BUILD.
 *
 * The boundary is scoped to the page rather than the layout so the rest of
 * the tenant shell keeps prerendering normally.
 */
export default function ComplaintsPage() {
  return (
    <Suspense fallback={null}>
      <ComplaintsPageInner />
    </Suspense>
  );
}
