import React, { useState, useEffect } from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { BottomSheet } from "../../../design-system/components/overlays/BottomSheet";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Switch } from "../../../design-system/components/forms/Switch";
import { PrimaryButton, TertiaryButton } from "../../../design-system/components/actions/Buttons";
import { Inline } from "../../../design-system/components/foundation/Layout";
import { StatusBadge } from "../../../design-system/components/data-display/Badges";
import { WORKFLOW_STATUS_MAP } from "../../../design-system/workflowStatus";

export interface JobsFilters {
  workflowStatus?: string;
  actionRequired?: boolean;
}

export interface JobsFilterSheetProps {
  visible: boolean;
  initialFilters: JobsFilters;
  onApply: (filters: JobsFilters) => void;
  onClose: () => void;
}

/**
 * Mobile bottom-sheet filter (Phase I spec section 6) -- backed only by
 * real, backend-supported params (workflow_status, action_required).
 * Service-group/master-service/job-type dropdowns are deliberately not
 * included: no catalog-list endpoint was audited/built for this phase, and
 * inventing option lists client-side would violate "values come from real
 * supported backend enums/catalog data" (disclosed in the phase report).
 */
export function JobsFilterSheet({ visible, initialFilters, onApply, onClose }: JobsFilterSheetProps) {
  const { theme } = useTheme();
  const [workflowStatus, setWorkflowStatus] = useState<string | undefined>(initialFilters.workflowStatus);
  const [actionRequired, setActionRequired] = useState<boolean>(!!initialFilters.actionRequired);

  useEffect(() => {
    if (visible) {
      setWorkflowStatus(initialFilters.workflowStatus);
      setActionRequired(!!initialFilters.actionRequired);
    }
  }, [visible, initialFilters]);

  const statusCodes = Object.keys(WORKFLOW_STATUS_MAP);

  return (
    <BottomSheet visible={visible} onClose={onClose}>
      <AppText variant="title" style={{ marginBottom: theme.spacing.sm }}>Filters</AppText>

      <AppText variant="label" color="tertiary" style={{ marginBottom: theme.spacing.xs }}>Workflow stage</AppText>
      <Inline gap="sm" wrap style={{ marginBottom: theme.spacing.base }}>
        {statusCodes.map(code => (
          <Pressable key={code} onPress={() => setWorkflowStatus(workflowStatus === code ? undefined : code)} accessibilityRole="button" accessibilityState={{ selected: workflowStatus === code }}>
            <View style={{ opacity: workflowStatus && workflowStatus !== code ? 0.4 : 1 }}>
              <StatusBadge statusCode={code} />
            </View>
          </Pressable>
        ))}
      </Inline>

      <Switch label="Action required only" value={actionRequired} onChange={setActionRequired} />

      <Inline gap="sm" style={{ marginTop: theme.spacing.lg }}>
        <TertiaryButton label="Clear all" onPress={() => { setWorkflowStatus(undefined); setActionRequired(false); }} />
        <View style={{ flex: 1 }}>
          <PrimaryButton label="Apply" onPress={() => onApply({ workflowStatus, actionRequired })} fullWidth />
        </View>
      </Inline>
    </BottomSheet>
  );
}
