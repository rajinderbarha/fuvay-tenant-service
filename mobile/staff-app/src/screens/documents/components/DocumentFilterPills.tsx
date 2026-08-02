import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { DocumentFilter, DocumentsReadinessDTO } from "../../../services/documents/types";

const FILTERS: { key: DocumentFilter; label: string }[] = [
  { key: "all", label: "All" }, { key: "action_needed", label: "Action needed" },
  { key: "pending", label: "Pending" }, { key: "verified", label: "Verified" },
];

export function DocumentFilterPills({ readiness, totalCount, value, onChange }: {
  readiness: DocumentsReadinessDTO; totalCount: number; value: DocumentFilter; onChange: (f: DocumentFilter) => void;
}) {
  const { theme } = useTheme();
  const counts: Record<DocumentFilter, number> = {
    all: totalCount, action_needed: readiness.action_needed, pending: readiness.pending, verified: readiness.verified,
  };
  return (
    <View style={{ flexDirection: "row", gap: theme.spacing.sm, flexWrap: "wrap" }}>
      {FILTERS.map(f => {
        const selected = value === f.key;
        return (
          <View
            key={f.key}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            accessibilityLabel={`${f.label}, ${counts[f.key]}`}
            onTouchEnd={() => onChange(f.key)}
            style={{
              flexDirection: "row", alignItems: "center", gap: 6,
              paddingHorizontal: theme.spacing.base, paddingVertical: theme.spacing.sm,
              borderRadius: theme.radiusUsage.statusPill,
              backgroundColor: selected ? theme.colors.brandPrimary : theme.colors.surfaceInteractive,
            }}
          >
            <AppText variant="labelStrong" style={{ color: selected ? theme.colors.textInverse : theme.colors.textPrimary }}>{f.label}</AppText>
            <AppText variant="caption" style={{ color: selected ? theme.colors.textInverse : theme.colors.textTertiary }}>{counts[f.key]}</AppText>
          </View>
        );
      })}
    </View>
  );
}
