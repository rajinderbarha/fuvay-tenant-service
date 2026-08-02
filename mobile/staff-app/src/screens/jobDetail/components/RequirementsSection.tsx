import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Icon } from "../../../design-system/components/Icon";
import { ListRow, SectionHeader } from "../../../design-system/components/data-display/InfoRow";
import { RequirementsDTO } from "../../../services/jobDetail/types";

interface Row {
  key: string;
  title: string;
  subtitle: string;
  done: boolean | null;
}

function toRows(requirements: RequirementsDTO): Row[] {
  const rows: Row[] = [];
  const { checklist, photos, estimate, parts, completion_proof, payment_confirmation } = requirements;

  rows.push({
    key: "checklist",
    title: "Inspection checklist",
    subtitle: checklist.required ? `${checklist.completed_items} of ${checklist.total_items} completed` : "Not required",
    done: checklist.required ? checklist.completed_items >= checklist.total_items && checklist.total_items > 0 : null,
  });

  if (photos.required !== false) {
    rows.push({ key: "photos", title: "Photos", subtitle: `${photos.uploaded_count} uploaded`, done: photos.uploaded_count > 0 ? true : null });
  }

  if (estimate.required) {
    rows.push({
      key: "estimate", title: "Estimate",
      subtitle: estimate.state ? estimate.state.replace(/_/g, " ") : "Not created",
      done: estimate.state === "approved",
    });
  }

  if (parts.requested) {
    rows.push({ key: "parts", title: "Parts request", subtitle: parts.approval_state ? parts.approval_state.replace(/_/g, " ") : "Pending", done: parts.approval_state === "approved" });
  }

  if (completion_proof.required) {
    rows.push({ key: "completion_proof", title: "Completion proof", subtitle: completion_proof.state.replace(/_/g, " "), done: completion_proof.state === "submitted" });
  }

  if (payment_confirmation.required) {
    rows.push({ key: "payment_confirmation", title: "Payment confirmation", subtitle: payment_confirmation.state ? payment_confirmation.state.replace(/_/g, " ") : "Pending", done: payment_confirmation.state === "confirmed" });
  }

  return rows;
}

/** Every row is a direct projection of backend requirement state -- no
 * readiness value is inferred beyond the explicit fields provided. */
export function RequirementsSection({ requirements }: { requirements: RequirementsDTO }) {
  const { theme } = useTheme();
  const rows = toRows(requirements);
  return (
    <View>
      <SectionHeader title="Requirements" />
      {rows.map(row => (
        <ListRow
          key={row.key}
          title={row.title}
          subtitle={row.subtitle}
          trailing={
            row.done === null ? (
              <Icon name="time-outline" size="compact" color={theme.colors.textTertiary} decorative />
            ) : row.done ? (
              <Icon name="checkmark-circle" size="compact" color={theme.colors.statusSuccess} decorative />
            ) : (
              <Icon name="ellipse-outline" size="compact" color={theme.colors.textTertiary} decorative />
            )
          }
        />
      ))}
    </View>
  );
}
