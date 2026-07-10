"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  bulkSetupApi, BulkSetupDraft, BulkNewService,
  BulkPreviewItem, BulkBlocker, BulkPreviewSummary,
} from "../../../../../lib/api";

const STEPS = [
  "Choose Category", "Select Services", "Apply Templates",
  "Brand Mapping", "Options + Issues", "Docs + Checklists",
  "Pricing + Commission", "Workflow", "Review Preview", "Apply",
];

const VERTICALS = ["home_services", "coaching", "real_estate", "restaurant", "salon", "automotive", "professional", "other"];

export default function BulkWizardDetailPage() {
  const { draftId } = useParams<{ draftId: string }>();
  const [draft, setDraft] = useState<BulkSetupDraft | null>(null);
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Step 1
  const [selectedCatId, setSelectedCatId] = useState("");
  const [newCatName, setNewCatName] = useState("");
  const [vertical, setVertical] = useState("");
  const [availableCategories, setAvailableCategories] = useState<unknown[]>([]);

  // Step 2
  const [selectedServiceIds, setSelectedServiceIds] = useState<string[]>([]);
  const [bulkServiceText, setBulkServiceText] = useState("");
  const [availableServices, setAvailableServices] = useState<unknown[]>([]);

  // Step 3
  const [selectedTemplateIds, setSelectedTemplateIds] = useState<string[]>([]);
  const [availableTemplates, setAvailableTemplates] = useState<unknown[]>([]);

  // Steps 4-8: stored in payload JSON
  const [previewResult, setPreviewResult] = useState<{
    can_apply: boolean; summary: BulkPreviewSummary; items: BulkPreviewItem[]; blockers: BulkBlocker[];
  } | null>(null);

  const [applyResult, setApplyResult] = useState<{ run_id: string; status: string; summary: Record<string, number> } | null>(null);
  const [applying, setApplying] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const d = await bulkSetupApi.getDraft(draftId);
      setDraft(d);
      setStep(d.current_step);
      setVertical(d.target_vertical_type ?? "");
      setSelectedCatId(d.target_category_id ?? "");
      setSelectedServiceIds(d.selected_service_ids_json ?? []);
      setSelectedTemplateIds(d.selected_template_ids_json ?? []);
      if (d.preview_summary_json) {
        // restore preview if already done
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [draftId]);

  useEffect(() => {
    if (step === 1 && vertical) {
      bulkSetupApi.getAvailableCategories({ vertical_type: vertical })
        .then(setAvailableCategories);
    }
    if (step === 2 && selectedCatId) {
      bulkSetupApi.getAvailableServices({ category_id: selectedCatId })
        .then(setAvailableServices);
    }
    if (step === 3) {
      bulkSetupApi.getAvailableTemplates({ vertical_type: vertical })
        .then(setAvailableTemplates);
    }
  }, [step, vertical, selectedCatId]);

  const saveCategory = async () => {
    setSaving(true);
    try {
      await bulkSetupApi.setCategory(draftId, {
        category_id: selectedCatId || undefined,
        vertical_type: vertical,
        new_category_payload: newCatName ? { name: newCatName } : undefined,
      });
      setStep(2);
    } finally { setSaving(false); }
  };

  const saveServices = async () => {
    setSaving(true);
    const newServices: BulkNewService[] = bulkServiceText
      .split("\n")
      .map(l => l.trim())
      .filter(Boolean)
      .map(name => ({ service_name: name }));
    try {
      await bulkSetupApi.setServices(draftId, {
        selected_service_ids: selectedServiceIds,
        new_services: newServices,
      });
      setStep(3);
    } finally { setSaving(false); }
  };

  const saveTemplates = async () => {
    setSaving(true);
    try {
      await bulkSetupApi.setTemplates(draftId, { template_ids: selectedTemplateIds });
      setStep(4);
    } finally { setSaving(false); }
  };

  const runPreview = async () => {
    setSaving(true);
    try {
      const res = await bulkSetupApi.previewDraft(draftId);
      setPreviewResult(res);
      setStep(9);
      await load();
    } finally { setSaving(false); }
  };

  const runApply = async () => {
    setApplying(true);
    try {
      const res = await bulkSetupApi.applyDraft(draftId);
      setApplyResult(res);
      setStep(10);
      await load();
    } finally { setApplying(false); }
  };

  const toggleServiceId = (id: string) =>
    setSelectedServiceIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);

  const toggleTemplateId = (id: string) =>
    setSelectedTemplateIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);

  if (loading) return <div style={{ padding: "2rem" }}>Loading...</div>;
  if (!draft) return <div style={{ padding: "2rem" }}>Draft not found.</div>;

  return (
    <div style={{ padding: "1.5rem", maxWidth: "960px" }}>
      {/* Header */}
      <div style={{ marginBottom: "1.5rem" }}>
        <a href="/admin/service-setup/bulk-wizard" style={{ color: "#6b7280", fontSize: "0.85rem", textDecoration: "none" }}>
          ← Back to Wizards
        </a>
        <h1 style={{ fontSize: "1.4rem", fontWeight: 700, margin: "0.5rem 0 0" }}>
          Bulk Setup — {draft.target_vertical_type ?? "New Setup"}
        </h1>
        <div style={{ fontSize: "0.75rem", color: "#9ca3af" }}>Draft: {draft.id}</div>
      </div>

      {/* Progress bar */}
      <div style={{ display: "flex", gap: "0.25rem", marginBottom: "1.75rem" }}>
        {STEPS.map((label, i) => (
          <div key={i} onClick={() => i + 1 <= step && setStep(i + 1)}
            style={{
              flex: 1, padding: "0.35rem 0.25rem", textAlign: "center", fontSize: "0.65rem",
              fontWeight: 600, borderRadius: "0.25rem", cursor: i + 1 <= step ? "pointer" : "default",
              background: i + 1 === step ? "#1e3a5f" : i + 1 < step ? "#93c5fd" : "#f3f4f6",
              color: i + 1 === step ? "#fff" : i + 1 < step ? "#1e3a5f" : "#9ca3af",
            }}>
            {i + 1}. {label}
          </div>
        ))}
      </div>

      {/* Step 1 — Category */}
      {step === 1 && (
        <div>
          <h2 style={{ fontWeight: 700, marginBottom: "1rem" }}>Step 1 — Choose Vertical &amp; Category</h2>
          <div style={{ marginBottom: "1rem" }}>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.25rem" }}>Vertical Type</label>
            <select value={vertical} onChange={e => setVertical(e.target.value)}
              style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.5rem 0.75rem" }}>
              <option value="">Select...</option>
              {VERTICALS.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
          {availableCategories.length > 0 && (
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.25rem" }}>Select Existing Category</label>
              <select value={selectedCatId} onChange={e => setSelectedCatId(e.target.value)}
                style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.5rem 0.75rem" }}>
                <option value="">— or create new below —</option>
                {(availableCategories as Array<{ id: string; name: string }>).map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          )}
          <div style={{ marginBottom: "1.25rem" }}>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.25rem" }}>Or: New Category Name</label>
            <input value={newCatName} onChange={e => setNewCatName(e.target.value)}
              placeholder="e.g. Home Appliance Repair"
              style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.5rem 0.75rem", boxSizing: "border-box" }} />
          </div>
          <button onClick={saveCategory} disabled={saving || (!selectedCatId && !newCatName)}
            style={{ background: "#1e3a5f", color: "#fff", border: "none", padding: "0.5rem 1.5rem", borderRadius: "0.375rem", cursor: "pointer", fontWeight: 600, opacity: saving ? 0.6 : 1 }}>
            {saving ? "Saving..." : "Next →"}
          </button>
        </div>
      )}

      {/* Step 2 — Services */}
      {step === 2 && (
        <div>
          <h2 style={{ fontWeight: 700, marginBottom: "1rem" }}>Step 2 — Select or Create Services</h2>
          {availableServices.length > 0 && (
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.5rem" }}>Existing Services (click to select)</label>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                {(availableServices as Array<{ id: string; service_name: string }>).map(s => (
                  <button key={s.id} onClick={() => toggleServiceId(s.id)}
                    style={{
                      padding: "0.3rem 0.75rem", borderRadius: "9999px", border: "1px solid",
                      borderColor: selectedServiceIds.includes(s.id) ? "#1e3a5f" : "#d1d5db",
                      background: selectedServiceIds.includes(s.id) ? "#1e3a5f" : "#fff",
                      color: selectedServiceIds.includes(s.id) ? "#fff" : "#374151",
                      cursor: "pointer", fontSize: "0.8rem",
                    }}>
                    {s.service_name}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div style={{ marginBottom: "1.25rem" }}>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.25rem" }}>
              Bulk Add New Services (one per line)
            </label>
            <textarea value={bulkServiceText} onChange={e => setBulkServiceText(e.target.value)}
              rows={6}
              placeholder={"AC Repair\nAC Installation\nGeyser Repair\nWashing Machine Repair\nRefrigerator Repair\nMicrowave Repair"}
              style={{ width: "100%", border: "1px solid #d1d5db", borderRadius: "0.375rem", padding: "0.5rem 0.75rem", fontFamily: "monospace", fontSize: "0.85rem", boxSizing: "border-box" }} />
          </div>
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <button onClick={() => setStep(1)} style={{ padding: "0.5rem 1rem", border: "1px solid #d1d5db", borderRadius: "0.375rem", background: "#fff", cursor: "pointer" }}>← Back</button>
            <button onClick={saveServices} disabled={saving}
              style={{ background: "#1e3a5f", color: "#fff", border: "none", padding: "0.5rem 1.5rem", borderRadius: "0.375rem", cursor: "pointer", fontWeight: 600, opacity: saving ? 0.6 : 1 }}>
              {saving ? "Saving..." : "Next →"}
            </button>
          </div>
        </div>
      )}

      {/* Step 3 — Templates */}
      {step === 3 && (
        <div>
          <h2 style={{ fontWeight: 700, marginBottom: "1rem" }}>Step 3 — Apply Service Setup Templates</h2>
          {availableTemplates.length === 0 ? (
            <p style={{ color: "#6b7280" }}>No published templates available for this vertical.</p>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "1.25rem" }}>
              {(availableTemplates as Array<{ id: string; name: string; description?: string; template_type: string }>).map(t => (
                <div key={t.id} onClick={() => toggleTemplateId(t.id)}
                  style={{
                    border: `2px solid ${selectedTemplateIds.includes(t.id) ? "#1e3a5f" : "#e5e7eb"}`,
                    borderRadius: "0.5rem", padding: "0.85rem", cursor: "pointer",
                    background: selectedTemplateIds.includes(t.id) ? "#eff6ff" : "#fff",
                  }}>
                  <div style={{ fontWeight: 700, fontSize: "0.9rem" }}>{t.name}</div>
                  {t.description && <div style={{ fontSize: "0.78rem", color: "#6b7280", marginTop: "0.25rem" }}>{t.description}</div>}
                  <div style={{ fontSize: "0.72rem", color: "#9ca3af", marginTop: "0.25rem" }}>{t.template_type}</div>
                </div>
              ))}
            </div>
          )}
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <button onClick={() => setStep(2)} style={{ padding: "0.5rem 1rem", border: "1px solid #d1d5db", borderRadius: "0.375rem", background: "#fff", cursor: "pointer" }}>← Back</button>
            <button onClick={saveTemplates} disabled={saving}
              style={{ background: "#1e3a5f", color: "#fff", border: "none", padding: "0.5rem 1.5rem", borderRadius: "0.375rem", cursor: "pointer", fontWeight: 600, opacity: saving ? 0.6 : 1 }}>
              {saving ? "Saving..." : "Next →"}
            </button>
          </div>
        </div>
      )}

      {/* Steps 4-8 — Mapping configuration (simplified) */}
      {step >= 4 && step <= 8 && (
        <div>
          <h2 style={{ fontWeight: 700, marginBottom: "0.5rem" }}>Step {step} — {STEPS[step - 1]}</h2>
          <p style={{ color: "#6b7280", marginBottom: "1.5rem" }}>
            Configure {STEPS[step - 1].toLowerCase()} for the selected services. Selections are saved to the draft and previewed in Step 9.
          </p>
          <div style={{ background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: "0.5rem", padding: "1.25rem", marginBottom: "1.25rem", color: "#6b7280", fontSize: "0.85rem" }}>
            Bulk mapping configuration is stored in the draft <code>bulk_setup_payload_json</code>.
            You can update mappings via the API or proceed to preview.
          </div>
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <button onClick={() => setStep(step - 1)} style={{ padding: "0.5rem 1rem", border: "1px solid #d1d5db", borderRadius: "0.375rem", background: "#fff", cursor: "pointer" }}>← Back</button>
            <button onClick={() => setStep(step + 1)}
              style={{ background: "#1e3a5f", color: "#fff", border: "none", padding: "0.5rem 1.5rem", borderRadius: "0.375rem", cursor: "pointer", fontWeight: 600 }}>
              Next →
            </button>
          </div>
        </div>
      )}

      {/* Step 9 — Preview */}
      {step === 9 && (
        <div>
          <h2 style={{ fontWeight: 700, marginBottom: "1rem" }}>Step 9 — Review Preview</h2>
          <button onClick={runPreview} disabled={saving}
            style={{ background: "#0891b2", color: "#fff", border: "none", padding: "0.5rem 1.25rem", borderRadius: "0.375rem", cursor: "pointer", fontWeight: 600, marginBottom: "1.25rem", opacity: saving ? 0.6 : 1 }}>
            {saving ? "Generating Preview..." : "Run Preview"}
          </button>

          {previewResult && (
            <>
              {previewResult.blockers.length > 0 && (
                <div style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "0.5rem", padding: "1rem", marginBottom: "1rem" }}>
                  <div style={{ fontWeight: 700, color: "#dc2626", marginBottom: "0.5rem" }}>
                    {previewResult.blockers.filter(b => b.severity === "P0").length} Blocking Error(s)
                  </div>
                  {previewResult.blockers.map((b, i) => (
                    <div key={i} style={{ fontSize: "0.8rem", color: "#dc2626", marginBottom: "0.25rem" }}>
                      [{b.severity}] {b.code}: {b.message}
                    </div>
                  ))}
                </div>
              )}

              <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: "0.5rem", marginBottom: "1.25rem" }}>
                {Object.entries(previewResult.summary).map(([k, v]) => (
                  <div key={k} style={{ background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: "0.375rem", padding: "0.6rem", textAlign: "center" }}>
                    <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#1e3a5f" }}>{v}</div>
                    <div style={{ fontSize: "0.7rem", color: "#6b7280" }}>{k}</div>
                  </div>
                ))}
              </div>

              <div style={{ maxHeight: "350px", overflow: "auto", border: "1px solid #e5e7eb", borderRadius: "0.5rem" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ background: "#f9fafb" }}>
                      {["Type", "Name", "Action", "Reason"].map(h => (
                        <th key={h} style={{ textAlign: "left", padding: "0.5rem 0.75rem", fontSize: "0.7rem", color: "#6b7280", fontWeight: 600, borderBottom: "1px solid #e5e7eb" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewResult.items.map((item, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid #f3f4f6" }}>
                        <td style={{ padding: "0.45rem 0.75rem", fontSize: "0.75rem", fontFamily: "monospace", color: "#6b7280" }}>{item.entity_type}</td>
                        <td style={{ padding: "0.45rem 0.75rem", fontSize: "0.8rem" }}>{item.name}</td>
                        <td style={{ padding: "0.45rem 0.75rem" }}>
                          <span style={{
                            fontSize: "0.7rem", padding: "0.15rem 0.4rem", borderRadius: "9999px",
                            background: item.action.startsWith("create") ? "#dcfce7" : item.action === "skip" ? "#f3f4f6" : "#dbeafe",
                            color: item.action.startsWith("create") ? "#166534" : item.action === "skip" ? "#6b7280" : "#1d4ed8",
                          }}>
                            {item.action}
                          </span>
                        </td>
                        <td style={{ padding: "0.45rem 0.75rem", fontSize: "0.75rem", color: "#9ca3af" }}>{item.reason ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div style={{ display: "flex", gap: "0.75rem", marginTop: "1.25rem" }}>
                <button onClick={() => setStep(8)} style={{ padding: "0.5rem 1rem", border: "1px solid #d1d5db", borderRadius: "0.375rem", background: "#fff", cursor: "pointer" }}>← Back</button>
                {previewResult.can_apply && (
                  <button onClick={() => setStep(10)}
                    style={{ background: "#16a34a", color: "#fff", border: "none", padding: "0.5rem 1.5rem", borderRadius: "0.375rem", cursor: "pointer", fontWeight: 600 }}>
                    Proceed to Apply →
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* Step 10 — Apply */}
      {step === 10 && (
        <div>
          <h2 style={{ fontWeight: 700, marginBottom: "1rem" }}>Step 10 — Apply Setup</h2>
          {!applyResult ? (
            <>
              {draft.preview_summary_json && (
                <div style={{ background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: "0.5rem", padding: "1rem", marginBottom: "1.25rem" }}>
                  <div style={{ fontWeight: 600, marginBottom: "0.5rem" }}>Preview Summary</div>
                  <div style={{ display: "flex", gap: "0.75rem", fontSize: "0.85rem" }}>
                    {Object.entries(draft.preview_summary_json).map(([k, v]) => (
                      <span key={k}><strong>{v as number}</strong> {k}</span>
                    ))}
                  </div>
                </div>
              )}
              <div style={{ background: "#fff7ed", border: "1px solid #fed7aa", borderRadius: "0.5rem", padding: "1rem", marginBottom: "1.25rem", fontSize: "0.85rem", color: "#c2410c" }}>
                ⚠️ This will apply all setup changes to the platform. Existing mappings will be skipped. New records will be created. This action cannot be undone automatically.
              </div>
              <div style={{ display: "flex", gap: "0.75rem" }}>
                <button onClick={() => setStep(9)} style={{ padding: "0.5rem 1rem", border: "1px solid #d1d5db", borderRadius: "0.375rem", background: "#fff", cursor: "pointer" }}>← Back</button>
                <button onClick={runApply} disabled={applying}
                  style={{ background: "#16a34a", color: "#fff", border: "none", padding: "0.5rem 1.75rem", borderRadius: "0.375rem", cursor: "pointer", fontWeight: 700, fontSize: "1rem", opacity: applying ? 0.6 : 1 }}>
                  {applying ? "Applying..." : "Apply Bulk Setup"}
                </button>
              </div>
            </>
          ) : (
            <div>
              <div style={{ background: applyResult.status === "completed" ? "#f0fdf4" : "#fef2f2", border: `1px solid ${applyResult.status === "completed" ? "#bbf7d0" : "#fecaca"}`, borderRadius: "0.5rem", padding: "1.5rem", marginBottom: "1.25rem" }}>
                <div style={{ fontWeight: 700, fontSize: "1.1rem", marginBottom: "0.5rem", color: applyResult.status === "completed" ? "#16a34a" : "#dc2626" }}>
                  {applyResult.status === "completed" ? "✓ Setup Applied Successfully" : "⚠ Setup Applied with Errors"}
                </div>
                <div style={{ display: "flex", gap: "1rem", fontSize: "0.85rem" }}>
                  {Object.entries(applyResult.summary || {}).map(([k, v]) => (
                    <span key={k}><strong>{v}</strong> {k}</span>
                  ))}
                </div>
                <div style={{ marginTop: "0.75rem", fontSize: "0.8rem", color: "#6b7280" }}>
                  Run ID: <code>{applyResult.run_id}</code>
                </div>
              </div>
              <div style={{ display: "flex", gap: "0.75rem" }}>
                <a href="/admin/service-setup/bulk-wizard" style={{ padding: "0.5rem 1rem", border: "1px solid #d1d5db", borderRadius: "0.375rem", color: "#374151", textDecoration: "none" }}>
                  ← All Wizards
                </a>
                <a href={`/admin/service-setup/bulk-runs/${applyResult.run_id}`}
                  style={{ padding: "0.5rem 1rem", background: "#1e3a5f", color: "#fff", borderRadius: "0.375rem", textDecoration: "none", fontWeight: 600 }}>
                  View Run Detail
                </a>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
