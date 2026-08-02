"use client";
import React, { useCallback, useState } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Card, Badge, Skeleton, Btn, SectionHeader } from "../../../components/shared/ui";
import { financeApi, providerPackageApi, usageCreditsApi, tenantSetupApi } from "../../../lib/api";
import type { CreditPackage, WalletBalance, ProviderPackage } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { useRazorpayCheckout } from "../../../hooks/useRazorpayCheckout";
import { useTenant } from "../../../hooks/useTenant";
import { Package, Wallet, Zap, Star, CheckCircle, Receipt, Shield } from "lucide-react";

const RAZORPAY_KEY = process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID ?? "";

const TYPE_COLORS: Record<string, string> = {
  onboarding: "var(--accent)", security_deposit: "var(--warning)",
  credit_topup: "var(--success)", subscription: "var(--brand)",
  lead_credit: "#db2777", trial: "#64748b", custom: "#94a3b8",
};
const TYPE_LABELS: Record<string, string> = {
  onboarding: "Onboarding", security_deposit: "Security Deposit",
  credit_topup: "Credit Top-up", subscription: "Subscription",
  lead_credit: "Lead Credits", trial: "Free Trial", custom: "Custom",
};
const BILLING_LABELS: Record<string, string> = {
  monthly: "/month", quarterly: "/quarter", yearly: "/year", one_time: " one-time",
};

const safeNum = (v: unknown): number => (typeof v === "number" && isFinite(v)) ? v : 0;

type TabKey = "overview" | "packages" | "ledger" | "deposit";
const TABS: { key: TabKey; label: string; icon: React.ReactNode }[] = [
  { key: "overview", label: "Overview",         icon: <Wallet size={14}/> },
  { key: "packages", label: "Packages & Top-up", icon: <Package size={14}/> },
  { key: "ledger",   label: "Credit Ledger",     icon: <Receipt size={14}/> },
  { key: "deposit",  label: "Security Deposit",  icon: <Shield size={14}/> },
];

export default function PackagesPage() {
  const { vertical } = useTenant();
  const [tab, setTab] = useState<TabKey>("overview");

  // Category-specific packages (Sprint 6 system)
  const categoryPkgs = useApi(useCallback(() => providerPackageApi.browse(), []));
  const myStatus     = useApi(useCallback(() => providerPackageApi.status(), []));

  // Legacy credit packages (for home services credit top-up via Razorpay)
  const legacyPkgs   = useApi(useCallback(() => financeApi.listPackages(), []));
  const wallet        = useApi(useCallback(() => financeApi.wallet(), []));
  const rzp           = useRazorpayCheckout();

  // Usage credit balance + ledger — consolidated in from the old
  // /finance/package and /finance/usage-credit-ledger pages so "Package &
  // Credits" and "Billing" no longer point at different screens.
  const usageCredits = useApi(useCallback(() => usageCreditsApi.getBalance(), []));
  const ledger        = useApi(useCallback(() => usageCreditsApi.getLedger(), []));

  // Security deposit — consolidated in from the old /finance/security-deposit page.
  const depositApi = useApi(useCallback(() => tenantSetupApi.getWallet(), []));
  const depositWallet = depositApi.data as Record<string, unknown> | null;
  const deposit = (depositWallet?.security_deposit ?? depositWallet?.deposit ?? null) as Record<string, unknown> | null;

  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const [purchasing, setPurchasing] = useState<string | null>(null);
  const [renewing, setRenewing] = useState<string | null>(null);

  const notify = (msg: string, ok = true) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 4000);
  };

  // Legacy Razorpay purchase (home services credit top-ups)
  const legacyPurchaseAction = useAction(async (pkg: CreditPackage) => {
    const order = await financeApi.initiateWalletPurchase(pkg.id);
    const key = order.key ?? RAZORPAY_KEY;
    if (!key) throw new Error("Razorpay key not configured. Contact support.");
    const result = await rzp.open({
      keyId: key,
      orderId: order.order_id,
      amountPaise: order.amount_paise ?? order.amount * 100,
      currency: order.currency ?? "INR",
      name: "ServiceOS Credits",
      description: `Purchase ${pkg.name}`,
    });
    await financeApi.confirmWalletPurchase(
      result.razorpay_order_id, result.razorpay_payment_id, result.razorpay_signature, pkg.id,
    );
    wallet.refetch();
    usageCredits.refetch();
    ledger.refetch();
    notify(`${pkg.name} purchased! Wallet credited.`);
  });

  // Category package purchase (creates pending assignment; awaits admin approval)
  async function handleCategoryPurchase(pkg: ProviderPackage) {
    setPurchasing(pkg.id);
    try {
      await providerPackageApi.initiatePurchase(pkg.id);
      notify(`Purchase initiated for "${pkg.name}". Awaiting admin approval.`);
      myStatus.refetch();
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : "Purchase failed", false);
    } finally {
      setPurchasing(null);
    }
  }

  // Renew an already-active/expiring package — re-runs the same purchase flow
  // against the existing package_id (creates a fresh pending assignment for
  // admin approval, same as a first-time purchase).
  async function handleRenew(purchase: { id: string; package_id: string; package_name: string }) {
    setRenewing(purchase.id);
    try {
      await providerPackageApi.initiatePurchase(purchase.package_id);
      notify(`Renewal requested for "${purchase.package_name}". Awaiting admin approval.`);
      myStatus.refetch();
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : "Renewal failed", false);
    } finally {
      setRenewing(null);
    }
  }

  const isHomeService = vertical === "home_services";
  const activePurchases = myStatus.data?.all_purchases ?? [];
  const hasActivePurchase = myStatus.data?.has_active_package ?? false;
  const leadBalance = 0; // lead-credit balance is not part of the real status response

  const bal: WalletBalance | undefined = wallet.data ?? undefined;

  // Use category packages if available, otherwise fall back to legacy
  const showCategoryPackages = (categoryPkgs.data?.available_packages ?? []).length > 0;

  const ledgerEntries = ledger.data?.entries ?? [];
  const lastDeduction = ledgerEntries.find(e => e.event_type === "completed_job_deduction");
  const deductedThisSet = ledgerEntries
    .filter(e => e.event_type === "completed_job_deduction")
    .reduce((sum, e) => sum + Math.abs(e.credit_delta), 0);

  return (
    <TenantLayout activeNav="finance-package">
      <SectionHeader
        title="Packages & Billing"
        subtitle="Your subscription, credit top-ups, usage ledger, and security deposit — all in one place"
        icon={<Package/>}
      />

      {toast && (
        <div style={{ padding:"10px 16px", borderRadius:10, marginBottom:16,
          background: toast.ok ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.ok ? "var(--success-text)" : "var(--danger-text)", fontSize:13 }}>
          {toast.msg}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display:"flex", gap:4, marginBottom:20, borderBottom:"1px solid var(--border)" }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{
            display:"flex", alignItems:"center", gap:6, padding:"10px 16px", fontSize:13, fontWeight:600,
            background:"none", border:"none", borderBottom: tab===t.key ? "2px solid var(--brand)" : "2px solid transparent",
            color: tab===t.key ? "var(--brand)" : "var(--text-secondary)", cursor:"pointer", fontFamily:"inherit",
            marginBottom:-1 }}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <>
          {/* Status Cards */}
          <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(200px,1fr))", gap:14, marginBottom:24 }}>
            {isHomeService && wallet.data && (
              <>
                <Card padding={18} style={{ borderLeft:"3px solid var(--brand)" }}>
                  <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                    <Wallet size={20} style={{ color:"var(--brand)" }}/>
                    <div>
                      <p style={{ fontSize:11, fontWeight:700, textTransform:"uppercase",
                        letterSpacing:"0.06em", color:"var(--text-tertiary)", margin:0 }}>Wallet</p>
                      <p style={{ fontSize:20, fontWeight:800, color:"var(--text-primary)", margin:"2px 0 0" }}>
                        ₹{(bal?.balance ?? 0).toFixed(0)}
                      </p>
                    </div>
                  </div>
                </Card>
                <Card padding={18}>
                  <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                    <Zap size={20} style={{ color:"var(--warning)" }}/>
                    <div>
                      <p style={{ fontSize:11, fontWeight:700, textTransform:"uppercase",
                        letterSpacing:"0.06em", color:"var(--text-tertiary)", margin:0 }}>Available</p>
                      <p style={{ fontSize:20, fontWeight:800, color:"var(--text-primary)", margin:"2px 0 0" }}>
                        ₹{(bal?.available ?? 0).toFixed(0)}
                      </p>
                    </div>
                  </div>
                </Card>
              </>
            )}

            {usageCredits.data && (
              <Card padding={18} style={{ borderLeft: usageCredits.data.low_credit ? "3px solid var(--danger)" : "3px solid var(--border)" }}>
                <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                  <Receipt size={20} style={{ color: usageCredits.data.low_credit ? "var(--danger)" : "var(--text-secondary)" }}/>
                  <div>
                    <p style={{ fontSize:11, fontWeight:700, textTransform:"uppercase",
                      letterSpacing:"0.06em", color:"var(--text-tertiary)", margin:0 }}>Usage Credits</p>
                    <p style={{ fontSize:20, fontWeight:800, color: usageCredits.data.low_credit ? "var(--danger)" : "var(--text-primary)", margin:"2px 0 0" }}>
                      {usageCredits.data.usage_credit_balance}
                    </p>
                  </div>
                </div>
              </Card>
            )}

            {leadBalance > 0 && (
              <Card padding={18} style={{ borderLeft:"3px solid #db2777" }}>
                <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                  <Star size={20} style={{ color:"#db2777" }}/>
                  <div>
                    <p style={{ fontSize:11, fontWeight:700, textTransform:"uppercase",
                      letterSpacing:"0.06em", color:"var(--text-tertiary)", margin:0 }}>Lead Credits</p>
                    <p style={{ fontSize:20, fontWeight:800, color:"var(--text-primary)", margin:"2px 0 0" }}>
                      {leadBalance}
                    </p>
                  </div>
                </div>
              </Card>
            )}

            {hasActivePurchase && (
              <Card padding={18} style={{ borderLeft:"3px solid var(--success)" }}>
                <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                  <CheckCircle size={20} style={{ color:"var(--success)" }}/>
                  <div>
                    <p style={{ fontSize:11, fontWeight:700, textTransform:"uppercase",
                      letterSpacing:"0.06em", color:"var(--text-tertiary)", margin:0 }}>Active</p>
                    <p style={{ fontSize:13, fontWeight:700, color:"var(--success)", margin:"2px 0 0" }}>
                      {activePurchases.length} plan{activePurchases.length > 1 ? "s" : ""}
                    </p>
                  </div>
                </div>
              </Card>
            )}
          </div>

          {usageCredits.data?.low_credit && (
            <div style={{ marginBottom:20, padding:"12px 16px", borderRadius:"var(--radius-md)",
              background:"var(--danger-bg)", border:"1px solid var(--danger-border)" }}>
              <p style={{ fontSize:13, color:"var(--danger-text)", margin:0 }}>
                Your usage credits are running low — completed jobs may fail to deduct.{" "}
                <button onClick={() => setTab("packages")} style={{ color:"var(--danger-text)", fontWeight:700, textDecoration:"underline", background:"none", border:"none", cursor:"pointer", padding:0, fontFamily:"inherit", fontSize:13 }}>
                  Top up now →
                </button>
              </p>
            </div>
          )}

          {/* Active purchases summary */}
          {hasActivePurchase ? (
            <div>
              <h3 style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:"0 0 12px" }}>
                Active Purchases
              </h3>
              <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                {activePurchases.map(p => (
                  <div key={p.id} style={{ display:"flex", alignItems:"center", gap:12, padding:"10px 14px",
                    background:"var(--surface)", borderRadius:10, border:"1px solid var(--border)" }}>
                    <CheckCircle size={14} style={{ color:"var(--success)", flexShrink:0 }}/>
                    <div style={{ flex:1 }}>
                      <p style={{ margin:0, fontSize:13, fontWeight:500, color:"var(--text-primary)" }}>
                        {p.package_name} — {TYPE_LABELS[p.package_type] ?? p.package_type}
                      </p>
                      {p.expires_at && (
                        <p style={{ margin:0, fontSize:11, color:"var(--text-tertiary)" }}>
                          Expires: {new Date(p.expires_at).toLocaleDateString("en-IN")}
                        </p>
                      )}
                    </div>
                    <Badge variant={p.status === "active" ? "success" : "warning"} size="sm">
                      {p.status}
                    </Badge>
                    <Btn variant="secondary" size="sm" loading={renewing === p.id}
                      onClick={() => handleRenew(p)}>
                      Renew
                    </Btn>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <Card padding={32} style={{ textAlign:"center" }}>
              <Package size={28} style={{ color:"var(--text-tertiary)", margin:"0 auto 10px", display:"block" }}/>
              <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 12px" }}>
                You don&apos;t have an active package yet.
              </p>
              <Btn variant="primary" size="sm" onClick={() => setTab("packages")}>Browse Packages</Btn>
            </Card>
          )}
        </>
      )}

      {tab === "packages" && (
        <>
          {/* Instant top-up moved first — it's the most-used action and was
              easy to miss when buried below a long "Available Packages" grid. */}
          {isHomeService && (
            <div style={{ marginBottom:32 }}>
              <h2 style={{ fontSize:16, fontWeight:700, color:"var(--text-primary)", margin:"0 0 4px" }}>
                Instant Credit Top-up
              </h2>
              <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 16px" }}>
                Top up your wallet instantly via Razorpay — credits appear immediately.
              </p>
              {legacyPkgs.loading ? (
                <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(220px,1fr))", gap:14 }}>
                  {[...Array(3)].map((_,i) => <Skeleton key={i} height={140} style={{ borderRadius:14 }}/>)}
                </div>
              ) : legacyPkgs.error ? (
                <Card padding={24} style={{ textAlign:"center", border:"1px solid var(--danger-border)", background:"var(--danger-bg)" }}>
                  <p style={{ fontSize:13, color:"var(--danger-text)", margin:"0 0 8px" }}>
                    Could not load top-up packages: {legacyPkgs.error}
                  </p>
                  <Btn variant="secondary" size="sm" onClick={legacyPkgs.refetch}>Retry</Btn>
                </Card>
              ) : (legacyPkgs.data?.packages ?? []).filter(p => p.is_active).length === 0 ? (
                <Card padding={24} style={{ textAlign:"center" }}>
                  <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>
                    No top-up packages are configured for your account yet. Contact support to enable instant credit top-ups.
                  </p>
                </Card>
              ) : (
                <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(220px,1fr))", gap:14 }}>
                  {(legacyPkgs.data?.packages ?? []).filter(p => p.is_active).map(pkg => (
                    <Card key={pkg.id} padding={20}
                      style={{ border:"1px solid var(--border)", display:"flex", flexDirection:"column" }}>
                      <p style={{ fontSize:15, fontWeight:700, color:"var(--text-primary)", margin:"0 0 6px" }}>
                        {pkg.name}
                      </p>
                      <p style={{ fontSize:22, fontWeight:800, color:"var(--brand)", margin:"0 0 4px" }}>
                        ₹{(pkg.price_inr ?? 0).toFixed(0)}
                      </p>
                      <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"0 0 14px" }}>
                        {(pkg.credits ?? 0).toLocaleString()} credits
                        {(pkg.bonus_credits ?? 0) > 0 && (
                          <span style={{ color:"var(--success-text)", fontWeight:600 }}>
                            {" "}+{pkg.bonus_credits} bonus
                          </span>
                        )}
                      </p>
                      <Btn variant="primary" size="sm" loading={legacyPurchaseAction.loading}
                        onClick={() => legacyPurchaseAction.execute(pkg)}
                        style={{ width:"100%", justifyContent:"center" }}>
                        Buy Now
                      </Btn>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}

          {categoryPkgs.error && !categoryPkgs.loading && (
            <Card padding={24} style={{ textAlign:"center", marginBottom:24,
              border:"1px solid var(--danger-border)", background:"var(--danger-bg)" }}>
              <p style={{ fontSize:13, color:"var(--danger-text)", margin:"0 0 8px" }}>
                Could not load available packages: {categoryPkgs.error}
              </p>
              <Btn variant="secondary" size="sm" onClick={categoryPkgs.refetch}>Retry</Btn>
            </Card>
          )}
          {showCategoryPackages && (
            <>
              <h2 style={{ fontSize:16, fontWeight:700, color:"var(--text-primary)", margin:"0 0 16px" }}>
                Available Packages
              </h2>
              {categoryPkgs.loading ? (
                <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(260px,1fr))", gap:14 }}>
                  {[...Array(3)].map((_,i) => <Skeleton key={i} height={200} style={{ borderRadius:14 }}/>)}
                </div>
              ) : (
                <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(260px,1fr))", gap:16, marginBottom:32 }}>
                  {categoryPkgs.data!.available_packages.map(pkg => {
                    const color = TYPE_COLORS[pkg.package_type] ?? "#64748b";
                    const isPurchasing = purchasing === pkg.id;
                    return (
                      <Card key={pkg.id} padding={0}
                        style={{ border: pkg.is_recommended ? `2px solid ${color}` : "1px solid var(--border)",
                          position:"relative", overflow:"hidden" }}>
                        <div style={{ background:`${color}15`, padding:"12px 16px",
                          borderBottom:"1px solid var(--border)" }}>
                          <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between" }}>
                            <span style={{ fontSize:11, fontWeight:700, color,
                              textTransform:"uppercase", letterSpacing:"0.06em" }}>
                              {TYPE_LABELS[pkg.package_type] ?? pkg.package_type}
                            </span>
                            <div style={{ display:"flex", gap:4 }}>
                              {pkg.is_featured && <Badge variant="warning" size="sm">Featured</Badge>}
                              {pkg.is_recommended && <Badge variant="success" size="sm">Recommended</Badge>}
                            </div>
                          </div>
                        </div>

                        <div style={{ padding:"16px 18px" }}>
                          <p style={{ fontSize:16, fontWeight:700, color:"var(--text-primary)", margin:"0 0 4px" }}>
                            {pkg.name}
                          </p>
                          {pkg.description && (
                            <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"0 0 14px", lineHeight:1.5 }}>
                              {pkg.description}
                            </p>
                          )}

                          <div style={{ margin:"0 0 16px" }}>
                            <span style={{ fontSize:28, fontWeight:800, color }}>
                              ₹{Number(pkg.price).toLocaleString("en-IN")}
                            </span>
                            <span style={{ fontSize:13, color:"var(--text-tertiary)" }}>
                              {BILLING_LABELS[pkg.billing_cycle ?? ""] ?? ""}
                            </span>
                          </div>

                          <div style={{ display:"flex", flexDirection:"column", gap:5, marginBottom:16 }}>
                            {Number(pkg.security_deposit_amount) > 0 && (
                              <IncludeRow icon="🔒" text={`₹${Number(pkg.security_deposit_amount).toLocaleString("en-IN")} security deposit`}/>
                            )}
                            {Number(pkg.included_credit_amount) > 0 && (
                              <IncludeRow icon="💳" text={`₹${Number(pkg.included_credit_amount).toLocaleString("en-IN")} wallet credits`}/>
                            )}
                            {pkg.lead_credits != null && pkg.lead_credits > 0 && (
                              <IncludeRow icon="⭐" text={`${pkg.lead_credits} lead credits`}/>
                            )}
                            {pkg.trial_days != null && pkg.trial_days > 0 && (
                              <IncludeRow icon="⏱" text={`${pkg.trial_days}-day free trial`}/>
                            )}
                          </div>

                          <Btn
                            variant="primary"
                            size="sm"
                            loading={isPurchasing}
                            onClick={() => handleCategoryPurchase(pkg)}
                            style={{ width:"100%", justifyContent:"center" }}>
                            Get Started
                          </Btn>
                        </div>
                      </Card>
                    );
                  })}
                </div>
              )}
            </>
          )}

          {!showCategoryPackages && !legacyPkgs.loading && (legacyPkgs.data?.packages ?? []).length === 0 && !isHomeService && (
            <Card padding={48} style={{ textAlign:"center" }}>
              <Package size={32} style={{ color:"var(--text-tertiary)", margin:"0 auto 12px", display:"block" }}/>
              <p style={{ fontSize:14, color:"var(--text-secondary)", margin:0 }}>
                No packages available for your business category.
              </p>
              <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:"6px 0 0" }}>
                Contact support or check back later.
              </p>
            </Card>
          )}

          <div style={{ marginTop:16, padding:"14px 18px", borderRadius:"var(--radius-lg)",
            background:"var(--surface-sunken)", border:"1px solid var(--border)" }}>
            <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:0 }}>
              Package purchases require admin confirmation for offline/manual payments.
              Razorpay instant top-ups are processed immediately.
            </p>
          </div>
        </>
      )}

      {tab === "ledger" && (
        <>
          {(usageCredits.error || ledger.error) && (
            <div style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius:"var(--radius-lg)", padding: 20, marginBottom: 16, color: "var(--danger-text)" }}>
              Usage credit activity could not be loaded. Retry or contact support with request ID.
              {(usageCredits.requestId || ledger.requestId) && (
                <div style={{ fontSize: 12, marginTop: 4 }}>Request ID: {usageCredits.requestId ?? ledger.requestId}</div>
              )}
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 24 }}>
            {[
              { label: "Usage Credit Balance",   value: safeNum(usageCredits.data?.usage_credit_balance) },
              { label: "Credits Deducted",       value: deductedThisSet },
              { label: "Completed Jobs",         value: ledgerEntries.filter(e => e.event_type === "completed_job_deduction").length },
              { label: "Low Credit Status",      value: usageCredits.data?.low_credit ? "Low" : "Healthy" },
            ].map(card => (
              <Card key={card.label} padding={16}>
                <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 4px" }}>{card.label}</p>
                <p style={{ fontSize: 22, fontWeight: 700, color: card.label === "Low Credit Status" && usageCredits.data?.low_credit ? "var(--danger-text)" : "var(--brand)", margin: 0 }}>{card.value}</p>
              </Card>
            ))}
          </div>

          {lastDeduction && (
            <p style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 16 }}>
              Last Deduction: {Math.abs(lastDeduction.credit_delta)} credits on {new Date(lastDeduction.created_at).toLocaleDateString()}
            </p>
          )}

          {ledger.loading ? (
            <Skeleton height={200} style={{ borderRadius:12 }}/>
          ) : ledgerEntries.length === 0 ? (
            <Card padding={48} style={{ textAlign: "center", color: "var(--text-secondary)" }}>
              No credit transactions found.
            </Card>
          ) : (
            <Card padding={0} style={{ overflow: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "var(--surface-sunken)" }}>
                    {["Date", "Job ID", "Event Type", "Credit Change", "Balance Before", "Balance After", "Reason", "Request ID"].map(col => (
                      <th key={col} style={{ padding: "10px 14px", textAlign: "left", fontSize: 12, color: "var(--text-secondary)", fontWeight: 600 }}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {ledgerEntries.map((entry) => (
                    <tr key={entry.ledger_id} style={{ borderTop: "1px solid var(--border)" }}>
                      <td style={{ padding: "10px 14px", fontSize: 13, color: "var(--text-secondary)" }}>
                        {entry.created_at ? new Date(entry.created_at).toLocaleDateString() : "—"}
                      </td>
                      <td style={{ padding: "10px 14px", fontSize: 13, color: "var(--text-secondary)" }}>{entry.job_id ? entry.job_id.slice(0, 8) : "—"}</td>
                      <td style={{ padding: "10px 14px", fontSize: 13, color: "var(--text-primary)" }}>
                        {entry.event_type === "completed_job_deduction" ? "Completed Job Deduction" : entry.event_type}
                      </td>
                      <td style={{ padding: "10px 14px", fontSize: 13, fontWeight: 600, color: entry.credit_delta < 0 ? "var(--danger-text)" : "var(--success)" }}>
                        {entry.credit_delta > 0 ? "+" : ""}{safeNum(entry.credit_delta)}
                      </td>
                      <td style={{ padding: "10px 14px", fontSize: 13, color: "var(--text-secondary)" }}>{safeNum(entry.balance_before)}</td>
                      <td style={{ padding: "10px 14px", fontSize: 13, color: "var(--text-secondary)" }}>{safeNum(entry.balance_after)}</td>
                      <td style={{ padding: "10px 14px", fontSize: 13, color: "var(--text-secondary)" }}>{entry.reason ?? "—"}</td>
                      <td style={{ padding: "10px 14px", fontSize: 11, color: "var(--text-tertiary)" }}>{entry.request_id ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
        </>
      )}

      {tab === "deposit" && (
        <>
          {depositApi.error && <div style={{ color: "var(--danger-text)", margin: "0 0 16px" }}>Error loading security deposit info.</div>}

          {depositApi.loading ? (
            <Skeleton height={140} style={{ borderRadius:12 }}/>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <Card padding={20}>
                <h3 style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: 15, margin: "0 0 14px" }}>Deposit Status</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <DepositRow label="Status"          value={String(deposit?.status ?? "pending")} />
                  <DepositRow label="Required Amount" value={`${safeNum(deposit?.required_amount ?? 5000)}`} />
                  <DepositRow label="Currency"        value={String(deposit?.currency ?? "INR")} />
                  <DepositRow label="Amount Received" value={safeNum(deposit?.amount_received ?? deposit?.total_paid ?? deposit?.amount)} />
                  {deposit?.received_at ? (
                    <DepositRow label="Received At" value={new Date(deposit.received_at as string).toLocaleDateString()} />
                  ) : null}
                </div>
              </Card>

              <Card padding={20}>
                <h3 style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: 15, margin: "0 0 14px" }}>Important Notes</h3>
                <ul style={{ color: "var(--text-secondary)", fontSize: 13, listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: 10, margin: 0 }}>
                  <li>&#8226; Security deposit is separate from your usage credit balance.</li>
                  <li>&#8226; Deposit status is managed by your administrator.</li>
                  <li>&#8226; Contact support for questions about your security deposit.</li>
                </ul>
              </Card>
            </div>
          )}
        </>
      )}
    </TenantLayout>
  );
}

function IncludeRow({ icon, text }: { icon: string; text: string }) {
  return (
    <div style={{ display:"flex", alignItems:"center", gap:6 }}>
      <span style={{ fontSize:12 }}>{icon}</span>
      <span style={{ fontSize:12, color:"var(--text-secondary)" }}>{text}</span>
    </div>
  );
}

function DepositRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between" }}>
      <span style={{ color: "var(--text-secondary)", fontSize: 13 }}>{label}</span>
      <span style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: 13 }}>{String(value)}</span>
    </div>
  );
}
