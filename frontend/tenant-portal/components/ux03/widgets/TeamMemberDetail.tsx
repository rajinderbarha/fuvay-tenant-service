"use client";
/**
 * DESIGN PHASE UX-03 — one reusable team-member detail pattern used for
 * BOTH staff and technician. Technician role additionally renders the
 * availability/active-job/skills/brands/certifications/completed-jobs/
 * rating/parts-activity sections. Never invent role variants — the only
 * canonical tenant roles are tenant_owner | staff | technician.
 */
import React from "react";
import { Card, StatusBadge, Section } from "@serviceos/design-system";
import type { TeamMemberFixture } from "../../../lib/ux03/types";
import { PermissionEditor } from "./PermissionEditor";

export function TeamMemberDetail({ member, readOnly = false }: { member: TeamMemberFixture; readOnly?: boolean }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "0.75rem" }}>
          <div>
            <h2 className="ds-text-section-title" style={{ margin: 0 }}>{member.name}</h2>
            <p className="ds-text-body" style={{ margin: "0.25rem 0", color: "var(--text-secondary)" }}>{member.email}</p>
            <p className="ds-text-body" style={{ margin: 0, color: "var(--text-secondary)", fontSize: "0.75rem" }}>
              {member.jobTitle} <span title="Descriptive only — not an authorization boundary">(descriptive title, not a role)</span>
            </p>
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <StatusBadge status={member.status} />
            <span
              style={{ fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase", color: "var(--brand)", border: "1px solid var(--brand)", borderRadius: "var(--radius-full)", padding: "0.125rem 0.625rem" }}
              title="Canonical tenant role — tenant_owner | staff | technician"
            >
              {member.role}
            </span>
          </div>
        </div>
      </Card>

      {member.technicianDetail && (
        <Section title="Technician Details">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
            <Card title="Availability">
              <StatusBadge status={member.technicianDetail.availability} />
              {member.technicianDetail.activeJobId && (
                <p className="ds-text-body" style={{ marginTop: "0.5rem" }}>Active job: {member.technicianDetail.activeJobId}</p>
              )}
            </Card>
            <Card title="Skills & Brands">
              <p className="ds-text-body">Skills: {member.technicianDetail.skills.join(", ") || "None recorded"}</p>
              <p className="ds-text-body">Brands: {member.technicianDetail.brands.join(", ") || "None recorded"}</p>
            </Card>
            <Card title="Certifications">
              {member.technicianDetail.certifications.length === 0 && <p className="ds-text-body">None on file.</p>}
              {member.technicianDetail.certifications.map((c) => (
                <p key={c.id} className="ds-text-body">{c.label}{c.expiresAt ? ` — expires ${new Date(c.expiresAt).toLocaleDateString()}` : ""}</p>
              ))}
            </Card>
            <Card title="Performance">
              <p className="ds-text-body">Completed jobs: {member.technicianDetail.completedJobsCount}</p>
              <p className="ds-text-body">Rating: {member.technicianDetail.rating ?? "Not yet rated"}</p>
              <p className="ds-text-body">Recent parts activity: {member.technicianDetail.recentPartsActivityCount}</p>
            </Card>
          </div>
        </Section>
      )}

      <Section title="Permissions">
        {member.role === "tenant_owner" ? (
          <p className="ds-text-body" style={{ color: "var(--text-secondary)" }}>
            The tenant owner has full account authority and is not subject to the StaffPermission override table.
          </p>
        ) : (
          <PermissionEditor permissions={member.permissions} readOnly={readOnly} />
        )}
      </Section>
    </div>
  );
}
