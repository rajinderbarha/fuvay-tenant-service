import React from "react";
import { View } from "react-native";
import { AppText } from "../AppText";

interface Props { children: React.ReactNode; sectionLabel: string }
interface State { hasError: boolean }

/**
 * A failure in one optional section must not blank the whole Home screen
 * (spec requirement) -- wrap each independently-rendered section
 * (campaigns, services, active booking) in one of these so a rendering
 * bug in a single section degrades to a small inline notice instead of
 * crashing the entire screen.
 */
export class HomeSectionErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    if (__DEV__) {
      // eslint-disable-next-line no-console
      console.error(`[HomeSectionErrorBoundary:${this.props.sectionLabel}]`, error);
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <View accessibilityRole="alert">
          <AppText variant="bodySmall" color="tertiary">{`Couldn't load ${this.props.sectionLabel} right now.`}</AppText>
        </View>
      );
    }
    return this.props.children;
  }
}
