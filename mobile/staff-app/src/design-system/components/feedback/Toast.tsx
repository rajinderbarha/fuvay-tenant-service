import React, { createContext, useCallback, useContext, useRef, useState } from "react";
import { Animated } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { SemanticTone } from "../../types";
import { zIndex } from "../../tokens/zIndex";

interface ToastItem {
  id: string;
  message: string;
  tone: SemanticTone;
}

interface ToastContextValue {
  show: (message: string, tone?: SemanticTone) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

/** Toast/Snackbar foundation -- app-root-mounted provider + `useToast()`
 * hook. Feature code calls `useToast().show(...)`; it does not build its
 * own transient-message UI. */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const { theme } = useTheme();
  const [toast, setToast] = useState<ToastItem | null>(null);
  const opacity = useRef(new Animated.Value(0)).current;
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback((message: string, tone: SemanticTone = "neutral") => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setToast({ id: String(Date.now()), message, tone });
    Animated.timing(opacity, { toValue: 1, duration: theme.motion.duration.fast, useNativeDriver: true }).start();
    timeoutRef.current = setTimeout(() => {
      Animated.timing(opacity, { toValue: 0, duration: theme.motion.duration.fast, useNativeDriver: true }).start(() => setToast(null));
    }, 3000);
  }, [opacity, theme.motion.duration.fast]);

  const toneColor = (tone: SemanticTone) => {
    switch (tone) {
      case "success": return theme.colors.statusSuccess;
      case "warning": return theme.colors.statusWarning;
      case "danger": return theme.colors.statusDanger;
      case "info": return theme.colors.statusInfo;
      default: return theme.colors.textInverse;
    }
  };

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      {toast ? (
        <Animated.View
          accessibilityLiveRegion="polite"
          accessibilityRole="alert"
          style={{
            position: "absolute", left: theme.spacing.base, right: theme.spacing.base, bottom: theme.spacing.xxl,
            backgroundColor: theme.mode === "dark" ? theme.colors.surfaceRaised : theme.colors.textPrimary,
            borderRadius: theme.radiusUsage.card, padding: theme.spacing.base, opacity, zIndex: zIndex.toast,
            borderLeftWidth: 4, borderLeftColor: toneColor(toast.tone),
          }}
        >
          <AppText variant="bodySmall" color="inverse">{toast.message}</AppText>
        </Animated.View>
      ) : null}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within a ToastProvider");
  return ctx;
}
