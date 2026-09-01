"use client";
import { Card } from "../shared/ui";
import EnterpriseFilterBar from "../enterprise/EnterpriseFilterBar";

export function CustomerFilters({
  search, onSearch, activity, onActivity, repeatStatus, onRepeatStatus,
}: {
  search: string; onSearch: (v: string) => void;
  activity: "" | "active" | "inactive"; onActivity: (v: "" | "active" | "inactive") => void;
  repeatStatus: "" | "repeat" | "one_time" | "none"; onRepeatStatus: (v: "" | "repeat" | "one_time" | "none") => void;
}) {
  return (
    <Card style={{ marginBottom: 16 }}>
      <EnterpriseFilterBar
        searchValue={search}
        onSearch={onSearch}
        filters={[
          { key: "activity", label: "Activity", type: "select", options: [{ value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }] },
          { key: "repeatStatus", label: "Customer type", type: "select", options: [{ value: "repeat", label: "Repeat" }, { value: "one_time", label: "One-time" }, { value: "none", label: "No completed jobs yet" }] },
        ]}
        values={{ activity, repeatStatus }}
        onChange={(key, value) => key === "activity" ? onActivity(value as typeof activity) : onRepeatStatus(value as typeof repeatStatus)}
        onReset={() => { onSearch(""); onActivity(""); onRepeatStatus(""); }}
      />
    </Card>
  );
}
