import React from "react";
import { View, Text } from "react-native";

interface Props { children: React.ReactNode }
interface State { hasError: boolean }

/**
 * Outermost boundary (spec section 12) -- a crash below QueryClient/Theme
 * still renders something rather than a blank/white screen. Deliberately
 * has no dependency on theme/query context, since either could be the
 * thing that crashed.
 */
export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    // Intentionally no console.log of error detail here in production --
    // wire to a real crash-reporting sink in a later phase.
    if (__DEV__) {
      // eslint-disable-next-line no-console
      console.error("[ErrorBoundary]", error);
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#171310", padding: 24 }}>
          <Text style={{ color: "#F2994A", fontSize: 18, fontWeight: "600", marginBottom: 8 }}>Something went wrong</Text>
          <Text style={{ color: "#B8AFA6", textAlign: "center" }}>Please restart the app.</Text>
        </View>
      );
    }
    return this.props.children;
  }
}
