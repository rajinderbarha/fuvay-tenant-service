"use client";
import React, { useState, useCallback } from "react";
import { TenantLayout } from "../../../../components/layout/TenantLayout";
import { Card, SectionHeader, Btn, Badge, Spinner, Modal } from "../../../../components/shared/ui";
import { customerComplianceApi, type CustomerConsentRecord } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import Link from "next/link";

const WITHDRAWABLE = new Set([
  "marketing", "location_access", "notification",
  "profiling", "ai_assistant_processing", "media_processing",
]);

const CONSENT_LABELS: Record<string, string> = {
  marketing:                "Marketing Communications",
  location_access:          "Location Access",
  notification:             "Push Notifications",
  profiling:                "Profiling & Personalisation",
  ai_assistant_processing:  "AI Assistant Processing",
  media_processing:         "Media Processing",
  terms_of_service:         "Terms of Service",
  privacy_policy:           "Privacy Policy",
};

type BadgeVariant = "default" | "success" | "warning" | "danger" | "info" | "muted" | "golden" | "terra";
const ACTION_BADGE: Record<string, BadgeVariant> = {
  granted:   "success",
  withdrawn: "danger",
};

export default function PrivacyPage() {
  const consents = useApi(useCallback(() => customerComplianceApi.listConsents(), []), []);

  const [withdrawType,  setWithdrawType]  = useState<string | null>(null);
  const [withdrawReason, setWithdrawReason] = useState("");
  const [toast, setToast] = useState("");

  const withdrawAction = useAction(useCallback(
    (ct: string, reason: string) => customerComplianceApi.withdrawConsent(ct, reason), []));

  async function handleWithdraw() {
    if (!withdrawType) return;
    await withdrawAction.execute(withdrawType, withdrawReason);
    setToast(`Consent for "${CONSENT_LABELS[withdrawType] ?? withdrawType}" withdrawn.`);
    setWithdrawType(null);
    setWithdrawReason("");
    consents.refetch();
  }

  // Deduplicate to latest event per consent_type
  const latestByType: Record<string, CustomerConsentRecord> = {};
  for (const rec of (consents.data?.records ?? [])) {
    const prev = latestByType[rec.consent_type];
    if (!prev || rec.created_at > prev.created_at) {
      latestByType[rec.consent_type] = rec;
    }
  }
  const consentList = Object.values(latestByType);

  return (
    <TenantLayout>
      <div style={{ padding: "var(--space-6)" }}>
        <SectionHeader
          title="Privacy & Data"
          subtitle="Manage your data rights under the DPDP Act 2023."
        />

        {toast && (
          <div style={{
            background: "var(--color-success-subtle)", color: "var(--color-success)",
            border: "1px solid var(--color-success)", borderRadius: "var(--radius-md)",
            padding: "var(--space-3) var(--space-4)", marginBottom: "var(--space-4)",
          }}>
            {toast}
            <button onClick={() => setToast("")} style={{ marginLeft: 8, cursor: "pointer" }}>✕</button>
          </div>
        )}

        {/* Quick Actions */}
        <div style={{ display: "flex", gap: "var(--space-3)", marginBottom: "var(--space-6)", flexWrap: "wrap" }}>
          <Link href="/account/privacy/requests">
            <Btn variant="primary">My Data Requests</Btn>
          </Link>
          <Link href="/account/privacy/requests/new">
            <Btn variant="secondary">+ New Request</Btn>
          </Link>
        </div>

        {/* Consent Records */}
        <Card>
          <h3 style={{ margin: "0 0 var(--space-4)", fontSize: "var(--font-size-base)", fontWeight: 600 }}>
            Consent Records
          </h3>

          {consents.loading && <Spinner />}
          {consents.error && (
            <p style={{ color: "var(--color-error)" }}>Could not load consent records.</p>
          )}

          {!consents.loading && consentList.length === 0 && (
            <p style={{ color: "var(--color-text-muted)" }}>No consent records found.</p>
          )}

          {consentList.length > 0 && (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--font-size-sm)" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                  {["Type", "Status", "Granted", "Withdrawn", "Action"].map(h => (
                    <th key={h} style={{ textAlign: "left", padding: "var(--space-2) var(--space-3)", fontWeight: 600 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {consentList.map(rec => (
                  <tr key={rec.consent_type} style={{ borderBottom: "1px solid var(--color-border)" }}>
                    <td style={{ padding: "var(--space-2) var(--space-3)" }}>
                      {CONSENT_LABELS[rec.consent_type] ?? rec.consent_type}
                    </td>
                    <td style={{ padding: "var(--space-2) var(--space-3)" }}>
                      <Badge variant={ACTION_BADGE[rec.action] ?? "muted"}>
                        {rec.action === "granted" ? "Active" : "Withdrawn"}
                      </Badge>
                    </td>
                    <td style={{ padding: "var(--space-2) var(--space-3)" }}>
                      {rec.granted_at ? new Date(rec.granted_at).toLocaleDateString() : "—"}
                    </td>
                    <td style={{ padding: "var(--space-2) var(--space-3)" }}>
                      {rec.withdrawn_at ? new Date(rec.withdrawn_at).toLocaleDateString() : "—"}
                    </td>
                    <td style={{ padding: "var(--space-2) var(--space-3)" }}>
                      {WITHDRAWABLE.has(rec.consent_type) && rec.action === "granted" ? (
                        <Btn size="sm" variant="ghost"
                          onClick={() => { setWithdrawType(rec.consent_type); setWithdrawReason(""); }}>
                          Withdraw
                        </Btn>
                      ) : (
                        <span style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-xs)" }}>
                          {rec.action === "withdrawn" ? "Already withdrawn" : "Required"}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        {/* DPDP Info */}
        <Card style={{ marginTop: "var(--space-4)", background: "var(--color-info-subtle)" }}>
          <h4 style={{ margin: "0 0 var(--space-2)", fontSize: "var(--font-size-sm)", fontWeight: 600 }}>
            Your Rights Under DPDP Act 2023
          </h4>
          <ul style={{ margin: 0, paddingLeft: "var(--space-5)", fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
            <li>Right to access your data</li>
            <li>Right to correct inaccurate data</li>
            <li>Right to erasure (where not legally required to retain)</li>
            <li>Right to data portability (export your data)</li>
            <li>Right to withdraw consent for non-essential processing</li>
            <li>Right to raise a grievance</li>
          </ul>
          <p style={{ marginTop: "var(--space-3)", fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
            All requests are processed within 72 hours. Financial records are retained as required by the GST Act (7 years).
          </p>
        </Card>
      </div>

      {/* Withdraw Consent Modal */}
      <Modal open={withdrawType !== null}
        title={withdrawType ? `Withdraw: ${CONSENT_LABELS[withdrawType] ?? withdrawType}` : "Withdraw Consent"}
        onClose={() => setWithdrawType(null)}>
        {withdrawType && (
          <>
            <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)", marginBottom: "var(--space-3)" }}>
              Are you sure you want to withdraw your consent for
              <strong> {CONSENT_LABELS[withdrawType] ?? withdrawType}</strong>?
              This may affect related features.
            </p>
            <label style={{ fontSize: "var(--font-size-sm)", fontWeight: 500 }}>Reason (optional)</label>
            <textarea
              value={withdrawReason}
              onChange={e => setWithdrawReason(e.target.value)}
              placeholder="Why are you withdrawing this consent?"
              rows={3}
              style={{
                width: "100%", marginTop: "var(--space-1)",
                padding: "var(--space-2)", borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                fontSize: "var(--font-size-sm)", resize: "vertical",
              }}
            />
            <div style={{ display: "flex", gap: "var(--space-2)", marginTop: "var(--space-4)", justifyContent: "flex-end" }}>
              <Btn variant="ghost" onClick={() => setWithdrawType(null)}>Cancel</Btn>
              <Btn variant="danger" loading={withdrawAction.loading} onClick={handleWithdraw}>
                Withdraw Consent
              </Btn>
            </div>
          </>
        )}
      </Modal>
    </TenantLayout>
  );
}
