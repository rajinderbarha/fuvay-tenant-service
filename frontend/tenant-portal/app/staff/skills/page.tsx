"use client";
import { TableSurface } from "@serviceos/design-system";
import React, { useCallback } from "react";
import { StaffLayout } from "../../../components/layout/StaffLayout";
import { Card, StatCard, Badge, Skeleton, EmptyState } from "../../../components/shared/ui";
import { useApi } from "../../../hooks/useApi";
import { staffSelfApi } from "../../../lib/api";
import { Wrench } from "lucide-react";

export default function StaffSkillsPage() {
  const skills = useApi(useCallback(() => staffSelfApi.getMySkills(), []));
  const list = skills.data?.skills ?? [];

  return (
    <StaffLayout activeNav="skills">
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>Skills & Assigned Services</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
          Skills are assigned by your tenant manager and mapped to the platform service catalog.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 20 }}>
        {skills.loading ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height={92}/>) : (
          <>
            <StatCard label="Active Skills" value={list.length}/>
            <StatCard label="Assigned Services" value={skills.data?.supported_offering_ids?.length ?? 0}/>
            <StatCard label="Pending Skill Requests" value={0}/>
            <StatCard label="Coverage Status" value={skills.data?.status === "active" ? "Active" : "Inactive"}/>
          </>
        )}
      </div>

      <Card padding={0}>
        {skills.loading ? <Skeleton height={140}/> : skills.error ? (
          <div style={{ padding: 20 }}>
            <p style={{ color: "var(--danger-text)", fontSize: 13 }}>{skills.error}{skills.requestId && ` — Request ID: ${skills.requestId}`}</p>
          </div>
        ) : list.length === 0 ? (
          <EmptyState icon={<Wrench/>} title="No skills assigned yet."
            description="Your tenant manager assigns skills mapped to the platform service catalog."/>
        ) : (
          <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["Skill", "Status", "Updated At"].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {list.map((s, i) => (
                <tr key={i} style={{ borderBottom: "1px solid var(--border-subtle, var(--border))" }}>
                  <td style={{ padding: "10px 16px" }}>{s}</td>
                  <td style={{ padding: "10px 16px" }}><Badge variant="success" size="sm">Active</Badge></td>
                  <td style={{ padding: "10px 16px", color: "var(--text-tertiary)" }}>—</td>
                </tr>
              ))}
            </tbody>
          </TableSurface>
        )}
      </Card>

      <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 12 }}>
        Skill update requests are not yet supported from this app — contact your tenant manager to change your assigned skills.
      </p>
    </StaffLayout>
  );
}
