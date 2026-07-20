import React, { useEffect, useState } from "react";
import { View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { AppText } from "../primitives/AppText";
import { AppPressable } from "../primitives/AppPressable";
import { toastService, type ToastMessage, type ToastType } from "./toast-service";
import { useAppTheme } from "../../design-system/themes/use-app-theme";
import type { SemanticColors } from "../../design-system/themes/theme-types";

const BG_KEY_BY_TYPE: Record<ToastType, keyof SemanticColors> = {
  success: "statusSuccessBackground",
  info: "statusInfoBackground",
  warning: "statusWarningBackground",
  error: "statusDangerBackground",
};
const FG_KEY_BY_TYPE: Record<ToastType, keyof SemanticColors> = {
  success: "statusSuccessForeground",
  info: "statusInfoForeground",
  warning: "statusWarningForeground",
  error: "statusDangerForeground",
};

/** Mount once near the app root. Renders whatever `toastService` queues. */
export function ToastHost() {
  const { theme } = useAppTheme();
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => toastService.subscribe(setToasts), []);

  useEffect(() => {
    const timers = toasts.map((toast) => setTimeout(() => toastService.dismiss(toast.id), toast.timeoutMs));
    return () => timers.forEach(clearTimeout);
  }, [toasts]);

  if (toasts.length === 0) return null;

  return (
    <SafeAreaView pointerEvents="box-none" style={{ position: "absolute", top: 0, left: 0, right: 0 }}>
      <View style={{ gap: theme.spacing[2], paddingHorizontal: theme.spacing[6], paddingTop: theme.spacing[4] }}>
        {toasts.map((toast) => (
          <AppPressable
            key={toast.id}
            onPress={() => toastService.dismiss(toast.id)}
            accessibilityRole="alert"
            accessibilityLabel={toast.message}
            enforceMinTouchTarget={false}
            style={{
              backgroundColor: theme.colors[BG_KEY_BY_TYPE[toast.type]],
              borderRadius: theme.radii.md,
              padding: theme.spacing[5],
              ...theme.shadows.md,
            }}
          >
            <AppText variant="bodyMedium" style={{ color: theme.colors[FG_KEY_BY_TYPE[toast.type]] }}>
              {toast.message}
            </AppText>
          </AppPressable>
        ))}
      </View>
    </SafeAreaView>
  );
}
