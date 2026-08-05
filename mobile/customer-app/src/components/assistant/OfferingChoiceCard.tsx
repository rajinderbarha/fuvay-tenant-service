import React, { useState } from "react";
import { View, Pressable, ScrollView, useWindowDimensions } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";
import { Icon } from "../Icon";

export interface OfferingChoiceOption {
  id: string;
  slug: string;
  name: string;
}

export interface OfferingChoiceCardProps {
  options: OfferingChoiceOption[];
  /** Called with every issue the customer has ticked, once they tap
   * Continue -- always at least one. A single tap-to-select-and-submit
   * interaction (no multi-select, no Continue step) is still possible by
   * the caller submitting immediately whenever the array has length 1;
   * this component itself always requires an explicit Continue once
   * multiSelect is on, so a customer can add a second real problem (e.g.
   * "AC Not Cooling" AND "Water Leakage" on the same unit) before
   * submitting. */
  onSubmit: (options: OfferingChoiceOption[]) => void;
  disabled: boolean;
  /** Multiple real problems can genuinely apply to the same booking (spec:
   * "add multiple problem") -- when true, tapping toggles a checkmark
   * instead of submitting immediately, and a Continue button appears
   * once at least one option is selected. */
  multiSelect?: boolean;
}

/** Backend-first Booking Assistant: renders the real, zipcode-serviceable
 * issue list from `assistant-bootstrap` as tap options -- visually
 * identical to `QuestionCard` (same card, same option row treatment) so
 * the FIRST booking choice feels like part of the same continuous chat as
 * every question that follows it, never a separate form. Every option
 * here comes directly from the backend; DeepSeek is never involved in
 * choosing or labeling them. */
export function OfferingChoiceCard({ options, onSubmit, disabled, multiSelect }: OfferingChoiceCardProps) {
  const { theme } = useTheme();
  const { height: windowHeight } = useWindowDimensions();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Real bug fixed here: a long issue list (AC alone has 9 real choices)
  // rendered as a plain, non-scrolling View outside the transcript
  // FlatList -- past a handful of options it simply overflowed off the
  // bottom of the screen with no way to reach the rest or the Continue
  // button. Capping this list's own height and letting IT scroll (rather
  // than the whole screen) keeps the header/composer/Continue button
  // fixed and reachable regardless of how many issues the backend
  // returns.
  const maxListHeight = windowHeight * 0.38;

  function handlePress(opt: OfferingChoiceOption) {
    if (disabled) return;
    if (!multiSelect) {
      onSubmit([opt]);
      return;
    }
    setSelectedIds(prev => (prev.includes(opt.id) ? prev.filter(id => id !== opt.id) : [...prev, opt.id]));
  }

  function handleContinue() {
    const selected = options.filter(o => selectedIds.includes(o.id));
    if (selected.length === 0) return;
    onSubmit(selected);
  }

  return (
    <View
      style={{
        alignSelf: "stretch",
        backgroundColor: theme.colors.surfaceDefault,
        borderRadius: theme.radiusUsage.card,
        borderBottomLeftRadius: theme.radius.radiusSmall,
        borderWidth: 1, borderColor: theme.colors.borderSubtle,
        paddingHorizontal: theme.spacing.base, paddingVertical: theme.spacing.sm,
      }}
    >
      <ScrollView
        style={{ maxHeight: maxListHeight }}
        contentContainerStyle={{ gap: theme.spacing.xs }}
        nestedScrollEnabled
        showsVerticalScrollIndicator={options.length > 4}
        keyboardShouldPersistTaps="handled"
      >
        {options.map(opt => {
          const selected = selectedIds.includes(opt.id);
          return (
            <Pressable
              key={opt.id}
              disabled={disabled}
              onPress={() => handlePress(opt)}
              accessibilityRole={multiSelect ? "checkbox" : "button"}
              accessibilityState={multiSelect ? { checked: selected, disabled } : { disabled }}
              accessibilityLabel={opt.name}
              style={{
                flexDirection: "row", alignItems: "center", justifyContent: "space-between",
                minHeight: 56, paddingHorizontal: theme.spacing.base,
                borderRadius: theme.radiusUsage.input, borderWidth: 1,
                borderColor: selected ? theme.colors.brandPrimary : theme.colors.borderDefault,
                backgroundColor: selected ? theme.colors.brandPrimaryMuted : theme.colors.backgroundSecondary,
                opacity: disabled ? theme.opacity.disabled : 1,
              }}
            >
              <AppText variant="body">{opt.name}</AppText>
              {multiSelect ? (
                selected ? <Icon name="checkmark-circle" size="compact" color={theme.colors.brandPrimaryStrong} decorative /> : null
              ) : (
                <Icon name="chevron-forward" size="compact" color={theme.colors.brandPrimaryStrong} decorative />
              )}
            </Pressable>
          );
        })}
      </ScrollView>
      {multiSelect && selectedIds.length > 0 ? (
        <View style={{ marginTop: theme.spacing.sm }}>
          <AppButton
            label={selectedIds.length > 1 ? `Continue with ${selectedIds.length} issues` : "Continue"}
            onPress={handleContinue}
            disabled={disabled}
            fullWidth
          />
        </View>
      ) : null}
    </View>
  );
}
