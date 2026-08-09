import React, { useRef, useState } from "react";
import {
  Keyboard, KeyboardAvoidingView, Modal, Platform, Pressable, TextInput, View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useTheme } from "../../design-system/theme";
import { AppText, AppButton, AppInput, AppIconButton } from "../index";

export interface LocationPickerModalProps {
  visible: boolean;
  currentZipcode: string | null;
  onClose: () => void;
  /** Caller re-runs the Home aggregation query with the new ZIP -- this
   * component owns no serviceability/query logic itself, only input. */
  onConfirm: (zipcode: string) => void;
}

const ZIPCODE_PATTERN = /^\d{6}$/;

/**
 * Minimal ZIP-entry picker (no map/geolocation this task). Confirming
 * re-runs GET /v1/customer/home?zipcode=<new> (see HomeScreen), which is
 * how serviceability is genuinely re-checked and services refreshed --
 * this modal has no serviceability logic of its own, it only collects
 * the new value.
 *
 * It is a BOTTOM sheet with a text field, which is the arrangement most likely to
 * end up underneath a keyboard, so two things are deliberate here:
 *
 *  - The sheet lifts above the keyboard (KeyboardAvoidingView). Without it the number
 *    pad covered the sheet outright: the field could not be seen while typing into it,
 *    and the Confirm and Close controls were behind the keyboard, which reads as a
 *    frozen screen with no way out.
 *  - The backdrop dismisses. A full-screen overlay with no escape other than one
 *    button that the keyboard can cover is a trap; tapping outside a sheet is also
 *    what people already expect.
 */
export function LocationPickerModal({ visible, currentZipcode, onClose, onConfirm }: LocationPickerModalProps) {
  const { theme } = useTheme();
  const insets = useSafeAreaInsets();
  const [value, setValue] = useState(currentZipcode ?? "");
  const inputRef = useRef<TextInput>(null);
  const [error, setError] = useState<string | undefined>();

  React.useEffect(() => {
    if (visible) {
      setValue(currentZipcode ?? "");
      setError(undefined);
    }
  }, [visible, currentZipcode]);

  /**
   * Closes the sheet with the number pad put away.
   *
   * Real bug this fixes: the customer changed their ZIP and was left with a number
   * pad covering the bottom half of Home, with nothing focused to dismiss it by
   * tapping.
   *
   * All three steps are load-bearing, which is why this is not simply
   * `Keyboard.dismiss()`:
   *
   *  1. Blur the field ITSELF. It lives inside a Modal, which hosts its own view
   *     hierarchy; the input stays first responder there, and `Keyboard.dismiss()`
   *     alone does not always take it away.
   *  2. Dismiss the keyboard, for the case where focus sits somewhere this ref does
   *     not cover.
   *  3. Close on the NEXT frame rather than this one. Unmounting the Modal in the
   *     same frame as the blur tears down the hierarchy before the blur is
   *     processed, and the keyboard is left behind with nothing to dismiss it.
   *
   * Every exit routes through here -- confirm, the close button, the backdrop, and
   * the hardware/gesture back -- because it only takes one path that does not to
   * reproduce it.
   */
  function dismissAndClose() {
    inputRef.current?.blur();
    Keyboard.dismiss();
    requestAnimationFrame(() => onClose());
  }

  function handleConfirm() {
    if (!ZIPCODE_PATTERN.test(value)) {
      setError("Enter a valid 6-digit ZIP code");
      return;
    }
    onConfirm(value);
    dismissAndClose();
  }

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={dismissAndClose}>
      <KeyboardAvoidingView
        // "padding" on iOS lifts the sheet by the keyboard's height; on Android the
        // window itself is already resized, and adding padding on top of that leaves
        // a gap under the sheet.
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={{ flex: 1, justifyContent: "flex-end" }}
      >
        <Pressable
          onPress={dismissAndClose}
          accessibilityRole="button"
          accessibilityLabel="Close change location"
          // Fills everything above the sheet. Flex, not absolute, so the sheet keeps
          // its own space when the keyboard lifts it.
          style={{ flex: 1, backgroundColor: theme.colors.backgroundOverlay }}
        />
        <View
          style={{
            backgroundColor: theme.colors.surfaceDefault,
            borderTopLeftRadius: theme.radiusUsage.card,
            borderTopRightRadius: theme.radiusUsage.card,
            padding: theme.spacing.base,
            // Clear of the home indicator when the keyboard is down; the keyboard
            // supplies its own clearance when it is up.
            paddingBottom: theme.spacing.base + insets.bottom,
          }}
        >
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: theme.spacing.base }}>
            <AppText variant="headingSmall" accessibilityRole="header">Change location</AppText>
            <AppIconButton name="close" accessibilityLabel="Close" onPress={dismissAndClose} />
          </View>
          <AppInput
            ref={inputRef}
            label="ZIP code"
            accessibilityLabel="ZIP code"
            value={value}
            onChangeText={t => { setValue(t.replace(/\D/g, "").slice(0, 6)); setError(undefined); }}
            keyboardType="number-pad"
            maxLength={6}
            error={error}
            placeholder="141001"
            returnKeyType="done"
            onSubmitEditing={handleConfirm}
          />
          <View style={{ marginTop: theme.spacing.base }}>
            <AppButton label="Confirm location" onPress={handleConfirm} fullWidth />
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}
