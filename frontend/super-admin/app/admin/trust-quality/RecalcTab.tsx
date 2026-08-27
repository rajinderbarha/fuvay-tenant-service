"use client";
import { TableSurface } from "@serviceos/design-system";
/**
 * Recalculation: queue a sweep, watch it run, cancel it, read the history.
 *
 * The button used to POST and then sit there until the entire platform had been
 * re-scored inside that one request. It now queues a job that the background
 * worker claims, so the call returns immediately and this tab polls the job for
 * progress — which is also the only honest way to show a sweep that takes
 * minutes rather than pretending it finished when the request returned.
 */
import React, { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Card, Btn, Badge, Spinner, Select, Input, Pagination } from "../../../components/shared/ui";
import { trustQualityApi, RecalcJob } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";

const PAGE_SIZE = 20;
const POLL_MS = 3000;

const KINDS = [
  { id: "all", label: "Everything", hint: "Badge eligibility and health scores." },
  { id: "badges", label: "Badges only", hint: "Re-evaluate auto-award rules." },
  { id: "health", label: "Health only", hint: "Re-score against health formulas." },
] as const;

const IN_FLIGHT = ["queued", "running", "cancelling"];

function jobTone(s: string): "success" | "danger" | "warning" | "info" | "muted" {
  if (s === "completed") return "success";
  if (s === "failed") return "danger";
  if (s === "completed_with_errors" || s === "cancelling") return "warning";
  if (s === "running" || s === "queued") return "info";
  return "muted";
}

export function RecalcTab() {
  const [page, setPage] = useState(1);
  const [kind, setKind] = useState<"all" | "badges" | "health">("all");
  const [scopeTenant, setScopeTenant] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  const jobs = useApi(
    useCallback(() => trustQualityApi.listRecalcJobs({
      limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }), [page]),
    [page],
  );

  const rows = jobs.data?.items ?? [];
  // `live` is the polled copy of the in-flight job; it supersedes the (staler)
  // row from the last list fetch.
  const [live, setLive] = useState<RecalcJob | null>(null);
  const listed = rows.find(j => IN_FLIGHT.includes(j.status)) ?? null;
  const active = live && IN_FLIGHT.includes(live.status) ? live : listed;

  // Poll only while something is actually in flight — a finished job's page must
  // not keep hitting the API forever just because the tab is left open. One job
  // is fetched rather than a whole page of history, and the list is refetched
  // once, when the sweep reaches a terminal state. Keyed on the job id and the
  // stable `refetch`, not the `jobs` object, which is a new reference every
  // render and would reset the interval before it ever fired.
  const activeId = listed?.id ?? live?.id ?? null;
  const refetchJobs = jobs.refetch;
  useEffect(() => {
    if (!activeId) return;
    let stop = false;
    const tick = async () => {
      try {
        const j = await trustQualityApi.getRecalcJob(activeId);
        if (stop) return;
        setLive(j);
        if (!IN_FLIGHT.includes(j.status)) { clearInterval(t); refetchJobs(); }
      } catch {
        // A transient failure must not kill the poll; the next tick retries.
      }
    };
    const t = setInterval(tick, POLL_MS);
    tick();
    return () => { stop = true; clearInterval(t); };
  }, [activeId, refetchJobs]);

  const start = useAction(async () => {
    setNotice(null);
    const scope = scopeTenant.trim()
      ? { scope_type: "tenant" as const, scope_id: scopeTenant.trim() }
      : undefined;
    const job = await trustQualityApi.recalculate(kind, scope);
    setNotice(job.already_running
      ? "A recalculation is already in flight — showing that one instead of queuing a duplicate."
      : "Queued. The worker picks it up within about 15 seconds.");
    setPage(1);
    setLive(job);
    jobs.refetch();
  });

  const cancel = useAction(async (id: string) => {
    setLive(await trustQualityApi.cancelRecalcJob(id));
    jobs.refetch();
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card>
        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Run a recalculation</div>
        <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 14px" }}>
          Re-evaluates every in-scope target against the active rules. The sweep runs in the
          background — this queues it and reports progress below, so you can leave the page.
        </p>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ minWidth: 200 }}>
            <Select label="What to recalculate" value={kind}
              onChange={v => setKind(v as typeof kind)}
              options={KINDS.map(k => ({ value: k.id, label: k.label }))} />
          </div>
          <div style={{ flex: 1, minWidth: 280 }}>
            <Input label="Limit to one provider (optional)" value={scopeTenant}
              onChange={setScopeTenant}
              placeholder="Tenant ID — leave blank to sweep the whole platform" />
          </div>
          <Btn disabled={!!active || start.loading} onClick={() => start.execute()}>
            {start.loading ? "Queuing…" : active ? "A sweep is already running" : "Queue recalculation"}
          </Btn>
        </div>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "10px 0 0" }}>
          {KINDS.find(k => k.id === kind)?.hint}
        </p>
        {notice && (
          <p style={{ fontSize: 12, color: "var(--info-text)", background: "var(--info-bg)",
            border: "1px solid var(--info-border)", borderRadius: "var(--radius-md)",
            padding: "8px 10px", margin: "12px 0 0" }}>{notice}</p>
        )}
        {start.error && (
          <p style={{ fontSize: 12, color: "var(--danger-text)", margin: "10px 0 0" }}>{start.error}</p>
        )}
      </Card>

      {active && <LiveProgress job={active} onCancel={() => cancel.execute(active.id)} busy={cancel.loading} />}

      <Card padding={0}>
        <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)",
          display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontWeight: 700, fontSize: 14 }}>Job history</span>
          <Btn size="sm" variant="ghost" onClick={() => jobs.refetch()}>
            <RefreshCw size={13} /> Refresh
          </Btn>
        </div>
        {jobs.loading && rows.length === 0 ? <Spinner /> : (
          <>
            <div style={{ overflowX: "auto" }}>
              <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead><tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                  <th style={{ padding: "8px 16px" }}>Type</th>
                  <th style={{ padding: "8px 16px" }}>Scope</th>
                  <th style={{ padding: "8px 16px" }}>Status</th>
                  <th style={{ padding: "8px 16px" }}>Progress</th>
                  <th style={{ padding: "8px 16px" }}>By</th>
                  <th style={{ padding: "8px 16px" }}>When</th>
                  <th style={{ padding: "8px 16px" }}></th>
                </tr></thead>
                <tbody>
                  {rows.map(j => (
                    <tr key={j.id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "8px 16px" }}>{j.job_type}</td>
                      <td style={{ padding: "8px 16px", color: "var(--text-tertiary)", fontSize: 12 }}>
                        {j.scope_type === "tenant" ? `tenant ${(j.scope_id ?? "").slice(0, 8)}` : "platform"}
                      </td>
                      <td style={{ padding: "8px 16px" }}>
                        <Badge variant={jobTone(j.status)}>{j.status.replace(/_/g, " ")}</Badge>
                      </td>
                      <td style={{ padding: "8px 16px" }}>
                        {j.processed_count.toLocaleString()}/{j.total_count.toLocaleString()}
                        {j.failed_count > 0 && (
                          <span style={{ color: "var(--danger-text)" }}> · {j.failed_count.toLocaleString()} failed</span>
                        )}
                      </td>
                      <td style={{ padding: "8px 16px", color: "var(--text-tertiary)" }}>{j.triggered_by}</td>
                      <td style={{ padding: "8px 16px", color: "var(--text-tertiary)", fontSize: 12 }}>
                        {String(j.completed_at ?? j.started_at ?? "").replace("T", " ").slice(0, 19) || "—"}
                      </td>
                      <td style={{ padding: "8px 16px" }}>
                        {IN_FLIGHT.includes(j.status) && j.status !== "cancelling" && (
                          <Btn size="sm" variant="ghost" disabled={cancel.loading}
                            onClick={() => cancel.execute(j.id)}>Cancel</Btn>
                        )}
                      </td>
                    </tr>
                  ))}
                  {rows.length === 0 && (
                    <tr><td colSpan={7} style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)" }}>
                      No recalculations have run yet.
                    </td></tr>
                  )}
                </tbody>
              </TableSurface>
            </div>
            <Pagination page={page} total={jobs.data?.total ?? 0}
              pageSize={PAGE_SIZE} onPage={setPage} alwaysShow />
          </>
        )}
      </Card>

      {rows.some(j => j.error_summary) && (
        <Card>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Recent errors</div>
          {rows.filter(j => j.error_summary).slice(0, 3).map(j => (
            <p key={j.id} style={{ fontSize: 12, color: "var(--danger-text)", margin: "0 0 8px",
              fontFamily: "monospace", wordBreak: "break-word" }}>
              {j.job_type} · {j.error_summary}
            </p>
          ))}
        </Card>
      )}
    </div>
  );
}

/** Live progress for the job currently in flight, refreshed by the parent's poll. */
function LiveProgress({ job, onCancel, busy }: {
  job: RecalcJob; onCancel: () => void; busy: boolean;
}) {
  const pct = job.total_count > 0
    ? Math.min(100, Math.round((job.processed_count / job.total_count) * 100))
    : 0;
  return (
    <Card>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 700 }}>
            {job.status === "queued" ? "Queued — waiting for the worker"
              : job.status === "cancelling" ? "Stopping after the current batch"
              : "Recalculation in progress"}
          </div>
          <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 2 }}>
            {job.job_type} · {job.scope_type === "tenant" ? "single provider" : "whole platform"}
            {job.total_count > 0 && ` · ${job.processed_count.toLocaleString()} of ${job.total_count.toLocaleString()}`}
          </div>
        </div>
        {job.status !== "cancelling" && (
          <Btn size="sm" variant="secondary" disabled={busy} onClick={onCancel}>
            {busy ? "Cancelling…" : "Cancel"}
          </Btn>
        )}
      </div>
      <div style={{ height: 8, background: "var(--border)", borderRadius: 999, overflow: "hidden" }}>
        <div style={{
          height: "100%",
          width: job.status === "queued" ? "100%" : `${pct}%`,
          background: job.status === "queued" ? "var(--border-strong, var(--border))" : "var(--brand)",
          borderRadius: 999, transition: "width 0.6s ease",
        }} />
      </div>
      <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 6 }}>
        {job.status === "queued"
          ? "The background worker checks for new jobs every 15 seconds."
          : `${pct}% complete${job.failed_count > 0 ? ` · ${job.failed_count.toLocaleString()} failed` : ""}`}
      </div>
    </Card>
  );
}
