import React from "react";
import { View } from "react-native";
import { useTheme } from "../design-system/theme";
import { AppText } from "./AppText";
import { Icon, IconProps } from "./Icon";
import { AppButton } from "./AppButton";

export interface StateViewSecondaryAction {
  label: string;
  onPress: () => void;
}

export interface StateViewProps {
  icon: IconProps["name"];
  title: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
  /** Additional, lower-emphasis recovery actions rendered below the
   * primary one (e.g. "Choose another service" / "Get support" alongside
   * a primary "Try again") -- a blocked state may have more than one
   * genuinely useful next step, not just one. */
  secondaryActions?: StateViewSecondaryAction[];
  /** Renders the icon as a white glyph inside a filled circle of this
   * colour instead of the default bare tertiary-grey glyph. A brand
   * colour, so it is passed explicitly rather than themed -- only states
   * the design actually calls out this way should set it. */
  iconCircleColor?: string;
}

/** Shared full-block state presentation for empty/error screens. Every
 * blocked state must show what happened, why, and what to do next --
 * title=what, message=why, action=what next. */
function StateView({ icon, title, message, actionLabel, onAction, secondaryActions, iconCircleColor }: StateViewProps) {
  const { theme } = useTheme();
  return (
    <View style={{ alignItems: "center", padding: theme.spacing.xxl, gap: theme.spacing.sm }}>
      {iconCircleColor ? (
        <View
          style={{
            width: 88, height: 88, borderRadius: theme.radius.radiusFull,
            alignItems: "center", justifyContent: "center",
            backgroundColor: iconCircleColor,
            marginBottom: theme.spacing.xs,
            ...theme.shadow.sm,
          }}
        >
          <Icon name={icon} size="feature" color={theme.colors.brandOnPrimary} decorative />
        </View>
      ) : (
        <Icon name={icon} size="emptyState" color={theme.colors.textTertiary} decorative />
      )}
      <AppText variant="title" align="center">{title}</AppText>
      {message ? <AppText variant="bodySmall" color="secondary" align="center">{message}</AppText> : null}
      {actionLabel && onAction ? (
        <View style={{ marginTop: theme.spacing.sm }}>
          <AppButton label={actionLabel} onPress={onAction} />
        </View>
      ) : null}
      {secondaryActions?.map(a => (
        <AppButton key={a.label} label={a.label} tone="tertiary" onPress={a.onPress} />
      ))}
    </View>
  );
}

export function EmptyState(props: Omit<StateViewProps, "icon"> & { icon?: IconProps["name"] }) {
  return <StateView icon={props.icon ?? "file-tray-outline"} {...props} />;
}

export function ErrorState(props: Omit<StateViewProps, "icon"> & { icon?: IconProps["name"] }) {
  return <StateView icon={props.icon ?? "cloud-offline-outline"} {...props} />;
}
