"use client";
/**
 * Home Services top-up plans — what providers buy to operate.
 *
 * This replaced the security deposit. A deposit was collateral scaled to
 * headcount; a top-up plan inverts that — the provider buys headcount, and
 * the platform's recourse is the credit balance plus the floor that stops it
 * being spent to nothing.
 *
 * Two things the UI has to make unmissable, because both are money:
 *   1. GST is NOT credit. A ₹5,000 plan costs ₹5,900 and puts ₹5,000 in the
 *      wallet. The form shows that split live rather than after saving.
 *   2. Seats are capacity, not just billing. Slot capacity is derived from
 *      ready technicians, so 3 seats = 3 technicians = 3 jobs bookable in the
 *      same slot.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle, Check, CreditCard, Plus, Star, Trash2, Users, Wallet, X,
} from "lucide-react";

import { AdminLayout } from "../../../components/layout/AdminLayout";
import {
  Badge, Btn, Card, Input, SectionHeader, Skeleton, Textarea,
} from "../../../components/shared/ui";
import { useApi } from "../../../hooks/useApi";
import { topupPlanApi, type TopupPlan } from "../../../lib/api-topup-plans";

const inr = (n: number) =>
  `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;

const emptyForm = {
  name: "",
  base_amount: "5000",
  seats: "3",
  gst_percent: "18",
  description: "",
  sort_order: "0",
  validity_days: "0",
  is_active: true,
  is_default: false,
};

type Form = typeof emptyForm;

export default function TopupPlansConsole() {
  const [form, setForm] = useState<Form>({ ...emptyForm });
  const [editing, setEditing] = useState<TopupPlan | null>(null);
  const [composing, setComposing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const list = useApi(useCallback(() => topupPlanApi.list(), []));
  const plans = list.data?.plans ?? [];

  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(null), 4000);
    return () => clearTimeout(t);
  }, [notice]);

  // Live money split, so an admin sees the GST/wallet breakdown before saving
  // rather than discovering it on the plan card afterwards.
  const preview = useMemo(() => {
    const base = Number(form.base_amount) || 0;
    const gstPct = Number(form.gst_percent) || 0;
    const gst = Math.round(base * gstPct) / 100;
    return { base, gst, total: base + gst, seats: Number(form.seats) || 0 };
  }, [form.base_amount, form.gst_percent, form.seats]);

  async function run(label: string, fn: () => Promise<unknown>) {
    setBusy(true);
    setErr(null);
    try {
      await fn();
      setNotice(label);
      list.refetch();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  function startCreate() {
    setEditing(null);
    setForm({ ...emptyForm });
    setComposing(true);
    setErr(null);
  }

  function startEdit(p: TopupPlan) {
    setEditing(p);
    setForm({
      name: p.name,
      base_amount: String(p.base_amount),
      seats: String(p.seats),
      gst_percent: String(p.gst_percent),
      description: p.description ?? "",
      sort_order: String(p.sort_order),
      validity_days: String(p.validity_days ?? 0),
      is_active: p.is_active,
      is_default: p.is_default,
    });
    setComposing(true);
    setErr(null);
  }

  async function save() {
    const body = {
      name: form.name.trim(),
      base_amount: Number(form.base_amount),
      seats: Number(form.seats),
      gst_percent: Number(form.gst_percent),
      description: form.description.trim() || null,
      sort_order: Number(form.sort_order) || 0,
      validity_days: Number(form.validity_days),
      is_active: form.is_active,
      is_default: form.is_default,
    };
    await run(editing ? "Plan updated" : "Plan created", async () => {
      if (editing) await topupPlanApi.update(editing.id, body);
      else await topupPlanApi.create(body);
      setComposing(false);
      setEditing(null);
    });
  }

  const canSave = form.name.trim().length >= 2 && Number.isFinite(preview.base) && preview.base > 0
    && Number.isInteger(Number(form.seats)) && Number(form.seats) >= 0
    && Number.isFinite(Number(form.gst_percent)) && Number(form.gst_percent) >= 0 && Number(form.gst_percent) <= 100
    && Number.isInteger(Number(form.validity_days)) && Number(form.validity_days) >= 0 && Number(form.validity_days) <= 3650;

  return (
    <AdminLayout>
      <SectionHeader
        title="Provider Technician Plans"
        subtitle="Create the plans providers select during onboarding. Set the price, technician seats and validity, then enable Offered to providers to publish. Staff and managers do not consume paid seats."
        actions={<div style={{ display: "flex", gap: 8 }}>
          <Link href="/admin/notifications?tab=payments"><Btn variant="secondary"><CreditCard size={15}/> Configure Razorpay</Btn></Link>
          <Btn onClick={startCreate} disabled={busy}><Plus size={15} /> New plan</Btn>
        </div>}
      />

      {err && (
        <Card padding={0} style={{ marginBottom: 14, borderColor: "var(--danger)" }}>
          <div style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: 12 }}>
            <AlertTriangle size={16} style={{ color: "var(--danger)", flexShrink: 0, marginTop: 2 }} />
            <div style={{ fontSize: 13 }}>{err}</div>
            <button onClick={() => setErr(null)}
                    style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer" }}>
              <X size={14} />
            </button>
          </div>
        </Card>
      )}
      {notice && (
        <Card padding={0} style={{ marginBottom: 14, borderColor: "var(--success)" }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center", padding: 12, fontSize: 13 }}>
            <Check size={16} style={{ color: "var(--success)" }} /> {notice}
          </div>
        </Card>
      )}

      {/* How seats work — stated once, where the numbers are set. */}
      <Card padding={0} style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: 14, fontSize: 12.5,
                      color: "var(--text-secondary)", lineHeight: 1.6 }}>
          <Users size={16} style={{ color: "var(--brand)", flexShrink: 0, marginTop: 1 }} />
          <span>
            <strong style={{ color: "var(--text-primary)" }}>Seats are capacity.</strong>{" "}
            Slot availability is derived from ready technicians, so a plan granting 3 seats
            lets a provider run 3 technicians and accept 3 jobs in the same time slot.{" "}
            <strong style={{ color: "var(--text-primary)" }}>GST is never credit</strong> — the
            provider pays base + GST, and only the base reaches their wallet.
          </span>
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 420px)", gap: 16, alignItems: "start" }}>
        {/* ── Plans ─────────────────────────────────────────────────────── */}
        <div style={{ display: "grid", gap: 12 }}>
          {list.loading && <Card><Skeleton /></Card>}
          {!list.loading && plans.length === 0 && (
            <Card>
              <div style={{ padding: 30, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>
                No plans yet. Create a plan and enable Offered to providers so providers can purchase technician seats during setup.
              </div>
            </Card>
          )}
          {plans.map(p => (
            <Card key={p.id} padding={0}>
              <div style={{ padding: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                  <span style={{ fontSize: 15, fontWeight: 700 }}>{p.name}</span>
                  {p.is_default && <Badge tone="info"><Star size={10} /> default</Badge>}
                  <Badge tone={p.is_active ? "success" : "muted"}>
                    {p.is_active ? "active" : "retired"}
                  </Badge>
                  <span style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
                    <Btn variant="secondary" size="sm" onClick={() => startEdit(p)} disabled={busy}>Edit</Btn>
                    <Btn variant="danger" size="sm" disabled={busy}
                         onClick={() => run("Plan deleted", () => topupPlanApi.remove(p.id))}>
                      <Trash2 size={13} />
                    </Btn>
                  </span>
                </div>

                {p.description && (
                  <div style={{ fontSize: 12.5, color: "var(--text-secondary)", marginBottom: 12 }}>
                    {p.description}
                  </div>
                )}

                <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                  <Stat label="Provider pays" value={inr(p.total_amount)} strong />
                  <Stat label={`GST @ ${p.gst_percent}%`} value={inr(p.gst_amount)} />
                  <Stat label="Wallet credit" value={inr(p.credited_amount)} icon={<Wallet size={12} />} />
                  <Stat label="Technician seats" value={String(p.seats)} icon={<Users size={12} />} />
                  <Stat label="Validity" value={p.validity_days ? `${p.validity_days} days` : "No expiry"} />
                  <Stat label="Jobs per slot" value={String(p.seats)} />
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* ── Editor ────────────────────────────────────────────────────── */}
        <Card padding={0}>
          {composing ? (
            <div style={{ padding: 16, display: "grid", gap: 12 }}>
              <div style={{ fontSize: 15, fontWeight: 700 }}>
                {editing ? `Edit — ${editing.name}` : "New top-up plan"}
              </div>

              <Input label="Plan name" value={form.name} placeholder="Starter - 3 seats"
                     onChange={v => setForm({ ...form, name: v })} />
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <Input label="Amount before GST (₹)" type="number" value={form.base_amount}
                       onChange={v => setForm({ ...form, base_amount: v })} />
                <Input label="GST %" type="number" value={form.gst_percent}
                       onChange={v => setForm({ ...form, gst_percent: v })} />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <Input label="Technician seats" type="number" value={form.seats}
                       onChange={v => setForm({ ...form, seats: v })} />
                <Input label="Sort order" type="number" value={form.sort_order}
                       onChange={v => setForm({ ...form, sort_order: v })} />
              </div>
              <Textarea label="Description" rows={3} value={form.description}
                        onChange={v => setForm({ ...form, description: v })} />
              <Input label="Validity in days (0 = no expiry)" type="number" value={form.validity_days}
                     onChange={v => setForm({ ...form, validity_days: v })} />

              {/* The split, before saving — not after. */}
              <div style={{ border: "1px solid var(--border)", borderRadius: 10, padding: 12,
                            background: "var(--surface-sunken)", display: "grid", gap: 6, fontSize: 13 }}>
                <Row label="Provider pays" value={inr(preview.total)} strong />
                <Row label={`of which GST (${form.gst_percent || 0}%)`} value={inr(preview.gst)} muted />
                <Row label="Reaches their wallet" value={inr(preview.base)} />
                <Row label="Technicians they may add" value={`${preview.seats}`} />
                <Row label="Staff and managers" value="No paid seats required" />
                <Row label="Validity" value={Number(form.validity_days) > 0 ? `${form.validity_days} days` : "No expiry"} />
                <Row label="Jobs bookable per slot" value={`${preview.seats}`} muted />
              </div>

              <label style={{ fontSize: 12.5, display: "flex", gap: 8, alignItems: "center" }}>
                <input type="checkbox" checked={form.is_active}
                       onChange={e => setForm({ ...form, is_active: e.target.checked })} />
                Offered to providers
              </label>
              <label style={{ fontSize: 12.5, display: "flex", gap: 8, alignItems: "center" }}>
                <input type="checkbox" checked={form.is_default}
                       onChange={e => setForm({ ...form, is_default: e.target.checked })} />
                Default plan (shown to a provider who has never bought one)
              </label>

              <div style={{ display: "flex", gap: 8 }}>
                <Btn onClick={save} disabled={busy || !canSave}>
                  {editing ? "Save changes" : "Create plan"}
                </Btn>
                <Btn variant="secondary" onClick={() => { setComposing(false); setEditing(null); }} disabled={busy}>
                  Cancel
                </Btn>
              </div>

              {editing && (
                <div style={{ fontSize: 11.5, color: "var(--text-tertiary)", lineHeight: 1.6 }}>
                  Re-pricing is safe: what a provider already paid is recorded on their payment
                  order, so past purchases keep their original price and seat count.
                </div>
              )}
            </div>
          ) : (
            <div style={{ padding: 40, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>
              Select a plan to edit, or create a new one.
            </div>
          )}
        </Card>
      </div>
    </AdminLayout>
  );
}

function Stat({ label, value, icon, strong }: {
  label: string; value: string; icon?: React.ReactNode; strong?: boolean;
}) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 9, padding: "8px 12px",
                  background: "var(--surface-sunken)", minWidth: 118 }}>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", display: "flex", alignItems: "center", gap: 4 }}>
        {icon} {label}
      </div>
      <div style={{ fontSize: strong ? 16 : 14, fontWeight: strong ? 700 : 600, marginTop: 2 }}>{value}</div>
    </div>
  );
}

function Row({ label, value, strong, muted }: {
  label: string; value: string; strong?: boolean; muted?: boolean;
}) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
      <span style={{ color: muted ? "var(--text-tertiary)" : "var(--text-secondary)" }}>{label}</span>
      <span style={{ fontWeight: strong ? 700 : 600,
                     color: muted ? "var(--text-tertiary)" : "var(--text-primary)" }}>{value}</span>
    </div>
  );
}
