"use client";
import React, { useState, useEffect } from "react";
import {
  Check, ArrowRight, ArrowLeft, Building2, Tag, Users2, PartyPopper, SkipForward,
} from "lucide-react";
import { tenantSelfApi, pricingApi, authApi } from "../../lib/api";

// ── Steps ─────────────────────────────────────────────────────────────────────
type StepId = "profile" | "service" | "staff" | "done";
const STEPS: { id: StepId; label: string; icon: React.ReactNode }[] = [
  { id: "profile", label: "Business Profile", icon: <Building2 size={15}/> },
  { id: "service", label: "First Service",    icon: <Tag size={15}/> },
  { id: "staff",   label: "Add Staff",        icon: <Users2 size={15}/> },
  { id: "done",    label: "Done",             icon: <PartyPopper size={15}/> },
];

const SERVICE_CATEGORIES = [
  "AC & HVAC", "Plumbing", "Electrical", "Cleaning", "Painting",
  "Carpentry", "Pest Control", "Appliance Repair", "Beauty & Salon", "Fitness",
];

// ── Helpers ───────────────────────────────────────────────────────────────────
function StepDot({ idx, current }: { idx: number; current: number }) {
  const done = current > idx;
  const active = current === idx;
  return (
    <div style={{
      width: 30, height: 30, borderRadius: "50%", flexShrink: 0,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 12, fontWeight: 700,
      border: `2px solid ${done || active ? "var(--brand)" : "var(--border)"}`,
      background: done ? "var(--accent)" : active ? "var(--brand)" : "transparent",
      color: done || active ? "#fff" : "var(--text-tertiary)",
      transition: "all 0.15s",
    }}>
      {done ? <Check size={14}/> : idx + 1}
    </div>
  );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)",
      display: "block", marginBottom: 5 }}>{children}</label>
  );
}

function TextInput({ value, onChange, placeholder, type = "text", hint }: {
  value: string; onChange: (v: string) => void; placeholder?: string; type?: string; hint?: string;
}) {
  return (
    <div>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        style={{ width: "100%", height: 42, padding: "0 14px", fontSize: 14,
          background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: 10, color: "var(--text-primary)", outline: "none",
          fontFamily: "inherit", boxSizing: "border-box" as const }}
        onFocus={e => e.currentTarget.style.borderColor = "var(--border-focus)"}
        onBlur={e  => e.currentTarget.style.borderColor = "var(--border)"}
      />
      {hint && <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "3px 0 0" }}>{hint}</p>}
    </div>
  );
}

function Btn({ children, onClick, disabled, loading, variant = "primary", size = "md" }: {
  children: React.ReactNode; onClick?: () => void; disabled?: boolean;
  loading?: boolean; variant?: "primary" | "ghost" | "secondary"; size?: "md" | "lg";
}) {
  const bg = variant === "primary" ? "var(--brand)"
    : variant === "secondary" ? "var(--surface-raised)"
    : "transparent";
  const color = variant === "primary" ? "white" : "var(--text-primary)";
  const h = size === "lg" ? 46 : 40;
  return (
    <button onClick={onClick} disabled={disabled || loading}
      style={{ height: h, padding: "0 20px", borderRadius: 11, border: variant === "secondary" ? "1px solid var(--border)" : "none",
        background: bg, color, fontWeight: 600, fontSize: 14, cursor: (disabled || loading) ? "not-allowed" : "pointer",
        opacity: (disabled || loading) ? 0.6 : 1, fontFamily: "inherit",
        transition: "opacity 0.15s", display: "flex", alignItems: "center", gap: 8 }}>
      {loading ? "Saving…" : children}
    </button>
  );
}

function ErrorBox({ text }: { text: string }) {
  return (
    <div style={{ padding: "10px 14px", borderRadius: 10, background: "var(--danger-bg)",
      border: "1px solid var(--danger-border)", color: "var(--danger-text)", fontSize: 13, marginBottom: 14 }}>
      {text}
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function OnboardingPage() {
  const [step,    setStep]    = useState(0);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");
  const [tenantName, setTenantName] = useState("");

  // Profile step
  const [description, setDescription] = useState("");
  const [state,       setState]       = useState("");
  const [website,     setWebsite]     = useState("");

  // Service step
  const [category,   setCategory]   = useState(SERVICE_CATEGORIES[0]);
  const [serviceId,  setServiceId]  = useState("");
  const [cityName,   setCityName]   = useState("");
  const [basePrice,  setBasePrice]  = useState("");

  // Staff step
  const [staffName,  setStaffName]  = useState("");
  const [staffEmail, setStaffEmail] = useState("");

  useEffect(() => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("serviceos_tenant_token");
    if (!token) { window.location.href = "/login"; return; }
    const name = localStorage.getItem("serviceos_tenant_name") ?? "";
    setTenantName(name);
    const city = localStorage.getItem("serviceos_tenant_city") ?? "";
    setCityName(city);
  }, []);

  // ── Step handlers ─────────────────────────────────────────────────────────

  async function saveProfile() {
    setError(""); setLoading(true);
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const patch: Record<string, any> = {};
      if (description.trim()) patch.description = description.trim();
      if (state.trim())       patch.state        = state.trim();
      if (website.trim())     patch.website      = website.trim();
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      if (Object.keys(patch).length > 0) await tenantSelfApi.updateProfile(patch as any);
      setStep(1);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save profile.");
    } finally { setLoading(false); }
  }

  async function saveService() {
    setError(""); setLoading(true);
    try {
      const sid = serviceId.trim() || category.toLowerCase().replace(/[^a-z0-9]+/g, "_");
      const city = cityName.trim() || "default";
      const price = parseFloat(basePrice);
      if (!basePrice || isNaN(price) || price <= 0) {
        setError("Enter a valid base price."); setLoading(false); return;
      }
      await pricingApi.setPrice({
        service_type_id: sid,
        service_category: category,
        city_name: city,
        base_price: price,
        unit: "per visit",
        change_reason: "Initial onboarding price",
      });
      setStep(2);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save service price.");
    } finally { setLoading(false); }
  }

  async function saveStaff() {
    setError(""); setLoading(true);
    try {
      if (!staffEmail.trim() || !staffName.trim()) {
        setError("Name and email are required."); setLoading(false); return;
      }
      await authApi.inviteStaff({
        full_name: staffName.trim(),
        email: staffEmail.trim(),
        role: "staff",
      });
      setStep(3);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to invite staff member.");
    } finally { setLoading(false); }
  }

  function skip() { setError(""); setStep(s => s + 1); }

  const stepId = STEPS[step]?.id;

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", padding: "48px 24px",
      display: "flex", flexDirection: "column", alignItems: "center" }}>

      {/* Logo */}
      <div style={{ textAlign: "center", marginBottom: 28 }}>
        <div style={{ width: 52, height: 52, borderRadius: 14, background: "var(--brand)",
          display: "flex", alignItems: "center", justifyContent: "center",
          margin: "0 auto 14px", boxShadow: "var(--shadow-md)" }}>
          <span style={{ color: "white", fontWeight: 800, fontSize: 20 }}>S</span>
        </div>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
          Set up {tenantName || "your business"}
        </h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
          3 quick steps to get you ready to accept your first job
        </p>
      </div>

      {/* Step bar */}
      {stepId !== "done" && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 28 }}>
          {STEPS.slice(0, 3).map((s, i) => (
            <React.Fragment key={s.id}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <StepDot idx={i} current={step}/>
                {step === i && (
                  <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>{s.label}</span>
                )}
              </div>
              {i < 2 && (
                <div style={{ height: 2, width: 32, background: step > i ? "var(--accent)" : "var(--border)", transition: "background 0.15s", flexShrink: 0 }}/>
              )}
            </React.Fragment>
          ))}
        </div>
      )}

      {/* ── Step 1: Profile ────────────────────────────────────────────────── */}
      {stepId === "profile" && (
        <div style={{ width: "100%", maxWidth: 520, background: "var(--surface)",
          border: "1px solid var(--border)", borderRadius: 18, padding: 32, boxShadow: "var(--shadow-lg)" }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>
            Complete your business profile
          </h2>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 22px", lineHeight: 1.5 }}>
            Help customers find and trust you. All fields are optional — you can update these anytime in Settings.
          </p>
          {error && <ErrorBox text={error}/>}
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <FieldLabel>Short Description</FieldLabel>
              <TextInput value={description} onChange={setDescription}
                placeholder="e.g. Trusted AC service in Mumbai since 2018" hint="Shown to customers on your profile"/>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              <div>
                <FieldLabel>State</FieldLabel>
                <TextInput value={state} onChange={setState} placeholder="e.g. Maharashtra"/>
              </div>
              <div>
                <FieldLabel>Website (optional)</FieldLabel>
                <TextInput value={website} onChange={setWebsite} type="url" placeholder="https://yourbusiness.com"/>
              </div>
            </div>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 24 }}>
            <button onClick={skip} style={{ background: "none", border: "none", cursor: "pointer",
              fontSize: 13, color: "var(--text-tertiary)", display: "flex", alignItems: "center", gap: 4 }}>
              <SkipForward size={13}/> Skip for now
            </button>
            <Btn onClick={saveProfile} loading={loading} size="lg">
              Save & Continue <ArrowRight size={15}/>
            </Btn>
          </div>
        </div>
      )}

      {/* ── Step 2: Service ────────────────────────────────────────────────── */}
      {stepId === "service" && (
        <div style={{ width: "100%", maxWidth: 520, background: "var(--surface)",
          border: "1px solid var(--border)", borderRadius: 18, padding: 32, boxShadow: "var(--shadow-lg)" }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>
            Add your first service
          </h2>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 22px", lineHeight: 1.5 }}>
            Set a base price for one service. You can add more from the Finance → Pricing page later.
          </p>
          {error && <ErrorBox text={error}/>}
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <FieldLabel>Service Category</FieldLabel>
              <select
                value={category}
                onChange={e => setCategory(e.target.value)}
                style={{ width: "100%", height: 42, padding: "0 14px", fontSize: 14,
                  background: "var(--surface)", border: "1px solid var(--border)",
                  borderRadius: 10, color: "var(--text-primary)", outline: "none",
                  fontFamily: "inherit", boxSizing: "border-box" as const }}>
                {SERVICE_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              <div>
                <FieldLabel>Service ID (slug)</FieldLabel>
                <TextInput value={serviceId} onChange={setServiceId}
                  placeholder="auto-generated if blank" hint="e.g. ac_service_1ton"/>
              </div>
              <div>
                <FieldLabel>City</FieldLabel>
                <TextInput value={cityName} onChange={setCityName} placeholder="e.g. Mumbai"/>
              </div>
            </div>
            <div>
              <FieldLabel>Base Price (₹ per visit)</FieldLabel>
              <TextInput value={basePrice} onChange={setBasePrice} type="number" placeholder="e.g. 499"/>
            </div>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 24 }}>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => setStep(0)} style={{ background: "none", border: "none",
                cursor: "pointer", fontSize: 13, color: "var(--text-tertiary)",
                display: "flex", alignItems: "center", gap: 4 }}>
                <ArrowLeft size={13}/> Back
              </button>
              <button onClick={skip} style={{ background: "none", border: "none",
                cursor: "pointer", fontSize: 13, color: "var(--text-tertiary)",
                display: "flex", alignItems: "center", gap: 4 }}>
                <SkipForward size={13}/> Skip
              </button>
            </div>
            <Btn onClick={saveService} loading={loading} size="lg">
              Save & Continue <ArrowRight size={15}/>
            </Btn>
          </div>
        </div>
      )}

      {/* ── Step 3: Staff ──────────────────────────────────────────────────── */}
      {stepId === "staff" && (
        <div style={{ width: "100%", maxWidth: 520, background: "var(--surface)",
          border: "1px solid var(--border)", borderRadius: 18, padding: 32, boxShadow: "var(--shadow-lg)" }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>
            Invite your first staff member
          </h2>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 22px", lineHeight: 1.5 }}>
            They&apos;ll get an invitation email to join your ServiceOS workspace. You can invite more from the Staff page.
          </p>
          {error && <ErrorBox text={error}/>}
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <FieldLabel>Full Name</FieldLabel>
              <TextInput value={staffName} onChange={setStaffName} placeholder="e.g. Ravi Kumar"/>
            </div>
            <div>
              <FieldLabel>Email Address</FieldLabel>
              <TextInput value={staffEmail} onChange={setStaffEmail} type="email"
                placeholder="staff@yourbusiness.com" hint="An invite will be sent to this address"/>
            </div>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 24 }}>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => setStep(1)} style={{ background: "none", border: "none",
                cursor: "pointer", fontSize: 13, color: "var(--text-tertiary)",
                display: "flex", alignItems: "center", gap: 4 }}>
                <ArrowLeft size={13}/> Back
              </button>
              <button onClick={skip} style={{ background: "none", border: "none",
                cursor: "pointer", fontSize: 13, color: "var(--text-tertiary)",
                display: "flex", alignItems: "center", gap: 4 }}>
                <SkipForward size={13}/> Skip
              </button>
            </div>
            <Btn onClick={saveStaff} loading={loading} size="lg">
              Send Invite <ArrowRight size={15}/>
            </Btn>
          </div>
        </div>
      )}

      {/* ── Step 4: Done ───────────────────────────────────────────────────── */}
      {stepId === "done" && (
        <div style={{ width: "100%", maxWidth: 480, background: "var(--surface)",
          border: "1px solid var(--border)", borderRadius: 18, padding: 40,
          boxShadow: "var(--shadow-lg)", textAlign: "center" }}>
          <div style={{ width: 70, height: 70, borderRadius: "50%", background: "var(--success-bg)",
            border: "1px solid var(--success-border)",
            display: "flex", alignItems: "center", justifyContent: "center",
            margin: "0 auto 20px", color: "var(--success-text)" }}>
            <PartyPopper size={30}/>
          </div>
          <h2 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>
            You&apos;re all set! 🎉
          </h2>
          <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 28px", lineHeight: 1.6 }}>
            <strong style={{ color: "var(--text-primary)" }}>{tenantName}</strong> is ready on ServiceOS.
            Head to your dashboard to create your first job or booking.
          </p>

          {/* Quick links */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 24 }}>
            {[
              { label: "Create a Job",         href: "/jobs",      icon: "🔧" },
              { label: "View Bookings & Jobs",  href: "/jobs",       icon: "📅" },
              { label: "Manage Staff",          href: "/staff",     icon: "👥" },
              { label: "Configure Pricing",     href: "/finance",   icon: "💰" },
            ].map(link => (
              <a key={link.href} href={link.href} style={{ display: "flex", alignItems: "center", gap: 10,
                padding: "12px 16px", borderRadius:"var(--radius-lg)", background: "var(--surface-sunken)",
                border: "1px solid var(--border)", textDecoration: "none",
                color: "var(--text-primary)", fontSize: 13, fontWeight: 500,
                transition: "border-color 0.15s" }}>
                <span style={{ fontSize: 18, lineHeight: 1 }}>{link.icon}</span>
                {link.label}
                <ArrowRight size={13} style={{ marginLeft: "auto", color: "var(--text-tertiary)" }}/>
              </a>
            ))}
          </div>

          <button onClick={() => { window.location.href = "/dashboard"; }}
            style={{ width: "100%", height: 46, borderRadius: 11, border: "none",
              background: "var(--brand)", color: "white", fontWeight: 700, fontSize: 15,
              cursor: "pointer", fontFamily: "inherit", display: "flex",
              alignItems: "center", justifyContent: "center", gap: 8 }}>
            Go to Dashboard <ArrowRight size={16}/>
          </button>
        </div>
      )}
    </div>
  );
}
