"use client";

import React, { Suspense, useCallback, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ChevronLeft, ChevronRight, RefreshCw } from "lucide-react";
import { Alert, Button, PageHeader, PageShell, Skeleton } from "@serviceos/design-system";
import { useApi } from "../../../../hooks/useApi";
import { apiFetch } from "../../../../lib/api";
import {
  AvailabilityWeekBoard,
  type AvailabilitySchedule,
  type AvailabilityTechnician,
} from "../../../../components/availability/AvailabilityWeekBoard";

interface PlannerResponse {
  generated_at: string;
  timezone: string;
  from: string;
  to: string;
  summary: {
    available_today: number;
    on_leave_today: number;
    total_capacity: number;
    technician_count: number;
    conflicts: number;
  };
  technicians: AvailabilityTechnician[];
  effective_schedules: AvailabilitySchedule[];
  pagination: { total: number; limit: number; offset: number; has_next: boolean };
}

function toISODate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function addDays(iso: string, amount: number): string {
  const date = new Date(`${iso}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + amount);
  return toISODate(date);
}

function startOfWeek(iso: string): string {
  const date = new Date(`${iso}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() - date.getUTCDay());
  return toISODate(date);
}

function compactMonth(iso: string): string {
  const month = new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { month: "short" });
  return month === "Sep" ? "Sept" : month;
}

function weekLabel(from: string, to: string): string {
  const start = new Date(`${from}T00:00:00`);
  const end = new Date(`${to}T00:00:00`);
  return `${String(start.getDate()).padStart(2, "0")} ${compactMonth(from)} – ${String(end.getDate()).padStart(2, "0")} ${compactMonth(to)}`;
}

export default function AvailabilityPage() {
  return (
    <Suspense fallback={<PageShell><Skeleton height={620} /></PageShell>}>
      <AvailabilityPageContent />
    </Suspense>
  );
}

function AvailabilityPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const today = toISODate(new Date());
  const [weekStart, setWeekStart] = useState(() => startOfWeek(today));
  const [selectedStaffId, setSelectedStaffId] = useState<string | null>(() => searchParams.get("staff_id"));
  const [selectedDate, setSelectedDate] = useState(today);
  const weekEnd = addDays(weekStart, 6);

  const planner = useApi(useCallback(async () => {
    const query = new URLSearchParams({
      from: weekStart,
      to: weekEnd,
      focus_date: selectedDate,
      limit: "100",
      offset: "0",
    });
    return apiFetch<PlannerResponse>(`/v1/tenant/home-services/availability?${query}`);
  }, [weekStart, weekEnd, selectedDate]), [weekStart, weekEnd, selectedDate]);

  const days = useMemo(
    () => Array.from({ length: 7 }, (_, index) => addDays(weekStart, index)),
    [weekStart],
  );

  const moveWeek = (direction: -1 | 1) => {
    const shift = direction * 7;
    setWeekStart(current => addDays(current, shift));
    setSelectedDate(current => addDays(current, shift));
  };

  return (
    <PageShell>
      <PageHeader
        eyebrow=""
        title="Availability"
        description="See who's working, who's off, and how full each technician's week is."
        actions={(
          <div className="availability-week-nav" aria-label="Week navigation">
            <button type="button" onClick={() => moveWeek(-1)} aria-label="Previous week">
              <ChevronLeft size={16} />
            </button>
            <span>{weekLabel(weekStart, weekEnd)}</span>
            <button type="button" onClick={() => moveWeek(1)} aria-label="Next week">
              <ChevronRight size={16} />
            </button>
          </div>
        )}
      />

      {planner.loading && (
        <div className="availability-loading" aria-label="Loading availability">
          <div className="availability-kpi-grid">
            {Array.from({ length: 4 }, (_, index) => <Skeleton key={index} height={96} />)}
          </div>
          {Array.from({ length: 3 }, (_, index) => <Skeleton key={index} height={190} />)}
        </div>
      )}

      {planner.error && (
        <Alert tone="danger">
          <div className="availability-error-row">
            <span>{planner.error}</span>
            <Button variant="secondary" size="sm" onClick={planner.refetch}>
              <RefreshCw size={14} /> Retry
            </Button>
          </div>
        </Alert>
      )}

      {planner.data && (
        <AvailabilityWeekBoard
          technicians={planner.data.technicians}
          schedules={planner.data.effective_schedules}
          days={days}
          focusDate={selectedDate}
          selectedStaffId={selectedStaffId}
          onSelectDay={(staffId, date) => {
            setSelectedStaffId(staffId);
            setSelectedDate(date);
          }}
          onCloseDrawer={() => setSelectedStaffId(null)}
          onOpenJob={jobId => router.push(`/service-jobs/${jobId}`)}
        />
      )}
    </PageShell>
  );
}
