import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppBadge } from "../AppBadge";
import { ReviewAddress } from "../../domain/bookingReview";

export interface ServiceAddressCardProps {
  address: ReviewAddress;
  onChange: () => void;
}

export function ServiceAddressCard({ address, onChange }: ServiceAddressCardProps) {
  const { theme } = useTheme();
  return (
    <AppCard>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <AppText variant="labelStrong" color="secondary">Service address</AppText>
        <AppText variant="labelStrong" color="link" onPress={onChange}>Change</AppText>
      </View>
      <View style={{ marginTop: theme.spacing.xxs, flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <View>
          {address.lines.map((line, i) => <AppText key={i} variant="body">{line}</AppText>)}
          <AppText variant="bodySmall" color="secondary">
            {[address.city, address.zipcode].filter(Boolean).join(", ")}
          </AppText>
        </View>
        <AppBadge label={address.serviceable ? "Serviceable" : "Unavailable"} tone={address.serviceable ? "success" : "danger"} />
      </View>
    </AppCard>
  );
}
