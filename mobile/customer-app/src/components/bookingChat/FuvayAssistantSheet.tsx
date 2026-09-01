import React from "react";
import { Modal, Pressable, ScrollView, type StyleProp, View, type ViewStyle } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useTheme } from "../../design-system/theme";
import { AppLucideIcon } from "../AppLucideIcon";
import { AppText } from "../AppText";

export interface FuvayAssistantSheetProps {
  visible: boolean;
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: React.ReactNode;
  scroll?: boolean;
  contentStyle?: StyleProp<ViewStyle>;
  footer?: React.ReactNode;
}

/** Shared modal shell transcribed from the supplied assistant bottom sheets. */
export function FuvayAssistantSheet({
  visible,
  title,
  subtitle,
  onClose,
  children,
  scroll = false,
  contentStyle,
  footer,
}: FuvayAssistantSheetProps) {
  const { theme } = useTheme();
  const insets = useSafeAreaInsets();
  const f = theme.fuvay;
  const content = (
    <View style={[{ paddingHorizontal: 20, paddingBottom: 18, gap: 14 }, contentStyle]}>
      {children}
    </View>
  );

  return (
    <Modal visible={visible} transparent animationType="slide" statusBarTranslucent onRequestClose={onClose}>
      <View style={{ flex: 1, justifyContent: "flex-end" }}>
        <Pressable accessibilityRole="button" accessibilityLabel="Close sheet" onPress={onClose} style={{ position: "absolute", inset: 0, backgroundColor: theme.colors.mediaScrimStrong }} />
        <View style={{ maxHeight: "88%", borderTopLeftRadius: 30, borderTopRightRadius: 30, overflow: "hidden", backgroundColor: f.surfaces.panel, borderWidth: 1, borderColor: f.surfaces.edge, paddingBottom: Math.max(insets.bottom, 10) }}>
          <View style={{ alignSelf: "center", width: 40, height: 4, borderRadius: 4, marginTop: 13, marginBottom: 13, backgroundColor: f.surfaces.rule }} />
          <View style={{ paddingHorizontal: 20, paddingBottom: 14, flexDirection: "row", alignItems: "flex-start", gap: 12 }}>
            <View style={{ flex: 1, gap: 3 }}>
              <AppText variant="headingSmall" style={{ color: f.surfaces.text, fontSize: 18 }}>{title}</AppText>
              {subtitle ? <AppText variant="caption" style={{ color: f.surfaces.sub }}>{subtitle}</AppText> : null}
            </View>
            <Pressable accessibilityRole="button" accessibilityLabel="Close" onPress={onClose} style={({ pressed }) => ({ width: 34, height: 34, borderRadius: 17, alignItems: "center", justifyContent: "center", backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge, opacity: pressed ? theme.opacity.pressed : 1 })}>
              <AppLucideIcon name="close" size={16} color={f.surfaces.sub} />
            </Pressable>
          </View>
          {scroll ? <ScrollView showsVerticalScrollIndicator={false}>{content}</ScrollView> : content}
          {footer ? <View style={{ paddingHorizontal: 20, paddingTop: 10, borderTopWidth: 1, borderTopColor: f.surfaces.edge }}>{footer}</View> : null}
        </View>
      </View>
    </Modal>
  );
}
