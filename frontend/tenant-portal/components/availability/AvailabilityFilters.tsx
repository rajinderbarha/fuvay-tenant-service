"use client";
import { Card } from "../shared/ui";
import EnterpriseFilterBar from "../enterprise/EnterpriseFilterBar";

export function AvailabilityFilters({
  search, onSearch, roleFilter, onRole, roles,
  availFilter, onAvail, capabilityFilter, onCapability, capabilities,
  timezone, onReset,
}: {
  search: string; onSearch: (v: string) => void;
  roleFilter: string; onRole: (v: string) => void; roles: string[];
  availFilter: "" | "available" | "unavailable"; onAvail: (v: "" | "available" | "unavailable") => void;
  capabilityFilter: string; onCapability: (v: string) => void;
  capabilities: { id: string; name: string }[];
  timezone: string | null; onReset: () => void;
}) {
  return (
    <Card style={{ marginBottom: 16 }}>
      <EnterpriseFilterBar
        searchValue={search}
        onSearch={onSearch}
        filters={[
          { key: "role", label: "Role", type: "select", options: roles.map(value => ({ value, label: value })) },
          { key: "availability", label: "Availability", type: "select", options: [{ value: "available", label: "Available" }, { value: "unavailable", label: "Unavailable" }] },
          { key: "capability", label: "Capability", type: "select", options: capabilities.map(item => ({ value: item.id, label: item.name })) },
        ]}
        values={{ role: roleFilter, availability: availFilter, capability: capabilityFilter }}
        onChange={(key, value) => {
          if (key === "role") onRole(value);
          else if (key === "availability") onAvail(value as "" | "available" | "unavailable");
          else if (key === "capability") onCapability(value);
        }}
        onReset={onReset}
        rightSlot={<span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Timezone: {timezone ?? "—"}</span>}
      />
    </Card>
  );
}
