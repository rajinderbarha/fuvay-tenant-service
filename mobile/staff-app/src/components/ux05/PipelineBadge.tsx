import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { theme } from "../../styles/theme";
import type { JobProvenanceView } from "../../types/ux05";

/**
 * Small provenance chip shown on every job surface -- preserves source
 * booking ID + job model + pipeline identity per the UX-05 provenance
 * contract even though (per real evidence -- see types/ux05.ts header)
 * only one pipeline is live today. Keeping this visible/testable now means
 * a future second pipeline can't silently merge without this badge
 * changing too.
 */
export function PipelineBadge({ provenance, compact }: { provenance:JobProvenanceView; compact?:boolean }) {
  return (
    <View style={s.wrap} testID="pipeline-badge">
      <Text style={s.text}>
        {compact ? "ServiceJob" : `ServiceJob · booking ${provenance.sourceBookingId.slice(0,8)}`}
      </Text>
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { backgroundColor:theme.colors.accentLight, borderRadius:theme.radius.sm,
          paddingHorizontal:6, paddingVertical:2, alignSelf:"flex-start" },
  text: { fontSize:theme.font.size.xs, fontWeight:"700", color:theme.colors.accent },
});
