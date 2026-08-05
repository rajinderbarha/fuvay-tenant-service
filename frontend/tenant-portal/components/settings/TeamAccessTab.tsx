"use client";
import React, { useCallback } from "react";
import { Users2, ExternalLink } from "lucide-react";
import { Card, Badge, Skeleton } from "../shared/ui";
import { workspaceSettingsApi } from "../../lib/api";
import { useApi } from "../../hooks/useApi";

export function TeamAccessTab() {
  const team = useApi(useCallback(() => workspaceSettingsApi.getTeamAccess(), []));
  if (team.loading) return <Skeleton height={300}/>;
  if (!team.data) return <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>{team.error ?? "Could not load team access."}</p>;
  const d = team.data;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 780 }}>
      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Workspace access</p>
          <a href={d.team_directory_link} style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)", display: "flex", alignItems: "center", gap: 4 }}>
            Open Team Directory <ExternalLink size={12}/>
          </a>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 14 }}>
          <Stat label="Owner" value={d.owner ? 1 : 0}/>
          <Stat label="Active managers" value={d.active_managers.length}/>
          <Stat label="Active staff" value={d.active_staff.length}/>
          <Stat label="Active technicians" value={d.active_technicians.length}/>
        </div>
      </Card>

      {d.owner && (
        <Card>
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>Owner</p>
          <MemberRow name={d.owner.full_name} sub={d.owner.email} role="Owner"/>
        </Card>
      )}

      <MemberListCard title="Active managers" members={d.active_managers} role="Manager"/>
      <MemberListCard title="Active staff" members={d.active_staff} role="Staff"/>
      <MemberListCard title="Active technicians" members={d.active_technicians} role="Technician"/>

      <Card>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>Pending invitations</p>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>{d.pending_invitations_note}</p>
      </Card>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>{value}</p>
      <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{label}</p>
    </div>
  );
}

function MemberListCard({ title, members, role }: { title: string; members: { id: string; full_name: string }[]; role: string }) {
  if (members.length === 0) return null;
  return (
    <Card>
      <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>{title}</p>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {members.map(m => <MemberRow key={m.id} name={m.full_name} role={role}/>)}
      </div>
    </Card>
  );
}

function MemberRow({ name, sub, role }: { name: string; sub?: string; role: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 30, height: 30, borderRadius: "50%", background: "var(--accent-muted)", color: "var(--accent)",
          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700 }}>
          {name[0]?.toUpperCase()}
        </div>
        <div>
          <p style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>{name}</p>
          {sub && <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{sub}</p>}
        </div>
      </div>
      <Badge variant="muted" size="sm">{role}</Badge>
    </div>
  );
}
