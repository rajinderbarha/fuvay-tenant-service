"use client";
import React, { useCallback, useState } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Card, Badge, Skeleton, Btn, SectionHeader } from "../../../components/shared/ui";
import { financeApi, providerPackageApi } from "../../../lib/api";
import type { CreditPackage, WalletBalance, ProviderPackage } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { useRazorpayCheckout } from "../../../hooks/useRazorpayCheckout";
import { Package, Wallet, Zap, Star, CheckCircle, Clock } from "lucide-react";

const RAZORPAY_KEY = process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID ?? "";

const TYPE_COLORS: Record<string, string> = {
  onboarding: "#7c3aed", security_deposit: "#d97706",
  credit_topup: "#059669", subscription: "#2563eb",
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

export default function PackagesPage() {
  // Category-specific packages (Sprint 6 system)
  const categoryPkgs = useApi(useCallback(() => providerPackageApi.browse(), []));
  const myStatus     = useApi(useCallback(() => providerPackageApi.status(), []));

  // Legacy credit packages (for home services credit top-up via Razorpay)
  const legacyPkgs   = useApi(useCallback(() => financeApi.listPackages(), []));
  const wallet        = useApi(useCallback(() => financeApi.wallet(), []));
  const rzp           = useRazorpayCheckout();

  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const [purchasing, setPurchasing] = useState<string | null>(null);

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
    notify(`${pkg.name} purchased! Wallet credited.`);
  });

  // Category package purchase (creates pending purchase; manual payment flow)
  async function handleCategoryPurchase(pkg: ProviderPackage) {
    setPurchasing(pkg.id);
    try {
      await providerPackageApi.initiatePurchase(pkg.id, "manual");
      notify(`Purchase initiated for "${pkg.name}". Our team will contact you to complete payment.`);
      myStatus.refetch();
    } catch (e: unknown) {
      notify(e instanceof Error ? e.message : "Purchase failed", false);
    } finally {
      setPurchasing(null);
    }
  }

  const model = categoryPkgs.data?.monetization_model;
  const isHomeService = model === "credit_wallet_commission";
  const hasActivePurchase = (myStatus.data?.active_purchases ?? []).length > 0;
  const leadBalance = myStatus.data?.lead_credit_balance ?? 0;

  const bal: WalletBalance | undefined = wallet.data ?? undefined;

  // Use category packages if available, otherwise fall back to legacy
  const showCategoryPackages = (categoryPkgs.data?.packages ?? []).length > 0;

  return (
    <TenantLayout activeNav="packages">
      <SectionHeader
        title="Packages & Plans"
        subtitle="Manage your platform subscription and credit packages"
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

      {/* Status Cards */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(200px,1fr))", gap:14, marginBottom:24 }}>
        {/* Wallet balance (always show for Home Services) */}
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

        {/* Lead credit balance (for subscription/lead_credit model) */}
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

        {/* Active subscription/package */}
        {hasActivePurchase && (
          <Card padding={18} style={{ borderLeft:"3px solid #059669" }}>
            <div style={{ display:"flex", alignItems:"center", gap:10 }}>
              <CheckCircle size={20} style={{ color:"#059669" }}/>
              <div>
                <p style={{ fontSize:11, fontWeight:700, textTransform:"uppercase",
                  letterSpacing:"0.06em", color:"var(--text-tertiary)", margin:0 }}>Active</p>
                <p style={{ fontSize:13, fontWeight:700, color:"#059669", margin:"2px 0 0" }}>
                  {myStatus.data!.active_purchases.length} active plan{myStatus.data!.active_purchases.length > 1 ? "s" : ""}
                </p>
              </div>
            </div>
          </Card>
        )}
      </div>

      {/* Active purchases summary */}
      {hasActivePurchase && (
        <div style={{ marginBottom:24 }}>
          <h3 style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:"0 0 12px" }}>
            Active Purchases
          </h3>
          <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
            {myStatus.data!.active_purchases.map(p => (
              <div key={p.id} style={{ display:"flex", alignItems:"center", gap:12, padding:"10px 14px",
                background:"var(--surface)", borderRadius:10, border:"1px solid var(--border)" }}>
                <CheckCircle size={14} style={{ color:"#059669", flexShrink:0 }}/>
                <div style={{ flex:1 }}>
                  <p style={{ margin:0, fontSize:13, fontWeight:500, color:"var(--text-primary)" }}>
                    {TYPE_LABELS[p.package_type] ?? p.package_type}
                  </p>
                  {p.expires_at && (
                    <p style={{ margin:0, fontSize:11, color:"var(--text-tertiary)" }}>
                      Expires: {new Date(p.expires_at).toLocaleDateString("en-IN")}
                    </p>
                  )}
                </div>
                <Badge variant="success" size="sm">Active</Badge>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Category-specific packages */}
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
              {categoryPkgs.data!.packages.map(pkg => {
                const color = TYPE_COLORS[pkg.package_type] ?? "#64748b";
                const isPurchasing = purchasing === pkg.id;
                return (
                  <Card key={pkg.id} padding={0}
                    style={{ border: pkg.is_recommended ? `2px solid ${color}` : "1px solid var(--border)",
                      position:"relative", overflow:"hidden" }}>
                    {/* Type badge */}
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

                      {/* Price */}
                      <div style={{ margin:"0 0 16px" }}>
                        <span style={{ fontSize:28, fontWeight:800, color }}>
                          ₹{Number(pkg.price).toLocaleString("en-IN")}
                        </span>
                        <span style={{ fontSize:13, color:"var(--text-tertiary)" }}>
                          {BILLING_LABELS[pkg.billing_cycle ?? ""] ?? ""}
                        </span>
                      </div>

                      {/* What's included */}
                      <div style={{ display:"flex", flexDirection:"column", gap:5, marginBottom:16 }}>
                        {Number(pkg.security_deposit_amount) > 0 && (
                          <IncludeRow icon="🔒" text={`₹${Number(pkg.security_deposit_amount).toLocaleString("en-IN")} security deposit`}/>
                        )}
                        {Number(pkg.included_credit_amount) > 0 && (
                          <IncludeRow icon="💳" text={`₹${Number(pkg.included_credit_amount).toLocaleString("en-IN")} wallet credits`}/>
                        )}
                        {pkg.included_lead_credits > 0 && (
                          <IncludeRow icon="⭐" text={`${pkg.included_lead_credits} lead credits`}/>
                        )}
                        {pkg.staff_limit != null && (
                          <IncludeRow icon="👥" text={`Up to ${pkg.staff_limit} staff`}/>
                        )}
                        {pkg.course_limit != null && (
                          <IncludeRow icon="📚" text={`Up to ${pkg.course_limit} courses`}/>
                        )}
                        {pkg.property_limit != null && (
                          <IncludeRow icon="🏠" text={`Up to ${pkg.property_limit} properties`}/>
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

      {/* Legacy credit top-ups for Home Services (if category packages loaded) */}
      {isHomeService && (
        <>
          <h2 style={{ fontSize:16, fontWeight:700, color:"var(--text-primary)", margin:"0 0 16px" }}>
            Instant Credit Top-ups
          </h2>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 16px" }}>
            Top up your wallet instantly via Razorpay — credits appear immediately.
          </p>
          {legacyPkgs.loading ? (
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(220px,1fr))", gap:14 }}>
              {[...Array(3)].map((_,i) => <Skeleton key={i} height={140} style={{ borderRadius:14 }}/>)}
            </div>
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
        </>
      )}

      {/* No packages at all */}
      {!showCategoryPackages && !legacyPkgs.loading && (legacyPkgs.data?.packages ?? []).length === 0 && (
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

      <div style={{ marginTop:24, padding:"14px 18px", borderRadius:12,
        background:"var(--surface-sunken)", border:"1px solid var(--border)" }}>
        <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:0 }}>
          Package purchases require admin confirmation for offline/manual payments.
          Razorpay instant purchases are processed immediately.
          For transaction history, visit the Finance page.
        </p>
      </div>
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
