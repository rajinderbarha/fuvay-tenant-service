"use client";
/**
 * Tenant Activation Center. Backend-authoritative: every gate rendered here
 * comes from GET .../application-status's `activation_gates`
 * (app.engines.vertical_catalog.activation.evaluate_activation_gates) --
 * there is no separate, hardcoded checklist. The tenant never sets its own
 * enrollment to active; this page only reflects what the activation
 * orchestrator has already decided.
 */
import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ShieldCheck, Wallet, Tag, MapPin, Users2, CheckCircle2, AlertTriangle,
  Clock, Lock, RefreshCw, ChevronRight, Rocket,
} from "lucide-react";
import { OnboardingShell } from "../../../components/onboarding/OnboardingShell";
import { Card, Badge, Btn, Skeleton } from "../../../components/shared/ui";
import {
  tenantApplicationStatusApi, financeReadinessApi, activationPaymentApi, ServiceOSError,
  type ApplicationStatus, type ActivationGate, type FinanceReadinessManifest,
} from "../../../lib/api";
import { useRazorpayCheckout } from "../../../hooks/useRazorpayCheckout";

const GATE_ICON: Record<string, React.ReactNode> = {
  category_wallet: <Wallet size={16}/>,
  technician_seats: <Users2 size={16}/>,
  approved_services: <Tag size={16}/>,
  coverage_availability: <MapPin size={16}/>,
  staff_capacity: <Users2 size={16}/>,
  finance_policy: <Wallet size={16}/>,
  vertical_enabled: <ShieldCheck size={16}/>,
};

function gateBadge(state: ActivationGate["state"]): { label: string; variant: "success" | "warning" | "danger" | "muted" } {
  switch (state) {
    case "ready": return { label: "Ready", variant: "success" };
    case "not_required": return { label: "—", variant: "muted" };
    case "action_required": return { label: "Action required", variant: "warning" };
    case "pending": return { label: "Waiting", variant: "muted" };
    case "processing": return { label: "Processing", variant: "warning" };
    case "failed": return { label: "Failed", variant: "danger" };
    case "blocked": return { label: "Blocked", variant: "danger" };
    default: return { label: state, variant: "muted" };
  }
}

const ACTIVITY_LABEL: Record<string, string> = {
  "enrollment.approved_pending_activation": "Setup approved",
  "enrollment.activation_requirements_pending": "Activation requirements created",
  "enrollment.activating": "Activating",
  "enrollment.active": "Activated",
};

function fmtTime(ts: string | null): string {
  if (!ts) return "";
  return new Date(ts).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

export default function ActivationCenterPage() {
  const router = useRouter();
  const [data, setData] = useState<ApplicationStatus | null>(null);
  const [finance, setFinance] = useState<FinanceReadinessManifest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [payingGate, setPayingGate] = useState<string | null>(null);
  const [paymentNotice, setPaymentNotice] = useState<string | null>(null);
  const { open: openCheckout } = useRazorpayCheckout();

  const load = useCallback(() => {
    setError(null);
    Promise.all([tenantApplicationStatusApi.get(), financeReadinessApi.get().catch(() => null)])
      .then(([status, financeManifest]) => {
        setData(status);
        setFinance(financeManifest);
        const activationEligible = [
          "approved", "approved_pending_activation", "activation_requirements_pending", "activating", "active",
        ];
        if (!activationEligible.includes(status.status)) {
          router.replace("/onboarding/application-status");
        }
      })
      .catch((e: unknown) => setError(e instanceof ServiceOSError ? e.message : "We couldn't load your activation status."))
      .finally(() => setLoading(false));
  }, [router]);

  useEffect(() => { load(); }, [load]);

  const payActivationFunding = useCallback(async () => {
    setPaymentNotice(null);
    setPayingGate("funding");
    let startedOrderId: string | null = null;
    try {
      const order = await activationPaymentApi.createFundingOrder();
      if (order.already_confirmed) {
        setPaymentNotice("Your earlier payment was found and confirmed. The checklist has been refreshed.");
        load();
        return;
      }
      startedOrderId = order.order_id;

      // Backend verifies Razorpay's signed order/payment tuple and resolves
      // all money allocations from its own stored order.
      const payment = await openCheckout({
        keyId: order.key, orderId: order.order_id, amountPaise: order.amount_paise,
        currency: order.currency, name: "Fuvay — Home Services Activation",
        description: order.quote?.checkout_mode === "credits_only"
          ? "Starter usage credits"
          : "Technician seats and usage credits",
      });
      await activationPaymentApi.confirmFunding(payment);
      setPaymentNotice("Payment confirmed. The activation checklist has been refreshed.");
      load();
    } catch (e: unknown) {
      if (startedOrderId) {
        try {
          const reconciled = await activationPaymentApi.reconcileFunding(startedOrderId);
          if (reconciled.status === "captured" || reconciled.captured) {
            setPaymentNotice("Payment was captured and reconciled successfully.");
            load();
            return;
          }
        } catch {
          // The next retry performs the same server-side reconciliation.
        }
      }
      setPaymentNotice(e instanceof ServiceOSError ? e.message
        : (e instanceof Error ? e.message : "Payment could not be started."));
    } finally {
      setPayingGate(null);
    }
  }, [openCheckout, load]);

  // Safe, low-frequency polling while activation is in flight -- the tenant
  // never triggers activation itself, it can only happen server-side.
  useEffect(() => {
    if (!data || data.status === "active") return;
    const id = window.setInterval(() => { if (document.visibilityState === "visible") load(); }, 20000);
    return () => window.clearInterval(id);
  }, [data, load]);

  if (loading) {
    return (
      <OnboardingShell activeNav="activation-center" restricted>
        <Skeleton height={70} style={{ marginBottom: 20 }}/>
        <Skeleton height={140} style={{ marginBottom: 20 }}/>
        <Skeleton height={380}/>
      </OnboardingShell>
    );
  }

  if (error || !data) {
    return (
      <OnboardingShell activeNav="activation-center" restricted>
        <Card>
          <div role="alert" style={{ textAlign: "center", padding: "32px 16px" }}>
            <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>
              We couldn&apos;t load your activation status.
            </p>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 16px" }}>{error}</p>
            <Btn variant="secondary" icon={<RefreshCw size={14}/>} onClick={load}>Retry</Btn>
          </div>
        </Card>
      </OnboardingShell>
    );
  }

  const gates = data.activation_gates ?? [];
  const requiredGates = gates.filter(g => g.required);
  const readyCount = requiredGates.filter(g => g.state === "ready" || g.state === "not_required").length;
  const totalRequired = requiredGates.length;
  const pct = totalRequired > 0 ? Math.round((readyCount / totalRequired) * 100) : 100;
  const isActive = data.status === "active";
  const fundingGateKey = gates.find(g =>
    g.key === "category_wallet" && g.state === "action_required"
  )?.key;
  const activityRows = data.review_activity.filter(a => a.action in ACTIVITY_LABEL || a.action.startsWith("enrollment.activ"));

  return (
    <OnboardingShell activeNav="activation-center" restricted>
      <style>{`
        .ac-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; align-items: start; }
        @media (max-width: 980px) { .ac-grid { grid-template-columns: 1fr; } }
        .ac-row { display: flex; align-items: center; gap: 12px; padding: 14px 0; border-bottom: 1px solid var(--border); }
        .ac-row:last-child { border-bottom: none; }
      `}</style>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12, marginBottom: 6 }}>
        <div>
          <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.06em", color: "var(--brand)", margin: "0 0 6px", textTransform: "uppercase" }}>Tenant Onboarding</p>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>Activation center</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Complete the final requirements before your Home Services workspace goes live.</p>
        </div>
        <Badge variant={isActive ? "success" : "warning"} size="lg" dot>
          {data.status_label}
        </Badge>
      </div>

      {error && (
        <div role="alert" style={{ display: "flex", gap: 8, padding: "12px 14px", borderRadius: 10, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", color: "var(--danger-text)", fontSize: 13, margin: "16px 0" }}>
          <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 1 }}/><span>{error}</span>
        </div>
      )}

      {paymentNotice && (
        <div role="status" style={{ display: "flex", gap: 8, padding: "12px 14px", borderRadius: 10, background: "var(--surface-sunken)", border: "1px solid var(--border)", color: "var(--text-secondary)", fontSize: 13, margin: "16px 0" }}>
          <Clock size={15} style={{ flexShrink: 0, marginTop: 1 }}/><span>{paymentNotice}</span>
        </div>
      )}

      <Card style={{ marginTop: 20, marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
          <div style={{
            width: 44, height: 44, borderRadius: "50%", background: "var(--success-bg)",
            border: "1px solid var(--success-border)", display: "flex", alignItems: "center",
            justifyContent: "center", color: "var(--success-text)", flexShrink: 0,
          }}>
            <CheckCircle2 size={22}/>
          </div>
          <div>
            <p style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
              {isActive ? "Your workspace is live" : "Your setup has been approved"}
            </p>
            <p style={{ fontSize: 12.5, color: "var(--text-tertiary)", margin: 0 }}>
              Submission {data.submission_details.submission_id} · Version {data.submission_details.version}
              {data.status_changed_at && ` · approved on ${new Date(data.status_changed_at).toLocaleDateString(undefined, { month: "short", day: "2-digit", year: "numeric" })}`}
            </p>
          </div>
        </div>
      </Card>

      <div className="ac-grid">
        <div style={{ minWidth: 0 }}>
          <Card>
            <p style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Activation checklist</p>
            {gates.length === 0 && <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No activation requirements to display yet.</p>}
            {gates.map((g, i) => {
              const badge = gateBadge(g.state);
              const canAct = g.state === "action_required" && g.action_type;
              return (
                <div className="ac-row" key={g.key}>
                  <span style={{
                    width: 26, height: 26, borderRadius: "50%", display: "flex", alignItems: "center",
                    justifyContent: "center", fontSize: 12, fontWeight: 700, flexShrink: 0,
                    color: badge.variant === "success" ? "var(--success-text)" : "var(--text-tertiary)",
                    border: `1px solid ${badge.variant === "success" ? "var(--success-border)" : "var(--border)"}`,
                  }}>
                    {badge.variant === "success" ? <CheckCircle2 size={14}/> : i + 1}
                  </span>
                  <span style={{ color: "var(--text-tertiary)", flexShrink: 0 }}>{GATE_ICON[g.key] ?? <Clock size={16}/>}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: 13.5, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{g.label}</p>
                    <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                      {g.tenant_visible_message ?? g.blocking_reason ?? ""}
                    </p>
                  </div>
                  <Badge variant={badge.variant} size="sm">{badge.label}</Badge>
                  {canAct && g.key === fundingGateKey && (
                    <Btn variant="secondary" size="sm" disabled={payingGate === "funding"}
                         onClick={payActivationFunding}>
                      {payingGate === "funding" ? "Opening…" : (finance?.activation_requirements?.funding_quote?.checkout_label ?? "Complete funding")}
                    </Btn>
                  )}
                  {canAct && g.key !== "category_wallet" && (
                    <Btn variant="secondary" size="sm" onClick={() => router.push("/help")}>Resolve</Btn>
                  )}
                </div>
              );
            })}
            <div style={{ display: "flex", gap: 8, padding: "12px 14px", borderRadius: 10, background: "var(--surface-sunken)", border: "1px solid var(--border)", fontSize: 12, color: "var(--text-secondary)", marginTop: 14 }}>
              <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 1, color: "var(--text-tertiary)" }}/>
              <span>Your workspace activates automatically after every required gate passes. You cannot bypass these checks.</span>
            </div>
          </Card>

          <Card style={{ marginTop: 16 }}>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Activation activity</p>
            {activityRows.length === 0 && <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>No activity yet.</p>}
            {activityRows.map((a, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <CheckCircle2 size={14} style={{ color: "var(--success-text)" }}/>
                  <span style={{ fontSize: 12.5, color: "var(--text-secondary)" }}>{ACTIVITY_LABEL[a.action] ?? a.action}</span>
                </div>
                <span style={{ fontSize: 11.5, color: "var(--text-tertiary)" }}>{fmtTime(a.occurred_at)}</span>
              </div>
            ))}
          </Card>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Activation progress</p>
            <div style={{ textAlign: "center" }}>
              <p style={{ fontSize: 34, fontWeight: 800, color: pct === 100 ? "var(--success)" : "var(--brand)", margin: 0 }}>{pct}%</p>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{readyCount} of {totalRequired} gates ready</p>
            </div>
          </Card>

          {finance && (
            <Card>
              <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>Finance policy</p>
              <PolicyRow label="Revenue model" value={finance.policy.revenue_model}/>
              <PolicyRow label="Customer pays" value={finance.policy.customer_pays}/>
              <PolicyRow label="Usage credits" value="Optional until the booking floor"/>
              <PolicyRow label="Technician seats" value="Purchase before adding technicians"/>
              <PolicyRow label="Policy version" value={finance.policy.policy_version}/>
            </Card>
          )}

          <Card>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>What goes live</p>
            {[
              "Customer catalog", "Provider matching", "Bookings & jobs", "Staff workspace", "Home Services finance",
            ].map(text => (
              <div key={text} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0" }}>
                <CheckCircle2 size={14} style={{ color: isActive ? "var(--success-text)" : "var(--text-tertiary)" }}/>
                <span style={{ fontSize: 12.5, color: "var(--text-secondary)" }}>{text}</span>
              </div>
            ))}
          </Card>
        </div>
      </div>

      <div style={{ position: "sticky", bottom: 0, display: "flex", justifyContent: "space-between", padding: "16px 0", marginTop: 24, background: "var(--bg-gradient)" }}>
        <Btn variant="secondary" onClick={() => router.push("/onboarding/application-status")}>Back to application status</Btn>
        {isActive ? (
          <Btn variant="primary" icon={<Rocket size={14}/>} onClick={() => router.push("/dashboard")}>Go to workspace</Btn>
        ) : (
          <Btn variant="secondary" disabled icon={<Lock size={14}/>}>Available after activation</Btn>
        )}
      </div>
    </OnboardingShell>
  );
}

function PolicyRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, padding: "7px 0", borderBottom: "1px solid var(--border)" }}>
      <span style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span style={{ fontWeight: 600, color: "var(--text-primary)", textAlign: "right" }}>{value}</span>
    </div>
  );
}
