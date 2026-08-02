import React from "react";
import { View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { Icon } from "../Icon";
import { Checkbox } from "../forms/Checkbox";

export interface ChecklistItemModel {
  itemId: string;
  label: string;
  required: boolean;
  completed: boolean;
  evidenceRequired?: boolean;
  evidenceProvided?: boolean;
}

export interface ChecklistItemProps {
  item: ChecklistItemModel;
  onToggle?: (itemId: string, completed: boolean) => void;
  disabled?: boolean;
}

/** Presentation only -- completion validity (required items + evidence)
 * is enforced server-side; this component never marks a checklist
 * "complete" on its own authority. */
export function ChecklistItem({ item, onToggle, disabled }: ChecklistItemProps) {
  const { theme } = useTheme();
  return (
    <View style={{ paddingVertical: theme.spacing.xs }}>
      <Checkbox
        label={item.label + (item.required ? " *" : "")}
        checked={item.completed}
        onChange={checked => onToggle?.(item.itemId, checked)}
        disabled={disabled || !onToggle}
      />
      {item.evidenceRequired ? (
        <View style={{ flexDirection: "row", alignItems: "center", gap: 4, marginLeft: 32 }}>
          <Icon name={item.evidenceProvided ? "checkmark-circle" : "camera-outline"} size="compact"
            color={item.evidenceProvided ? theme.colors.statusSuccess : theme.colors.textTertiary} decorative />
          <AppText variant="caption" color={item.evidenceProvided ? "success" : "tertiary"}>
            {item.evidenceProvided ? "Evidence attached" : "Evidence required"}
          </AppText>
        </View>
      ) : null}
    </View>
  );
}
