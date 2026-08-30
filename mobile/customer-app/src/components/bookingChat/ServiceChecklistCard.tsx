import React, { useEffect, useRef, useState } from "react";
import { View, Animated, Easing, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useReducedMotion } from "../../design-system/theme";
import { useBotColors } from "./botTheme";
import { ServiceChecklist } from "../../domain/serviceChecklist";
import { BotText } from "./BotText";
import { BOT_GUTTER } from "./BotPrimitives";

export interface ServiceChecklistCardProps {
  checklist: ServiceChecklist;
  onContinue: () => void;
}

/** How long between each point appearing. Slow enough to read one line, fast
 * enough that twelve of them do not feel like waiting. */
const REVEAL_STEP_MS = 260;
/** Beyond this, the list is collapsed behind a "show all" so the card never
 * becomes a wall the customer scrolls past without reading. */
const COLLAPSED_LIMIT = 6;

/**
 * "Here's exactly what your technician will do" -- shown before Confirm.
 *
 * This is the strongest trust signal in the flow: it turns an abstract price
 * into a concrete list of work. Every line is REAL authored catalog content the
 * technician is held to on the job (server-side narrowed to the assigned
 * provider's own selected points, customer-visible only). The card renders
 * nothing at all when the list is empty -- an unauthored service must not be
 * dressed up with generic reassurance.
 *
 * Points reveal one at a time rather than appearing as a block: a list that
 * builds itself is read, a list that is simply there is skipped. Respects
 * reduced-motion by showing everything immediately.
 */
export function ServiceChecklistCard({ checklist, onContinue }: ServiceChecklistCardProps) {
  const BOT = useBotColors();
  const reduced = useReducedMotion();
  const [expanded, setExpanded] = useState(false);

  const flat = checklist.sections.flatMap(section =>
    section.points.map(point => ({ ...point, sectionTitle: section.title })),
  );
  const [revealed, setRevealed] = useState(reduced ? flat.length : 0);

  useEffect(() => {
    if (reduced) {
      setRevealed(flat.length);
      return;
    }
    if (revealed >= flat.length) return;
    const timer = setTimeout(() => setRevealed(n => n + 1), REVEAL_STEP_MS);
    return () => clearTimeout(timer);
  }, [revealed, flat.length, reduced]);

  // Nothing authored -> say nothing. See component doc.
  if (checklist.totalPoints === 0 || flat.length === 0) return null;

  const revealDone = revealed >= flat.length;
  const limit = expanded || !revealDone ? flat.length : COLLAPSED_LIMIT;
  const shown = flat.slice(0, Math.min(revealed, limit));
  const hidden = flat.length - Math.min(flat.length, limit);

  return (
    <View
      style={{
        marginLeft: BOT_GUTTER, borderRadius: 20, padding: 16,
        backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.borderSubtle,
      }}
    >
      <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
        <Ionicons name="clipboard-outline" size={18} color={BOT.brand} />
        <BotText style={{ flex: 1, fontSize: 16, fontWeight: "700", color: BOT.textPrimary }}>
          What your technician will do
        </BotText>
      </View>

      <BotText style={{ fontSize: 13, color: BOT.textTertiary, marginTop: 4 }}>
        {checklist.totalPoints} checks on this visit
        {checklist.photoPoints > 0
          ? ` · ${checklist.photoPoints} photographed for you`
          : ""}
      </BotText>

      <View style={{ marginTop: 14, gap: 2 }}>
        {shown.map((point, index) => (
          <ChecklistLine
            key={point.id}
            BOT={BOT}
            reduced={reduced}
            label={point.label}
            requiresPhoto={point.requiresPhoto}
            sectionTitle={
              index === 0 || shown[index - 1].sectionTitle !== point.sectionTitle
                ? point.sectionTitle
                : null
            }
          />
        ))}
      </View>

      {revealDone && hidden > 0 && !expanded ? (
        <Pressable
          onPress={() => setExpanded(true)}
          accessibilityRole="button"
          accessibilityLabel={`Show all ${flat.length} checks`}
          style={{ flexDirection: "row", alignItems: "center", gap: 6, marginTop: 10 }}
        >
          <BotText style={{ fontSize: 13, fontWeight: "600", color: BOT.brandLight }}>
            + {hidden} more {hidden === 1 ? "check" : "checks"}
          </BotText>
          <Ionicons name="chevron-down" size={13} color={BOT.brandLight} />
        </Pressable>
      ) : null}

      <View
        style={{
          flexDirection: "row", alignItems: "center", gap: 8,
          marginTop: 14, paddingTop: 12, borderTopWidth: 1, borderTopColor: BOT.borderSubtle,
        }}
      >
        <Ionicons name="shield-checkmark-outline" size={13} color={BOT.success} />
        <BotText style={{ flex: 1, fontSize: 13, color: BOT.textTertiary }}>
          Your technician records each one, so you can see it was done.
        </BotText>
      </View>

      <Pressable
        onPress={onContinue}
        accessibilityRole="button"
        accessibilityLabel="Continue"
        style={{
          height: 44, borderRadius: 16, marginTop: 14,
          alignItems: "center", justifyContent: "center", backgroundColor: BOT.brand,
        }}
      >
        <BotText style={{ fontSize: 15, fontWeight: "700", color: BOT.bubbleOnBrand }}>
          Looks good
        </BotText>
      </Pressable>
    </View>
  );
}

/** One point, fading and sliding in as it is revealed. */
function ChecklistLine({
  BOT, reduced, label, requiresPhoto, sectionTitle,
}: {
  BOT: ReturnType<typeof useBotColors>;
  reduced: boolean;
  label: string;
  requiresPhoto: boolean;
  sectionTitle: string | null;
}) {
  const progress = useRef(new Animated.Value(reduced ? 1 : 0)).current;
  useEffect(() => {
    if (reduced) return;
    Animated.timing(progress, {
      toValue: 1, duration: 280, easing: Easing.out(Easing.cubic), useNativeDriver: true,
    }).start();
  }, [progress, reduced]);

  const style = {
    opacity: progress,
    transform: [
      { translateY: progress.interpolate({ inputRange: [0, 1], outputRange: [6, 0] }) },
    ],
  };

  return (
    <Animated.View style={style}>
      {sectionTitle ? (
        <BotText
          style={{
            fontSize: 12, fontWeight: "700", color: BOT.textTertiary,
            textTransform: "uppercase", letterSpacing: 0.4, marginTop: 10, marginBottom: 4,
          }}
        >
          {sectionTitle}
        </BotText>
      ) : null}
      <View style={{ flexDirection: "row", alignItems: "flex-start", gap: 8, paddingVertical: 4 }}>
        <Ionicons
          name="checkmark-circle"
          size={16}
          color={BOT.success}
          style={{ marginTop: 1 }}
        />
        <BotText style={{ flex: 1, fontSize: 15, lineHeight: 21, color: BOT.textSecondary }}>
          {label}
        </BotText>
        {requiresPhoto ? (
          <Ionicons name="camera-outline" size={14} color={BOT.textTertiary} style={{ marginTop: 3 }} />
        ) : null}
      </View>
    </Animated.View>
  );
}
