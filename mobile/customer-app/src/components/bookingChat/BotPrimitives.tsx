import React, { useEffect, useRef, useState } from "react";
import { View, Text, Pressable, Animated } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useReducedMotion } from "../../design-system/theme";
import { BOT } from "./botTheme";

/**
 * Visual primitives for the merged booking chat -- its own dark, animated
 * language (working-step traces, shimmering labels, staged pill tracker)
 * matching the reference bot on explicit request. Every animation respects
 * reduced-motion (falls back to a static equivalent), same discipline as
 * TypingBubble/AssistantActivity elsewhere in the app.
 */

export type BotStageStatus = "done" | "active" | "pending";

export function BotStageTracker({ stages, activeIndex, allDone }: { stages: string[]; activeIndex: number; allDone: boolean }) {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", marginTop: 14 }}>
      {stages.map((s, i) => {
        const done = i < activeIndex || allDone;
        const active = i === activeIndex && !allDone;
        return (
          <React.Fragment key={s}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 6, flexShrink: 0 }}>
              {done ? (
                <Ionicons name="checkmark-circle" size={13} color={BOT.success} />
              ) : active ? (
                <SpinningIcon />
              ) : (
                <Ionicons name="ellipse-outline" size={11} color={BOT.textFaint} />
              )}
              <Text style={{ fontSize: 10.5, fontFamily: "monospace", color: done ? BOT.success : active ? BOT.brandLight : BOT.textFaint }}>
                {s}
              </Text>
            </View>
            {i < stages.length - 1 ? <View style={{ flex: 1, height: 1, marginHorizontal: 4, backgroundColor: BOT.borderSubtle }} /> : null}
          </React.Fragment>
        );
      })}
    </View>
  );
}

function SpinningIcon() {
  const reduced = useReducedMotion();
  const spin = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (reduced) return;
    const loop = Animated.loop(Animated.timing(spin, { toValue: 1, duration: 900, useNativeDriver: true }));
    loop.start();
    return () => loop.stop();
  }, [reduced, spin]);
  const rotate = spin.interpolate({ inputRange: [0, 1], outputRange: ["0deg", "360deg"] });
  return (
    <Animated.View style={{ transform: reduced ? undefined : [{ rotate }] }}>
      <Ionicons name="sync" size={13} color={BOT.brand} />
    </Animated.View>
  );
}

/** Three bouncing dots, matching TypingBubble's existing pulse pattern but
 * restyled for this dark surface. */
export function BotTypingDots() {
  const reduced = useReducedMotion();
  const dots = [useRef(new Animated.Value(0.5)).current, useRef(new Animated.Value(0.5)).current, useRef(new Animated.Value(0.5)).current];
  useEffect(() => {
    if (reduced) return;
    const loops = dots.map((v, i) =>
      Animated.loop(
        Animated.sequence([
          Animated.timing(v, { toValue: 1, duration: 260, delay: i * 130, useNativeDriver: true }),
          Animated.timing(v, { toValue: 0.5, duration: 260, useNativeDriver: true }),
        ]),
      ),
    );
    loops.forEach(l => l.start());
    return () => loops.forEach(l => l.stop());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reduced]);
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 6, paddingLeft: 36 }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 14, height: 32, borderRadius: 16, backgroundColor: BOT.surfaceSunken, borderWidth: 1, borderColor: BOT.borderSubtle }}>
        {dots.map((v, i) => (
          <Animated.View key={i} style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: BOT.textFaint, opacity: reduced ? 0.7 : v }} />
        ))}
      </View>
    </View>
  );
}

/** One line of a working-step trace: pending (spinner + shimmer text) ->
 * done (check + settled text). `status` is driven by a REAL async call
 * resolving, never a fixed timer -- this component only renders the
 * state it's given. */
export function BotWorkingStep({ label, status }: { label: string; status: "pending" | "done" }) {
  const reduced = useReducedMotion();
  const shimmer = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    if (reduced || status === "done") return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(shimmer, { toValue: 0.6, duration: 650, useNativeDriver: true }),
        Animated.timing(shimmer, { toValue: 1, duration: 650, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [reduced, status, shimmer]);

  const done = status === "done";
  return (
    <View style={{ flexDirection: "row", alignItems: "center", paddingLeft: 36 }}>
      <View
        style={{
          flexDirection: "row", alignItems: "center", gap: 10,
          paddingLeft: 12, paddingRight: 16, height: 40, borderRadius: 16, minWidth: 200,
          backgroundColor: done ? BOT.surfaceSunken : BOT.surfaceActive,
          borderWidth: 1, borderColor: done ? BOT.borderSubtle : BOT.borderActive,
        }}
      >
        {done ? <Ionicons name="checkmark-circle" size={14} color={BOT.success} /> : <SpinningIcon />}
        <Animated.Text
          style={{
            fontSize: 12, fontFamily: "monospace",
            color: done ? BOT.textMuted : "#BFD6FF",
            opacity: done || reduced ? 1 : shimmer,
          }}
        >
          {label}
        </Animated.Text>
      </View>
    </View>
  );
}

export function BotAssistantBubble({ text, children }: { text?: string; children?: React.ReactNode }) {
  return (
    <View style={{ flexDirection: "row", alignItems: "flex-start", gap: 8 }}>
      <View style={{ width: 28, height: 28, borderRadius: 14, alignItems: "center", justifyContent: "center", backgroundColor: BOT.surfaceRaised, borderWidth: 1, borderColor: BOT.border, marginTop: 2 }}>
        <Ionicons name="sparkles" size={13} color={BOT.brand} />
      </View>
      {text ? (
        <View style={{ maxWidth: "80%", borderRadius: 16, borderTopLeftRadius: 4, paddingHorizontal: 16, paddingVertical: 10, backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.borderSubtle }}>
          <Text style={{ fontSize: 13, lineHeight: 19, color: "#E4E8EE" }}>{text}</Text>
        </View>
      ) : (
        <View style={{ flex: 1 }}>{children}</View>
      )}
    </View>
  );
}

export function BotUserBubble({ text }: { text: string }) {
  return (
    <View style={{ flexDirection: "row", justifyContent: "flex-end" }}>
      <View style={{ maxWidth: "78%", borderRadius: 16, borderTopRightRadius: 4, paddingHorizontal: 16, paddingVertical: 10, backgroundColor: BOT.brand }}>
        <Text style={{ fontSize: 13, fontWeight: "600", color: BOT.bg }}>{text}</Text>
      </View>
    </View>
  );
}

export function BotOptionChips({
  items, selected, disabled, onSelect,
}: { items: string[]; selected: string | null; disabled?: boolean; onSelect: (label: string) => void }) {
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, paddingLeft: 36 }}>
      {items.map(label => {
        const isSelected = selected === label;
        const isInactive = !!selected && !isSelected;
        return (
          <Pressable
            key={label}
            disabled={disabled || !!selected}
            onPress={() => onSelect(label)}
            accessibilityRole="button"
            accessibilityLabel={label}
            style={{
              paddingHorizontal: 14, height: 36, borderRadius: 18,
              alignItems: "center", justifyContent: "center",
              backgroundColor: isSelected ? BOT.brand : BOT.surface,
              borderWidth: 1, borderColor: isSelected ? BOT.brand : BOT.border,
              opacity: isInactive ? 0.4 : 1,
            }}
          >
            <Text style={{ fontSize: 12.5, fontWeight: "500", color: isSelected ? BOT.bg : BOT.textSecondary }}>{label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export function BotCard({ children }: { children: React.ReactNode }) {
  return (
    <View style={{ marginLeft: 36, borderRadius: 20, padding: 16, backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.borderSubtle }}>
      {children}
    </View>
  );
}

export function BotPrimaryButton({ label, onPress, disabled, loading }: { label: string; onPress: () => void | Promise<void>; disabled?: boolean; loading?: boolean }) {
  const [busy, setBusy] = useState(false);
  const isDisabled = disabled || loading || busy;
  async function handlePress() {
    if (isDisabled) return;
    const result = onPress();
    if (result && typeof result.then === "function") {
      setBusy(true);
      try { await result; } finally { setBusy(false); }
    }
  }
  return (
    <Pressable
      onPress={handlePress}
      disabled={isDisabled}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: isDisabled }}
      style={{
        height: 44, borderRadius: 16, alignItems: "center", justifyContent: "center",
        backgroundColor: isDisabled && !loading && !busy ? BOT.surfaceRaised : BOT.brand,
        opacity: isDisabled && !loading && !busy ? 0.6 : 1,
      }}
    >
      <Text style={{ fontSize: 13.5, fontWeight: "700", color: isDisabled && !loading && !busy ? BOT.textDim : BOT.bg }}>
        {loading || busy ? "Working…" : label}
      </Text>
    </Pressable>
  );
}
