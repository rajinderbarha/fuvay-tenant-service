import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Icon } from "../../../design-system/components/Icon";
import { ScheduleItemDTO } from "../../../services/schedule/types";

const STATUS_LABEL: Record<string, string> = {
  assigned: "Assigned", accepted: "Accepted", on_the_way: "On the way", reached_site: "Arrived",
  inspection_started: "Inspection", inspection_done: "Inspection done", quote_required: "Estimate",
  service_started: "In progress", work_done: "Work done",
};

function itemTone(theme: ReturnType<typeof useTheme>["theme"], item: ScheduleItemDTO) {
  if (item.type === "assigned_job") return { bg: theme.colors.statusWarningSurface, dot: theme.colors.statusWarning };
  if (item.type === "available_slot") return { bg: theme.colors.statusSuccessSurface, dot: theme.colors.statusSuccess };
  if (item.type === "approved_leave") return { bg: theme.colors.surfaceInteractive, dot: theme.colors.textTertiary };
  if (item.type === "pending_leave") return { bg: theme.colors.statusWarningSurface, dot: theme.colors.statusWarning };
  return { bg: theme.colors.surfaceInteractive, dot: theme.colors.textTertiary };
}

function itemTitle(item: ScheduleItemDTO): string {
  if (item.type === "assigned_job") return `${item.job_reference} · ${STATUS_LABEL[item.workflow_status ?? ""] ?? item.workflow_status}`;
  if (item.type === "available_slot") return "Available";
  if (item.type === "blocked_time") return "Blocked time";
  if (item.type === "approved_leave") return "Approved leave";
  return "Pending leave";
}

function itemSubtitle(item: ScheduleItemDTO): string | undefined {
  if (item.type === "available_slot") return `${item.duration_minutes ?? 60} min`;
  if (item.type === "blocked_time") return item.reason ?? undefined;
  if (item.type === "approved_leave" || item.type === "pending_leave") return item.reason_category;
  return undefined;
}

export interface ScheduleTimelineProps {
  items: ScheduleItemDTO[];
  onOpenJob: (jobId: string) => void;
  onRemoveBlock: (blockId: string) => void;
}

/** Connected vertical timeline (spec section 3). Safe locality/type/brand
 * are not fetched here -- job cards show only reference + status; full
 * detail (including any locality) lives behind the canonical Job Detail
 * screen this component navigates to. */
export function ScheduleTimeline({ items, onOpenJob, onRemoveBlock }: ScheduleTimelineProps) {
  const { theme } = useTheme();
  if (items.length === 0) {
    return <AppText variant="bodySmall" color="tertiary">Nothing scheduled.</AppText>;
  }
  return (
    <View>
      {items.map((item, i) => {
        const tone = itemTone(theme, item);
        const timeLabel = item.time_label ?? item.start_time ?? "";
        const content = (
          <View style={{ flex: 1, padding: theme.spacing.sm, borderRadius: theme.radiusUsage.card, backgroundColor: tone.bg }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <AppText variant="bodyStrong" numberOfLines={1} style={{ flex: 1 }}>{itemTitle(item)}</AppText>
              {item.type === "assigned_job" ? <Icon name="chevron-forward" size="compact" color={theme.colors.textTertiary} decorative /> : null}
              {item.type === "blocked_time" && item.source === "staff" ? (
                <Pressable onPress={() => onRemoveBlock(item.id!)} accessibilityRole="button" accessibilityLabel="Remove blocked time" hitSlop={8}>
                  <Icon name="close-circle-outline" size="compact" color={theme.colors.textTertiary} decorative />
                </Pressable>
              ) : null}
            </View>
            {itemSubtitle(item) ? <AppText variant="caption" color="tertiary">{itemSubtitle(item)}</AppText> : null}
          </View>
        );
        return (
          <View key={`${item.type}-${item.id ?? item.job_id ?? i}`} style={{ flexDirection: "row", gap: theme.spacing.sm, marginBottom: theme.spacing.sm }}>
            <View style={{ width: 64 }}>
              <AppText variant="caption" color="tertiary">{timeLabel}</AppText>
            </View>
            <View style={{ alignItems: "center" }}>
              <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: tone.dot }} />
              {i < items.length - 1 ? <View style={{ width: 1, flex: 1, backgroundColor: theme.colors.borderDefault, marginTop: 2 }} /> : null}
            </View>
            {item.type === "assigned_job" ? (
              <Pressable style={{ flex: 1 }} onPress={() => onOpenJob(item.job_id!)} accessibilityRole="button" accessibilityLabel={itemTitle(item)}>
                {content}
              </Pressable>
            ) : content}
          </View>
        );
      })}
    </View>
  );
}
