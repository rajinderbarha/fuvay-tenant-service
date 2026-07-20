import React, { useMemo } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useAppTheme } from "../../context/ThemeContext";
import type { JobProvenanceView } from "../../types/ux05";

/**
 * Small provenance chip shown on every job surface -- preserves source
 * booking ID + job model + pipeline identity per the UX-05 provenance
 * contract even though (per real evidence -- see types/ux05.ts header)
 * only one pipeline is live today. Keeping this visible/testable now means
 * a future second pipeline can't silently merge without this badge
 * changing too.
 *
 * UX-05 Round 5: converted to reactive theme colors (useAppTheme()) --
 * requires a ThemeProvider ancestor (see App.tsx / test files).
 */
export function PipelineBadge({ provenance, compact }: { provenance:JobProvenanceView; compact?:boolean }) {
  const { colors } = useAppTheme();
  const s = useMemo(() => makeStyles(colors), [colors]);
  return (
    <View style={s.wrap} testID="pipeline-badge">
      <Text style={s.text}>
        {compact ? "ServiceJob" : `ServiceJob · booking ${provenance.sourceBookingId.slice(0,8)}`}
      </Text>
    </View>
  );
}

function makeStyles(colors: ReturnType<typeof import("../../styles/theme").getColors>) {
  return StyleSheet.create({
    wrap: { backgroundColor:colors.accentLight, borderRadius:4,
            paddingHorizontal:6, paddingVertical:2, alignSelf:"flex-start" },
    text: { fontSize:11, fontWeight:"700", color:colors.accent },
  });
}
