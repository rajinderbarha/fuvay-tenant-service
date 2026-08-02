"use client";
import { useCallback, useEffect, useState } from "react";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import {
  providerServiceOptionApi,
  providerOfferingsApi,
  type ProviderAvailableServiceOption,
  type EnabledOffering,
} from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

type PriceDraft = { pricing_model: "FIXED" | "PER_UNIT"; value: string };

export default function ProviderServiceOptionsPage() {
  const enabledOfferings = useApi(useCallback(() => providerOfferingsApi.listEnabled(), []));
  const services: EnabledOffering[] = enabledOfferings.data?.offerings ?? [];

  const [serviceId, setServiceId] = useState("");
  const [available, setAvailable] = useState<ProviderAvailableServiceOption[]>([]);
  const [selected,  setSelected]  = useState<Set<string>>(new Set());
  const [prices,    setPrices]    = useState<Record<string, PriceDraft>>({}); // keyed by mapping_id
  const [priceErrors, setPriceErrors] = useState<Record<string, string>>({});
  const [loading,   setLoading]   = useState(false);
  const [saving,    setSaving]    = useState(false);
  const [msg,       setMsg]       = useState("");

  async function loadOptions(sid: string) {
    if (!sid) { setAvailable([]); setSelected(new Set()); return; }
    setLoading(true); setMsg("");
    try {
      const res = await providerServiceOptionApi.getAvailableForService(sid);
      const items = (res as unknown as { data: ProviderAvailableServiceOption[] }).data
        ?? (Array.isArray(res) ? res : []);
      setAvailable(items);
      const supportedRes = await providerServiceOptionApi.getSupportedForService(sid);
      const supported = (supportedRes as unknown as { data: { service_option_id: string }[] }).data
        ?? (Array.isArray(supportedRes) ? supportedRes : []);
      setSelected(new Set(supported.map((x: { service_option_id: string }) => x.service_option_id)));
    } catch (err: unknown) {
      setMsg((err as Error).message ?? "Failed to load options");
    }
    setLoading(false);
  }

  // Auto-load when service selection changes
  useEffect(() => {
    loadOptions(serviceId);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serviceId]);

  function toggle(id: string) {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function save() {
    if (!serviceId) return;
    setSaving(true); setMsg(""); setPriceErrors({});
    try {
      await providerServiceOptionApi.setSupportedForService(serviceId, Array.from(selected));
      // Publish price for every enabled option — an enabled option with no
      // valid price must not be allowed to publish (no admin fallback).
      const errors: Record<string, string> = {};
      for (const opt of available) {
        if (!selected.has(opt.id)) continue;
        const draft = prices[opt.mapping_id];
        if (!draft || !draft.value.trim()) {
          errors[opt.mapping_id] = "Enter a price before publishing this option.";
          continue;
        }
        try {
          await providerServiceOptionApi.setOptionPrice(opt.mapping_id, {
            enabled: true,
            pricing_model: draft.pricing_model,
            ...(draft.pricing_model === "FIXED" ? { fixed_price: draft.value } : { unit_price: draft.value }),
          });
        } catch (err: unknown) {
          errors[opt.mapping_id] = (err as Error).message ?? "Couldn't save this price.";
        }
      }
      if (Object.keys(errors).length > 0) {
        setPriceErrors(errors);
        setMsg("Some options couldn't be published — see field errors below.");
      } else {
        setMsg("Saved successfully");
        setTimeout(() => setMsg(""), 2500);
      }
    } catch (err: unknown) {
      setMsg((err as Error).message ?? "Save failed");
    }
    setSaving(false);
  }

  const selectedService = services.find(s => s.offering_id === serviceId);

  return (
    <TenantLayout activeNav="provider">
      <div style={{ maxWidth: 700, padding: "0 4px" }}>
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 4px", color: "var(--text-primary)" }}>
            Service Options
          </h1>
          <p style={{ color: "var(--text-secondary)", margin: 0, fontSize: 14 }}>
            Select which service options (types, variants, add-ons) you support for each service.
            Only admin-approved options mapped to the service are shown.
          </p>
        </div>

        {/* Service selector */}
        <div style={{ marginBottom: 20 }}>
          <label style={{ display: "block", fontSize: 13, fontWeight: 600,
            marginBottom: 6, color: "var(--text-secondary)" }}>
            Select Service
          </label>
          {enabledOfferings.loading ? (
            <div style={{ padding: "10px 14px", borderRadius:"var(--radius-md)", border: "1px solid var(--border)",
              background: "var(--surface-sunken)", fontSize: 13, color: "var(--text-tertiary)" }}>
              Loading your services…
            </div>
          ) : services.length === 0 ? (
            <div style={{ padding: "10px 14px", borderRadius:"var(--radius-md)", border: "1px solid var(--border)",
              background: "var(--surface-sunken)", fontSize: 13, color: "var(--text-tertiary)" }}>
              No enabled services yet. Enable services in Provider → Offerings first.
            </div>
          ) : (
            <select
              value={serviceId}
              onChange={e => setServiceId(e.target.value)}
              style={{ width: "100%", padding: "10px 14px", borderRadius:"var(--radius-md)",
                border: "1px solid var(--border)", background: "var(--bg)",
                color: "var(--text-primary)", fontSize: 14, outline: "none", cursor: "pointer" }}>
              <option value="">— Choose a service —</option>
              {services.map(s => (
                <option key={s.offering_id} value={s.offering_id}>
                  {s.offering_name}
                  {s.status !== "active" ? ` (${s.status})` : ""}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Options list */}
        {serviceId && (
          <div>
            {selectedService && (
              <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)",
                marginBottom: 12 }}>
                Options for: {selectedService.offering_name}
              </p>
            )}

            {loading && (
              <p style={{ color: "var(--text-tertiary)", fontSize: 14 }}>Loading options…</p>
            )}

            {!loading && available.length === 0 && (
              <div style={{ padding: "24px 16px", borderRadius: 10,
                background: "var(--surface-sunken)", border: "1px solid var(--border)",
                textAlign: "center" }}>
                <p style={{ color: "var(--text-secondary)", fontSize: 14, margin: 0 }}>
                  No options mapped to this service yet.
                </p>
                <p style={{ color: "var(--text-tertiary)", fontSize: 12, margin: "6px 0 0" }}>
                  Contact your admin to map service options to this service.
                </p>
              </div>
            )}

            {!loading && available.length > 0 && (
              <>
                <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
                  {[...available].sort((a, b) => a.display_order - b.display_order).map(opt => {
                    const active = selected.has(opt.id) || opt.is_required;
                    const draft = prices[opt.mapping_id] ?? { pricing_model: "FIXED" as const, value: "" };
                    const unitLabel = opt.measurement_unit === "per_unit" || opt.quantity_supported ? "Per Unit" : "Flat";
                    return (
                      <div key={opt.id} style={{ padding: "12px 14px", borderRadius: 12,
                        border: `1px solid ${active ? "var(--brand)" : "var(--border)"}`,
                        background: active ? "var(--surface-sunken)" : "var(--bg)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
                          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: opt.is_required ? "default" : "pointer" }}>
                            <input type="checkbox" checked={active} disabled={opt.is_required}
                              onChange={() => toggle(opt.id)}/>
                            <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>{opt.name}</span>
                            {opt.is_required && <span style={{ fontSize: 11, opacity: 0.75, color: "var(--text-tertiary)" }}>required</span>}
                          </label>
                          <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Unit: {unitLabel}</span>
                        </div>
                        {active && (
                          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
                            <select value={draft.pricing_model}
                              onChange={e => setPrices(p => ({ ...p, [opt.mapping_id]: { ...draft, pricing_model: e.target.value as PriceDraft["pricing_model"] } }))}
                              style={{ padding: "6px 8px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 13 }}>
                              <option value="FIXED">Fixed</option>
                              <option value="PER_UNIT">Per {unitLabel === "Per Unit" ? "Unit" : "Visit"}</option>
                            </select>
                            <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Your price: ₹</span>
                            <input type="number" min="0" value={draft.value}
                              onChange={e => setPrices(p => ({ ...p, [opt.mapping_id]: { ...draft, value: e.target.value } }))}
                              placeholder="0" style={{ width: 100, padding: "6px 8px", borderRadius: 8,
                                border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-primary)", fontSize: 13 }}/>
                            {priceErrors[opt.mapping_id] && (
                              <span style={{ fontSize: 12, color: "var(--danger-text)" }}>{priceErrors[opt.mapping_id]}</span>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <button
                    onClick={save}
                    disabled={saving}
                    style={{ padding: "10px 24px", background: "var(--brand)", color: "#fff",
                      borderRadius:"var(--radius-md)", fontSize: 14, cursor: "pointer", border: "none",
                      fontWeight: 600, opacity: saving ? 0.7 : 1 }}>
                    {saving ? "Saving…" : "Save Selections"}
                  </button>
                  {msg && (
                    <p style={{ margin: 0, fontSize: 14,
                      color: msg.includes("fail") || msg.includes("error") ? "var(--danger-text)" : "var(--success-text)" }}>
                      {msg}
                    </p>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </TenantLayout>
  );
}
