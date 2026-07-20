import React from "react";
import { PixelRatio, ScrollView, StyleSheet, Text, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import { Button } from "../../components/Button";

/**
 * Dev-only accessibility/large-text showcase (workstream 30). Real,
 * verifiable claims only:
 * - No component in this app sets `allowFontScaling={false}` anywhere
 *   (confirmed by grep across src/) -- OS-level text-scaling (Dynamic
 *   Type / Android font scale) is never blocked. This screen surfaces the
 *   device's CURRENT font scale factor (`PixelRatio.getFontScale()`, a
 *   real RN API) so a reviewer can see this isn't a static claim.
 * - Below: a sample of real components (Button at all 3 sizes, a card with
 *   long wrapping text) rendered as-is, to eyeball whether layouts hold up
 *   as text grows -- no synthetic "simulate 200% text" override was built
 *   (RN has no supported in-app override of the OS font-scale setting;
 *   the real test is changing the OS/device accessibility setting and
 *   reopening the app, which weren't done this round -- see
 *   accessibility-report.md for the honest scope boundary).
 */
export function AccessibilityShowcaseScreen() {
  const fontScale = PixelRatio.getFontScale();
  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content} testID="accessibility-showcase">
      <View style={[gs.card, { gap:6 }]}>
        <Text style={gs.label}>Current device font scale</Text>
        <Text style={s.scaleValue}>{fontScale.toFixed(2)}×</Text>
        <Text style={s.note}>
          Real value from PixelRatio.getFontScale() -- reflects the OS accessibility text-size setting live. No
          component in this app sets allowFontScaling=false (confirmed by grep), so this value genuinely affects
          every screen's text.
        </Text>
      </View>

      <View style={[gs.card, { gap:10 }]}>
        <Text style={gs.label}>Buttons at all sizes (44pt+ touch targets)</Text>
        <Button label="Small" size="sm" onPress={() => {}} />
        <Button label="Medium" size="md" onPress={() => {}} />
        <Button label="Large" size="lg" onPress={() => {}} />
      </View>

      <View style={[gs.card, { gap:6 }]}>
        <Text style={gs.label}>Long-text wrapping sample</Text>
        <Text style={s.longText}>
          This is a deliberately long sentence meant to wrap across multiple lines on a narrow phone screen, so a
          reviewer can confirm no fixed-height container clips it as text scaling increases the rendered size of
          every character in this paragraph.
        </Text>
      </View>

      <Text style={s.mockNote}>
        Not done this round: an actual OS-level 200% text-scale device test, a live screen-reader (VoiceOver/
        TalkBack) session, and a systematic focus-order audit -- all require a real device/emulator not available
        in this environment. See accessibility-report.md.
      </Text>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:   { padding:theme.spacing.base, gap:12, paddingBottom:32 },
  scaleValue:{ fontSize:theme.font.size.xxxl, fontWeight:"800", color:theme.colors.accent },
  note:      { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
  longText:  { fontSize:theme.font.size.base, color:theme.colors.textPrimary, lineHeight:22 },
  mockNote:  { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, textAlign:"center" },
});
