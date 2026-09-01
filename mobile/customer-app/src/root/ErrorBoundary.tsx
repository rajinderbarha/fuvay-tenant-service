import React from "react";
import { View, Text, Pressable } from "react-native";
import { lightColors, radius, spacing, typography } from "../design-system/tokens";

interface Props { children: React.ReactNode }
interface State { hasError: boolean }

/**
 * Outermost boundary -- a crash below QueryClient/Theme still renders
 * something rather than a blank/white screen. Deliberately has no
 * dependency on theme/query context, since either could be the thing that
 * crashed. This fallback therefore carries the small, self-contained Fuvay
 * light palette it needs instead of trying to read a potentially-failed
 * provider.
 */
export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    if (__DEV__) {
      // eslint-disable-next-line no-console
      console.error("[ErrorBoundary]", error);
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: lightColors.backgroundPrimary, padding: spacing.xxl }}>
          <View style={{ width: 64, height: 64, borderRadius: radius.radiusFull, alignItems: "center", justifyContent: "center", backgroundColor: lightColors.brandPrimaryMuted, marginBottom: spacing.lg }}>
            <Text style={[typography.headingLarge, { color: lightColors.brandPrimaryStrong }]}>!</Text>
          </View>
          <Text style={[typography.headingLarge, { color: lightColors.textPrimary, marginBottom: spacing.sm }]}>Something went wrong</Text>
          <Text style={[typography.body, { color: lightColors.textSecondary, textAlign: "center", marginBottom: spacing.xl }]}>
            Fuvay could not open this screen. You can try it again safely.
          </Text>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Try again"
            onPress={() => this.setState({ hasError: false })}
            style={({ pressed }) => ({
              minWidth: 180,
              minHeight: 48,
              borderRadius: radius.radiusPill,
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: pressed ? lightColors.brandPrimaryPressed : lightColors.brandPrimary,
            })}
          >
            <Text style={[typography.button, { color: lightColors.brandOnPrimary }]}>Try again</Text>
          </Pressable>
        </View>
      );
    }
    return this.props.children;
  }
}
