import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppInput } from "../AppInput";
import { Icon } from "../Icon";
import { AddressFormState, AddressFormErrors, validatePinCode } from "../../domain/addressForm";

export interface AddressFormFieldsProps {
  form: AddressFormState;
  errors: AddressFormErrors;
  touched: Partial<Record<keyof AddressFormErrors, boolean>>;
  onChange: <K extends keyof AddressFormState>(key: K, value: AddressFormState[K]) => void;
  onBlur: (key: keyof AddressFormErrors) => void;
}

export function AddressFormFields({ form, errors, touched, onChange, onBlur }: AddressFormFieldsProps) {
  const { theme } = useTheme();
  const pinValid = validatePinCode(form.pinCode).valid;

  return (
    <View style={{ gap: theme.spacing.sm }}>
      <AppInput
        label="Full name"
        value={form.fullName}
        onChangeText={t => onChange("fullName", t)}
        onBlur={() => onBlur("fullName")}
        error={touched.fullName ? errors.fullName ?? undefined : undefined}
        accessibilityLabel="Full name"
        autoComplete="name"
        textContentType="name"
        returnKeyType="next"
        maxLength={100}
      />
      <AppInput
        label="House / Flat / Floor"
        value={form.addressLine1}
        onChangeText={t => onChange("addressLine1", t)}
        onBlur={() => onBlur("addressLine1")}
        error={touched.addressLine1 ? errors.addressLine1 ?? undefined : undefined}
        accessibilityLabel="House, flat, or floor"
        returnKeyType="next"
        maxLength={300}
      />
      <AppInput
        label="Street / Area"
        value={form.addressLine2}
        onChangeText={t => onChange("addressLine2", t)}
        accessibilityLabel="Street or area"
        returnKeyType="next"
        maxLength={300}
      />
      <AppInput
        label="Landmark (optional)"
        placeholder="Add a nearby landmark"
        value={form.landmark}
        onChangeText={t => onChange("landmark", t)}
        accessibilityLabel="Landmark, optional"
        returnKeyType="next"
        maxLength={200}
      />
      <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
        <View style={{ flex: 1 }}>
          <AppInput
            label="City"
            value={form.city}
            onChangeText={t => onChange("city", t)}
            onBlur={() => onBlur("city")}
            error={touched.city ? errors.city ?? undefined : undefined}
            accessibilityLabel="City"
            returnKeyType="next"
            maxLength={100}
          />
        </View>
        <View style={{ flex: 1 }}>
          <AppInput
            label="State"
            value={form.state}
            onChangeText={t => onChange("state", t)}
            onBlur={() => onBlur("state")}
            error={touched.state ? errors.state ?? undefined : undefined}
            accessibilityLabel="State"
            returnKeyType="next"
            maxLength={100}
          />
        </View>
      </View>
      <View>
        <AppText variant="label" color="secondary" style={{ marginBottom: theme.spacing.xxs }}>PIN code</AppText>
        <View style={{ flexDirection: "row", gap: theme.spacing.xs, alignItems: "flex-start" }}>
          <View style={{ flex: 1 }}>
            <AppInput
              value={form.pinCode}
              onChangeText={t => onChange("pinCode", t.replace(/[^0-9]/g, "").slice(0, 6))}
              onBlur={() => onBlur("pinCode")}
              error={touched.pinCode ? errors.pinCode ?? undefined : undefined}
              accessibilityLabel="PIN code"
              keyboardType="number-pad"
              returnKeyType="done"
              maxLength={6}
            />
          </View>
          {pinValid ? (
            <View style={{
              flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs,
              minHeight: theme.touchTargets.minimum, paddingHorizontal: theme.spacing.sm,
              borderRadius: theme.radiusUsage.statusPill, backgroundColor: theme.colors.statusSuccessSurface,
            }}>
              <Icon name="checkmark-circle" size="compact" color={theme.colors.statusSuccess} decorative />
              <AppText variant="caption" style={{ color: theme.colors.statusSuccess }}>6-digit valid</AppText>
            </View>
          ) : null}
        </View>
      </View>
    </View>
  );
}
