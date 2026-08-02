import React from "react";
import { View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { Icon, IconProps } from "../Icon";
import { PrimaryButton } from "../actions/Buttons";

export interface StateViewProps {
  icon: IconProps["name"];
  title: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
}

/** Shared full-block state presentation for empty/error/blocked screens.
 * Every blocked state must show what happened, why, and what to do next --
 * this shape enforces that (title=what, message=why, action=what next). */
function StateView({ icon, title, message, actionLabel, onAction }: StateViewProps) {
  const { theme } = useTheme();
  return (
    <View style={{ alignItems: "center", padding: theme.spacing.xxl, gap: theme.spacing.sm }}>
      <Icon name={icon} size="emptyState" color={theme.colors.textTertiary} decorative />
      <AppText variant="title" style={{ textAlign: "center" }}>{title}</AppText>
      {message ? <AppText variant="bodySmall" color="secondary" style={{ textAlign: "center" }}>{message}</AppText> : null}
      {actionLabel && onAction ? (
        <View style={{ marginTop: theme.spacing.sm }}>
          <PrimaryButton label={actionLabel} onPress={onAction} />
        </View>
      ) : null}
    </View>
  );
}

export function EmptyState(props: Omit<StateViewProps, "icon"> & { icon?: IconProps["name"] }) {
  return <StateView icon={props.icon ?? "file-tray-outline"} {...props} />;
}

export function ErrorState(props: Omit<StateViewProps, "icon"> & { icon?: IconProps["name"] }) {
  return <StateView icon={props.icon ?? "cloud-offline-outline"} {...props} />;
}

export function RetryState({ onRetry, ...rest }: Omit<StateViewProps, "icon" | "actionLabel" | "onAction"> & { onRetry: () => void; icon?: IconProps["name"] }) {
  return <StateView icon={rest.icon ?? "refresh-outline"} actionLabel="Try again" onAction={onRetry} {...rest} />;
}

export function PermissionDeniedState(props: Omit<StateViewProps, "icon" | "title"> & { title?: string }) {
  return <StateView icon="lock-closed-outline" title={props.title ?? "You don't have access"} {...props} />;
}

export function RestrictedAccountState(props: Omit<StateViewProps, "icon" | "title"> & { title?: string }) {
  return <StateView icon="alert-circle-outline" title={props.title ?? "Account restricted"} {...props} />;
}

/** PartialDataNotice -- inline (not full-screen) notice that one section of
 * a composed screen failed to load while the rest rendered fine. A single
 * failed read-only projection must never blank the whole screen. */
export function PartialDataNotice({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs, padding: theme.spacing.sm }}>
      <Icon name="information-circle-outline" size="compact" color={theme.colors.textTertiary} decorative />
      <AppText variant="caption" color="tertiary" style={{ flex: 1 }}>{message}</AppText>
      {onRetry ? (
        <AppText variant="caption" color="link" onPress={onRetry}>Retry</AppText>
      ) : null}
    </View>
  );
}
