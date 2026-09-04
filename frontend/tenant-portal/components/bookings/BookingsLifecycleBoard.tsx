"use client";

import React from "react";
import type { BJItem } from "../../lib/api";

const BOARD_STAGES = [
  { key: "new", label: "New", tone: "warning" },
  { key: "assignment", label: "Assignment", tone: "warning" },
  { key: "scheduled", label: "Scheduled", tone: "neutral" },
  { key: "on_the_way", label: "On the way", tone: "neutral" },
  { key: "inspection", label: "Inspection", tone: "neutral" },
  { key: "estimate_approval", label: "Awaiting estimate", tone: "neutral" },
  { key: "in_progress", label: "Work in progress", tone: "neutral" },
  { key: "payment", label: "Payment", tone: "neutral" },
  { key: "completed", label: "Completed", tone: "brand" },
] as const;

export function BookingsLifecycleBoard({
  items,
  selectedJobId,
  onOpen,
}: {
  items: BJItem[];
  selectedJobId: string | null;
  onOpen: (jobId: string) => void;
}) {
  return (
    <div className="bj-board" aria-label="Bookings lifecycle board">
      {BOARD_STAGES.map(column => {
        const jobs = items.filter(row => row.stage === column.key);
        return (
          <section className="bj-board-column" key={column.key} aria-label={`${column.label}, ${jobs.length} jobs`}>
            <header className="bj-board-head">
              <span className="bj-board-title"><i className="bj-board-dot" data-tone={column.tone}/>{column.label}</span>
              <span className="bj-board-count">{jobs.length}</span>
            </header>
            <div className="bj-board-cards">
              {jobs.length ? jobs.map(row => (
                <button
                  type="button"
                  key={row.service_job_id}
                  className="bj-board-card"
                  aria-current={selectedJobId === row.service_job_id}
                  onClick={() => onOpen(row.service_job_id)}
                >
                  <span className="bj-board-card-top"><strong>{row.job_number}</strong><BoardSlaLabel row={row}/></span>
                  <span className="bj-board-service">{row.service_name ?? "Service unavailable"}</span>
                  <span className="bj-board-customer">{row.customer_alias ?? "Private customer"}</span>
                  <span className="bj-board-card-foot">
                    <span data-unassigned={!row.assigned_staff_name}>{row.assigned_staff_name || "Unassigned"}</span>
                    <span className="bj-board-time">{row.scheduled_time_window ?? "Time pending"}</span>
                  </span>
                </button>
              )) : <div className="bj-board-empty">No jobs</div>}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function BoardSlaLabel({ row }: { row: BJItem }) {
  const status = row.sla?.sla_status ?? "NOT_APPLICABLE";
  if (status === "NOT_APPLICABLE") return <span className="bj-board-sla">—</span>;
  const danger = status === "BREACHED";
  const warning = status === "AT_RISK";
  return (
    <span className="bj-board-sla" data-tone={danger ? "danger" : warning ? "warning" : "success"}>
      {danger ? `${row.sla?.minutes_overdue ?? 0}m overdue` : warning ? `${row.sla?.minutes_remaining ?? 0}m left` : "On track"}
    </span>
  );
}
