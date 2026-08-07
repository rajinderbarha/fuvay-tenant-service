import React, { useEffect, useRef, useState } from "react";
import { View, Text, Pressable, Animated, Easing } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useReducedMotion } from "../../design-system/theme";
import { useBotColors } from "./botTheme";

/**
 * Visual primitives for the merged booking chat -- its own dark, animated
 * language (working-step traces, shimmering labels, staged pill tracker)
 * matching the reference bot on explicit request. Every animation respects
 * reduced-motion (falls back to a static equivalent), same discipline as
 * TypingBubble/AssistantActivity elsewhere in the app.
 */

export type BotStageStatus = "done" | "active" | "pending";

export function BotStageTracker({ stages, activeIndex, allDone }: { stages: string[]; activeIndex: number; allDone: boolean }) {
  const BOT = useBotColors();
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
              <Text style={{ fontSize: 10.5, color: done ? BOT.success : active ? BOT.brandLight : BOT.textFaint }}>
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
  const BOT = useBotColors();
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

/** Three bouncing dots. Matches the reference's `bounceDot` keyframe:
 * translateY 0 -> -3px -> 0 with opacity .5 -> 1 -> .5 over 1.1s, each dot
 * offset by 150ms. The offset is applied by staggering the loop START (not
 * by a per-iteration delay), so the dots keep a constant phase difference
 * instead of drifting apart on every cycle. */
export function BotTypingDots() {
  const BOT = useBotColors();
  const reduced = useReducedMotion();
  const d0 = useRef(new Animated.Value(0)).current;
  const d1 = useRef(new Animated.Value(0)).current;
  const d2 = useRef(new Animated.Value(0)).current;
  const dots = [d0, d1, d2];

  useEffect(() => {
    if (reduced) return;
    const loops = dots.map(v =>
      Animated.loop(Animated.timing(v, { toValue: 1, duration: 1100, easing: Easing.inOut(Easing.ease), useNativeDriver: true })),
    );
    const timers = loops.map((l, i) => setTimeout(() => l.start(), i * 150));
    return () => {
      timers.forEach(clearTimeout);
      loops.forEach(l => l.stop());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reduced]);

  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 6, paddingLeft: 36 }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 14, height: 32, borderRadius: 16, backgroundColor: BOT.surfaceSunken, borderWidth: 1, borderColor: BOT.borderSubtle }}>
        {dots.map((v, i) => (
          <Animated.View
            key={i}
            style={{
              width: 6, height: 6, borderRadius: 3, backgroundColor: BOT.textTertiary,
              opacity: reduced ? 0.7 : v.interpolate({ inputRange: [0, 0.4, 0.8, 1], outputRange: [0.5, 1, 0.5, 0.5] }),
              transform: reduced ? undefined : [{ translateY: v.interpolate({ inputRange: [0, 0.4, 0.8, 1], outputRange: [0, -3, 0, 0] }) }],
            }}
          />
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
  const BOT = useBotColors();
  const reduced = useReducedMotion();
  const entrance = useTurnEntrance();
  // Matches the reference's `shimmerText` keyframe exactly: opacity
  // .65 <-> 1 over 1.3s, easing in and out.
  const shimmer = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    if (reduced || status === "done") return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(shimmer, { toValue: 0.65, duration: 650, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(shimmer, { toValue: 1, duration: 650, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [reduced, status, shimmer]);

  const done = status === "done";
  return (
    <Animated.View style={[{ flexDirection: "row", alignItems: "center", paddingLeft: 36 }, entrance]}>
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
            fontSize: 12,
            color: done ? BOT.textMuted : BOT.brandLight,
            opacity: done || reduced ? 1 : shimmer,
          }}
        >
          {label}
        </Animated.Text>
      </View>
    </Animated.View>
  );
}

/** Fades + slides a turn in on mount, so each new bubble/card arrives as a
 * visible transition rather than popping in instantly -- respects
 * reduced-motion by rendering at rest immediately. `delay` staggers
 * siblings (option chips, trace lines) so a group cascades in. */
function useTurnEntrance(delay = 0) {
  const reduced = useReducedMotion();
  const progress = useRef(new Animated.Value(reduced ? 1 : 0)).current;
  useEffect(() => {
    if (reduced) return;
    Animated.timing(progress, { toValue: 1, duration: 300, delay, useNativeDriver: true }).start();
  }, [reduced, progress, delay]);
  return {
    opacity: progress,
    transform: [
      { translateY: progress.interpolate({ inputRange: [0, 1], outputRange: [10, 0] }) },
      { scale: progress.interpolate({ inputRange: [0, 1], outputRange: [0.97, 1] }) },
    ],
  };
}

/** The header's live status dot -- reference `dotPulse`: opacity .35 <-> 1
 * over 1.4s, signalling the assistant is actively working. */
export function BotPulseDot({ color, size = 6 }: { color: string; size?: number }) {
  const reduced = useReducedMotion();
  const pulse = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    if (reduced) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 0.35, duration: 700, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 1, duration: 700, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [reduced, pulse]);
  return (
    <Animated.View
      style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: color, opacity: reduced ? 1 : pulse }}
    />
  );
}

export interface WorkingTraceEntry {
  label: string;
  status: "pending" | "done";
}

/**
 * Accumulates the stages a real backend sequence has actually passed
 * through, so the chat shows a growing checklist instead of one step that
 * vanishes -- the visual language of the reference bot, but every line is
 * a stage that genuinely ran.
 *
 * The critical difference from the reference: nothing here is on a timer.
 * A line flips to "done" only because the controller genuinely moved to
 * the next stage (or finished), so a slow backend call shimmers for
 * exactly as long as it really takes.
 */
export function useWorkingTrace(currentLabel: string | null): WorkingTraceEntry[] {
  const [entries, setEntries] = useState<WorkingTraceEntry[]>([]);
  useEffect(() => {
    setEntries(prev => {
      if (currentLabel === null) {
        // Sequence finished -- settle everything that was still running.
        return prev.some(e => e.status === "pending")
          ? prev.map(e => ({ ...e, status: "done" as const }))
          : prev;
      }
      if (prev.length > 0 && prev[prev.length - 1].label === currentLabel) return prev;
      return [
        ...prev.map(e => ({ ...e, status: "done" as const })),
        { label: currentLabel, status: "pending" as const },
      ];
    });
  }, [currentLabel]);
  return entries;
}

/** The accumulated trace: settled steps stay visible with a check, the
 * live one shimmers under a spinner, and typing dots trail it while work
 * is genuinely still in flight. */
export function BotWorkingTrace({ entries }: { entries: WorkingTraceEntry[] }) {
  if (entries.length === 0) return null;
  const running = entries.some(e => e.status === "pending");
  return (
    <View style={{ gap: 6 }}>
      {entries.map((e, i) => (
        <BotWorkingStep key={`${e.label}-${i}`} label={e.label} status={e.status} />
      ))}
      {running ? <BotTypingDots /> : null}
    </View>
  );
}

export function BotAssistantBubble({ text, children }: { text?: string; children?: React.ReactNode }) {
  const BOT = useBotColors();
  const entrance = useTurnEntrance();
  return (
    <Animated.View style={[{ flexDirection: "row", alignItems: "flex-start", gap: 8 }, entrance]}>
      <View style={{ width: 28, height: 28, borderRadius: 14, alignItems: "center", justifyContent: "center", backgroundColor: BOT.surfaceRaised, borderWidth: 1, borderColor: BOT.border, marginTop: 2 }}>
        <Ionicons name="sparkles" size={13} color={BOT.brand} />
      </View>
      {text ? (
        <View style={{ maxWidth: "80%", borderRadius: 16, borderTopLeftRadius: 4, paddingHorizontal: 16, paddingVertical: 10, backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.borderSubtle }}>
          <Text style={{ fontSize: 13, lineHeight: 19, color: BOT.textPrimary }}>{text}</Text>
        </View>
      ) : (
        <View style={{ flex: 1 }}>{children}</View>
      )}
    </Animated.View>
  );
}

export function BotUserBubble({ text }: { text: string }) {
  const BOT = useBotColors();
  const entrance = useTurnEntrance();
  return (
    <Animated.View style={[{ flexDirection: "row", justifyContent: "flex-end" }, entrance]}>
      <View style={{ maxWidth: "78%", borderRadius: 16, borderTopRightRadius: 4, paddingHorizontal: 16, paddingVertical: 10, backgroundColor: BOT.brand }}>
        <Text style={{ fontSize: 13, fontWeight: "600", color: BOT.bubbleOnBrand }}>{text}</Text>
      </View>
    </Animated.View>
  );
}

export function BotOptionChips({
  items, selected, disabled, onSelect,
}: { items: string[]; selected: string | null; disabled?: boolean; onSelect: (label: string) => void }) {
  const BOT = useBotColors();
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, paddingLeft: 36 }}>
      {items.map((label, i) => (
        <OptionChip
          key={label}
          label={label}
          index={i}
          isSelected={selected === label}
          isInactive={!!selected && selected !== label}
          disabled={disabled || !!selected}
          onSelect={onSelect}
        />
      ))}
    </View>
  );
}

/** Split out so each chip owns its own staggered entrance -- the
 * reference's `animationDelay: ix * 90ms` cascade. */
function OptionChip({
  label, index, isSelected, isInactive, disabled, onSelect,
}: { label: string; index: number; isSelected: boolean; isInactive: boolean; disabled?: boolean; onSelect: (label: string) => void }) {
  const BOT = useBotColors();
  const entrance = useTurnEntrance(index * 90);
  return (
    <Animated.View style={entrance}>
      <Pressable
        disabled={disabled}
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
        <Text style={{ fontSize: 12.5, fontWeight: "500", color: isSelected ? BOT.bubbleOnBrand : BOT.textSecondary }}>{label}</Text>
      </Pressable>
    </Animated.View>
  );
}

export function BotCard({ children }: { children: React.ReactNode }) {
  const BOT = useBotColors();
  const entrance = useTurnEntrance();
  return (
    <Animated.View style={[{ marginLeft: 36, borderRadius: 20, padding: 16, backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.borderSubtle }, entrance]}>
      {children}
    </Animated.View>
  );
}

export function BotPrimaryButton({ label, onPress, disabled, loading }: { label: string; onPress: () => void | Promise<void>; disabled?: boolean; loading?: boolean }) {
  const BOT = useBotColors();
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
      <Text style={{ fontSize: 13.5, fontWeight: "700", color: isDisabled && !loading && !busy ? BOT.textDim : BOT.bubbleOnBrand }}>
        {loading || busy ? "Working…" : label}
      </Text>
    </Pressable>
  );
}
