import React, { useState } from "react";
import { Modal, View } from "react-native";
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
 */
export function LocationPickerModal({ visible, currentZipcode, onClose, onConfirm }: LocationPickerModalProps) {
  const { theme } = useTheme();
  const [value, setValue] = useState(currentZipcode ?? "");
  const [error, setError] = useState<string | undefined>();

  React.useEffect(() => {
    if (visible) {
      setValue(currentZipcode ?? "");
      setError(undefined);
    }
  }, [visible, currentZipcode]);

  function handleConfirm() {
    if (!ZIPCODE_PATTERN.test(value)) {
      setError("Enter a valid 6-digit ZIP code");
      return;
    }
    onConfirm(value);
    onClose();
  }

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={{ flex: 1, justifyContent: "flex-end", backgroundColor: theme.colors.backgroundOverlay }}>
        <View
          style={{
            backgroundColor: theme.colors.surfaceDefault, borderTopLeftRadius: theme.radiusUsage.card, borderTopRightRadius: theme.radiusUsage.card,
            padding: theme.spacing.base,
          }}
        >
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: theme.spacing.base }}>
            <AppText variant="headingSmall" accessibilityRole="header">Change location</AppText>
            <AppIconButton name="close" accessibilityLabel="Close" onPress={onClose} />
          </View>
          <AppInput
            label="ZIP code"
            accessibilityLabel="ZIP code"
            value={value}
            onChangeText={t => { setValue(t.replace(/\D/g, "").slice(0, 6)); setError(undefined); }}
            keyboardType="number-pad"
            maxLength={6}
            error={error}
            placeholder="141001"
          />
          <View style={{ marginTop: theme.spacing.base }}>
            <AppButton label="Confirm location" onPress={handleConfirm} fullWidth />
          </View>
        </View>
      </View>
    </Modal>
  );
}
