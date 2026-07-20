import React from "react";
import { View, StyleSheet } from "react-native";
import { logger } from "../observability/logger";
import { AppText } from "../components/primitives/AppText";
import { AppButton } from "../components/primitives/AppButton";
import { lightTheme } from "../design-system/themes/light-theme";

interface Props {
  children: React.ReactNode;
  /** Optional section label — lets section-level boundaries reuse this component with narrower scope. */
  section?: string;
}

interface State {
  error: Error | null;
  errorReferenceId: string | null;
}

function newErrorReferenceId(): string {
  return `err_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Root-level (or section-level, via `section` prop) React error boundary.
 * Cannot use theme context (a render error inside ThemeProvider must still
 * be catchable), so it renders with static light-theme tokens rather than
 * `useAppTheme()`.
 */
export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null, errorReferenceId: null };

  static getDerivedStateFromError(error: Error): State {
    return { error, errorReferenceId: newErrorReferenceId() };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    logger.error("error_boundary.caught", error, {
      section: this.props.section ?? "root",
      errorReferenceId: this.state.errorReferenceId ?? undefined,
      componentStack: __DEV__ ? info.componentStack : undefined,
    });
  }

  private handleRetry = () => {
    this.setState({ error: null, errorReferenceId: null });
  };

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <View style={styles.container} accessibilityRole="alert">
        <AppText variant="headingSmall" color="textPrimary" style={styles.title}>
          Something went wrong
        </AppText>
        <AppText variant="bodyMedium" color="textSecondary" style={styles.body}>
          {this.props.section ? "This part of the app couldn't load. You can try again." : "We hit an unexpected problem. You can try again."}
        </AppText>
        {this.state.errorReferenceId ? (
          <AppText variant="caption" color="textTertiary" style={styles.reference}>
            Reference: {this.state.errorReferenceId}
          </AppText>
        ) : null}
        {__DEV__ ? (
          <AppText variant="caption" color="textDanger" style={styles.devDetail} numberOfLines={4}>
            {this.state.error.message}
          </AppText>
        ) : null}
        <AppButton label="Retry" onPress={this.handleRetry} variant="primary" size="medium" />
      </View>
    );
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: lightTheme.spacing[8],
    backgroundColor: lightTheme.colors.backgroundPrimary,
    gap: lightTheme.spacing[4],
  },
  title: { textAlign: "center" },
  body: { textAlign: "center" },
  reference: { textAlign: "center" },
  devDetail: { textAlign: "center", marginBottom: lightTheme.spacing[4] },
});
