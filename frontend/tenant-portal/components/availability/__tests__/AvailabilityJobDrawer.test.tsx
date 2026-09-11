import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AvailabilityJobDrawer } from "../AvailabilityJobDrawer";
import type { BJDetail } from "../../../lib/api";

const detail = {
  booking: {
    booking_number: "BK-001",
    customer_alias: "Customer HS-1234",
    locality: "Ludhiana · 141001",
    issue_summary: "AC is not cooling after running for ten minutes.",
    customer_photo_urls: ["https://example.test/photo.jpg"],
    is_emergency: true,
    price_snapshot: { customer_total: "157.50" },
  },
  job: {
    id: "job-1",
    job_number: "JOB-001",
    status: "completed",
    assignment_status: "accepted",
    scheduled_date: "2026-09-11",
    scheduled_time_window: "09:00-11:00",
    completion_data: { work_summary: "Replaced capacitor", collected_amount: "1375.50", payment_mode: "onsite_cash" },
    warranty_days: 30,
  },
  service_name: "Air Conditioner",
  job_type_label: "Repair",
  problem_name: "AC not cooling",
  technician: { id: "staff-1", full_name: "Amandeep Kumar", designation: "Technician", phone: null },
  stage: { stage: "completed", stage_label: "Completed", is_terminal: true, next_action: null },
  available_actions: [],
  invoice: { customer_payable_amount: "1375.50", total_amount: "1310.00", payment_status: "verified" },
  quote: { customer_payable_amount: "1375.50", total_amount: "1310.00", status: "customer_approved" },
  visit_fee: "150",
  open_complaint_count: 0,
  sla: { sla_status: "NOT_APPLICABLE", next_deadline: null, minutes_remaining: null, minutes_overdue: null, breach_stage: null, source_policy: null },
  workflow_stages: [],
  direct_payment_notice: "Customer pays the provider directly.",
} satisfies BJDetail;

describe("AvailabilityJobDrawer", () => {
  it("shows operational, customer, pricing and completion context", () => {
    render(<AvailabilityJobDrawer jobId="job-1" technicianName={null} detail={detail} loading={false} error={null} onClose={vi.fn()} onOpenDetails={vi.fn()} onOpenDispatch={vi.fn()} />);

    expect(screen.getByRole("complementary", { name: "Allocated job details" })).toBeInTheDocument();
    expect(screen.getByText("JOB-001")).toBeInTheDocument();
    expect(screen.getByText("Amandeep Kumar")).toBeInTheDocument();
    expect(screen.getByText("AC not cooling")).toBeInTheDocument();
    expect(screen.getByText("AC is not cooling after running for ten minutes.")).toBeInTheDocument();
    expect(screen.getAllByText(/₹1,375/)).toHaveLength(2);
    expect(screen.getByText("Replaced capacitor")).toBeInTheDocument();
    expect(screen.getByText("30 days")).toBeInTheDocument();
  });

  it("provides full-detail, dispatch and close actions", () => {
    const onClose = vi.fn();
    const onOpenDetails = vi.fn();
    const onOpenDispatch = vi.fn();
    render(<AvailabilityJobDrawer jobId="job-1" technicianName={null} detail={detail} loading={false} error={null} onClose={onClose} onOpenDetails={onOpenDetails} onOpenDispatch={onOpenDispatch} />);

    fireEvent.click(screen.getByRole("button", { name: "Full job details" }));
    fireEvent.click(screen.getByRole("button", { name: "Manage in dispatch" }));
    fireEvent.click(screen.getByRole("button", { name: "Close job details" }));
    expect(onOpenDetails).toHaveBeenCalledOnce();
    expect(onOpenDispatch).toHaveBeenCalledOnce();
    expect(onClose).toHaveBeenCalledOnce();
  });
});
