import React from "react";
import { View, Text } from "react-native";

interface Props { children: React.ReactNode }
interface State { hasError: boolean }

/**
 * Outermost boundary -- a crash below QueryClient/Theme still renders
 * something rather than a blank/white screen. Deliberately has no
 * dependency on theme/query context, since either could be the thing that
 * crashed. Colors are intentionally literal here for that reason.
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
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#F7F6F3", padding: 24 }}>
          <Text style={{ color: "#D9642B", fontSize: 18, fontWeight: "600", marginBottom: 8 }}>Something went wrong</Text>
          <Text style={{ color: "#5C5348", textAlign: "center" }}>Please restart the app.</Text>
        </View>
      );
    }
    return this.props.children;
  }
}
