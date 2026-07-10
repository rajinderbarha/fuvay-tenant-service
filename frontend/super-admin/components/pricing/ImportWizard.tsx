"use client";
import { useRef, useState } from "react";
import { Modal, Btn, Badge } from "../shared/ui";
import type { ImportPreviewResult, ImportBatch } from "../../lib/api";

interface ImportWizardProps {
  open: boolean;
  onClose: () => void;
  previewFn: (fileName: string, csvText: string) => Promise<ImportPreviewResult>;
  confirmFn: (batchId: string, conflictResolution: "skip" | "override") => Promise<ImportBatch>;
  onComplete?: (batch: ImportBatch) => void;
  columnsHint?: string;
}

type Step = "upload" | "preview" | "report";

export function ImportWizard({ open, onClose, previewFn, confirmFn, onComplete, columnsHint }: ImportWizardProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState<Step>("upload");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<ImportPreviewResult | null>(null);
  const [conflictResolution, setConflictResolution] = useState<"skip" | "override">("skip");
  const [report, setReport] = useState<ImportBatch | null>(null);

  function reset() {
    setStep("upload"); setError(null); setPreview(null); setReport(null); setConflictResolution("skip");
  }
  function handleClose() { reset(); onClose(); }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async ev => {
      const text = ev.target?.result as string;
      setLoading(true); setError(null);
      try {
        const res = await previewFn(file.name, text);
        setPreview(res);
        setStep("preview");
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to preview file.");
      } finally {
        setLoading(false);
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  }

  async function handleConfirm() {
    if (!preview) return;
    setLoading(true); setError(null);
    try {
      const batch = await confirmFn(preview.batch_id, conflictResolution);
      setReport(batch);
      setStep("report");
      onComplete?.(batch);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to confirm import.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal open={open} onClose={handleClose} title="Import CSV">
      <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 480 }}>
        {error && <p style={{ color: "var(--danger-text)", fontSize: 13 }}>{error}</p>}

        {step === "upload" && (
          <>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
              {columnsHint ?? "Upload a CSV file to preview and validate before import."}
            </p>
            <input ref={fileRef} type="file" accept=".csv" style={{ display: "none" }} onChange={handleFileSelect} />
            <Btn variant="primary" size="sm" loading={loading} onClick={() => fileRef.current?.click()}>
              Choose CSV File
            </Btn>
          </>
        )}

        {step === "preview" && preview && (
          <>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <Badge variant="muted">Total: {preview.total_rows}</Badge>
              <Badge variant="success">Valid: {preview.valid_rows}</Badge>
              <Badge variant="danger">Invalid: {preview.invalid_rows}</Badge>
              <Badge variant="warning">Conflicts: {preview.conflict_rows}</Badge>
            </div>
            <div style={{ maxHeight: 320, overflowY: "auto", border: "1px solid var(--border)", borderRadius: 8 }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                    {["#", "City", "Zipcode", "Tier Code", "Status", "Notes"].map(h => (
                      <th key={h} style={{ textAlign: "left", padding: "6px 8px", fontWeight: 700 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.sample_rows.map(row => (
                    <tr key={row.row_no} style={{
                      borderBottom: "1px solid var(--border)",
                      background: row.errors.length ? "var(--danger-bg, #fdecea)" : row.conflict ? "var(--warning-bg, #fff8e6)" : undefined,
                    }}>
                      <td style={{ padding: "6px 8px" }}>{row.row_no}</td>
                      <td style={{ padding: "6px 8px" }}>{row.city}</td>
                      <td style={{ padding: "6px 8px", fontFamily: "monospace" }}>{row.zipcode ?? "—"}</td>
                      <td style={{ padding: "6px 8px" }}>{row.tier_code}</td>
                      <td style={{ padding: "6px 8px" }}>
                        {row.errors.length ? "Invalid" : row.conflict ? "Duplicate Zipcode" : "Valid"}
                      </td>
                      <td style={{ padding: "6px 8px", color: "var(--text-tertiary)" }}>
                        {row.errors.join("; ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {preview.conflict_rows > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <p style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>
                  {preview.conflict_rows} row(s) have a zipcode that already has an active mapping. How should conflicts be resolved?
                </p>
                <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
                  <input type="radio" checked={conflictResolution === "skip"} onChange={() => setConflictResolution("skip")} />
                  Skip conflicting rows (keep existing mappings)
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
                  <input type="radio" checked={conflictResolution === "override"} onChange={() => setConflictResolution("override")} />
                  Override — deactivate the existing mapping and create the new one
                </label>
              </div>
            )}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <Btn variant="secondary" size="sm" onClick={handleClose}>Cancel</Btn>
              <Btn variant="primary" size="sm" loading={loading}
                disabled={preview.valid_rows === 0} onClick={handleConfirm}>
                Confirm Import
              </Btn>
            </div>
          </>
        )}

        {step === "report" && report && (
          <>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <Badge variant="muted">Total: {report.total_rows}</Badge>
              <Badge variant="success">Created: {report.created_rows}</Badge>
              <Badge variant="muted">Skipped: {report.skipped_rows}</Badge>
            </div>
            <div style={{ maxHeight: 280, overflowY: "auto", border: "1px solid var(--border)", borderRadius: 8 }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                    {["#", "City", "Zipcode", "Action", "Reason"].map(h => (
                      <th key={h} style={{ textAlign: "left", padding: "6px 8px", fontWeight: 700 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(report.report_payload?.rows ?? []).map(row => (
                    <tr key={row.row_no} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "6px 8px" }}>{row.row_no}</td>
                      <td style={{ padding: "6px 8px" }}>{row.city}</td>
                      <td style={{ padding: "6px 8px", fontFamily: "monospace" }}>{row.zipcode ?? "—"}</td>
                      <td style={{ padding: "6px 8px" }}>
                        <Badge variant={row.action === "created" ? "success" : "muted"}>{row.action}</Badge>
                      </td>
                      <td style={{ padding: "6px 8px", color: "var(--text-tertiary)" }}>{row.reason ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <Btn variant="primary" size="sm" onClick={handleClose}>Done</Btn>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}
