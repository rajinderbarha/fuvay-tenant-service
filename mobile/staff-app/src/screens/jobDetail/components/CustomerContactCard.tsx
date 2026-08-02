import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { Card } from "../../../design-system/components/foundation/Layout";
import { CustomerAlias, RelayContactButton } from "../../../design-system/components/data-display/Privacy";
import { CustomerContactDTO } from "../../../services/jobDetail/types";

export interface CustomerContactCardProps {
  customer: CustomerContactDTO;
  onCallRelay: () => void;
  onMessageRelay: () => void;
}

/**
 * Never renders a raw phone/email -- both relay buttons are backend-gated
 * (spec section 9). Currently always disabled since no relay/telephony
 * engine exists yet; still surfaced so the affordance is discoverable.
 */
export function CustomerContactCard({ customer, onCallRelay, onMessageRelay }: CustomerContactCardProps) {
  const { theme } = useTheme();
  return (
    <Card>
      <CustomerAlias alias={customer.customer_alias} showAvatar />
      <View style={{ flexDirection: "row", gap: theme.spacing.lg, marginTop: theme.spacing.sm }}>
        <RelayContactButton label="Relay call" onPress={onCallRelay} disabled={!customer.call_relay_available} />
        <RelayContactButton label="Message" onPress={onMessageRelay} disabled={!customer.message_relay_available} />
      </View>
    </Card>
  );
}
