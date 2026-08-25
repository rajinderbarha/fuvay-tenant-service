import React from "react";
import { View, Text, Pressable } from "react-native";

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
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#F5F8FD", padding: 28 }}>
          <View style={{ width: 64, height: 64, borderRadius: 32, alignItems: "center", justifyContent: "center", backgroundColor: "#EEF3FF", marginBottom: 20 }}>
            <Text style={{ color: "#3868E0", fontSize: 28, fontWeight: "800" }}>!</Text>
          </View>
          <Text style={{ color: "#0F172A", fontSize: 22, fontWeight: "700", marginBottom: 8 }}>Something went wrong</Text>
          <Text style={{ color: "#475569", fontSize: 15, lineHeight: 22, textAlign: "center", marginBottom: 24 }}>
            Fuvay could not open this screen. You can try it again safely.
          </Text>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Try again"
            onPress={() => this.setState({ hasError: false })}
            style={({ pressed }) => ({
              minWidth: 180,
              minHeight: 48,
              borderRadius: 12,
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: pressed ? "#2F5BD1" : "#3868E0",
            })}
          >
            <Text style={{ color: "#FFFFFF", fontSize: 16, fontWeight: "700" }}>Try again</Text>
          </Pressable>
        </View>
      );
    }
    return this.props.children;
  }
}
