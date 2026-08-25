import React, { useEffect, useRef, useState } from "react";
import { View, Text, Pressable, Animated, Easing } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useReducedMotion } from "../../design-system/theme";
import { useBotColors } from "./botTheme";
import { FuvayIcon } from "../FuvayIcon";

/**
 * Visual primitives for the merged booking chat -- its own dark, animated
 * language (working-step traces, shimmering labels, staged pill tracker)
 * matching the reference bot on explicit request. Every animation respects
 * reduced-motion (falls back to a static equivalent), same discipline as
 * TypingBubble/AssistantActivity elsewhere in the app.
 */

export type BotStageStatus = "done" | "active" | "pending";

function stageIcon(index: number): React.ComponentProps<typeof Ionicons>["name"] {
  return ["chatbubble-ellipses-outline", "people-outline", "document-text-outline", "checkmark-circle-outline"][index] as React.ComponentProps<typeof Ionicons>["name"];
}

export function BotStageTracker({ stages, activeIndex, allDone }: { stages: string[]; activeIndex: number; allDone: boolean }) {
  const BOT = useBotColors();
  return (
    <View
      accessibilityLabel={`Booking step ${Math.min(activeIndex + 1, stages.length)} of ${stages.length}: ${stages[activeIndex] ?? stages[stages.length - 1]}`}
      style={{ marginTop: 12, padding: 4, borderRadius: 10, flexDirection: "row", gap: 3, backgroundColor: BOT.surfaceSunken }}
    >
      {stages.map((s, i) => {
          const done = i < activeIndex || allDone;
          const active = i === activeIndex && !allDone;
          return (
            <View key={s} style={{ flex: 1, minWidth: 0, minHeight: 52, borderRadius: 8, paddingHorizontal: 7, paddingVertical: 7, justifyContent: "space-between", backgroundColor: active ? BOT.surface : "transparent", borderWidth: active ? 1 : 0, borderColor: BOT.borderSubtle }}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 5 }}>
              <View
                style={{
                  width: 18, height: 18, borderRadius: 6,
                  alignItems: "center", justifyContent: "center",
                  backgroundColor: done ? BOT.success : active ? BOT.brand : BOT.surfaceRaised,
                  borderWidth: done || active ? 0 : 1,
                  borderColor: BOT.border,
                }}
              >
                {done ? (
                  <Ionicons name="checkmark" size={11} color={BOT.bubbleOnBrand} />
                ) : (
                  <Ionicons name={stageIcon(i)} size={11} color={active ? BOT.bubbleOnBrand : BOT.textFaint} />
                )}
              </View>
              <Text style={{ fontSize: 8, fontWeight: "800", color: active ? BOT.brandLight : BOT.textTertiary }}>{done ? "DONE" : active ? "CURRENT" : "UP NEXT"}</Text>
              </View>
              <Text style={{ fontSize: 9, lineHeight: 11, fontWeight: active ? "700" : "600", color: active ? BOT.textPrimary : BOT.textMuted }} numberOfLines={2}>{s}</Text>
            </View>
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
    <Animated.View style={[{ flexDirection: "row", alignItems: "center", paddingLeft: 36, paddingRight: 8 }, entrance]}>
      <View
        style={{
          flex: 1, flexDirection: "row", alignItems: "center", gap: 10,
          paddingLeft: 14, paddingRight: 16, height: 46, borderRadius: 16,
          backgroundColor: done ? BOT.surfaceSunken : BOT.surfaceActive,
          borderWidth: 1, borderColor: done ? BOT.borderSubtle : BOT.borderActive,
        }}
      >
        {done ? <Ionicons name="checkmark-circle" size={16} color={BOT.success} /> : <SpinningIcon />}
        <Animated.Text
          numberOfLines={1}
          style={{
            flex: 1,
            fontSize: 15,
            fontWeight: done ? "400" : "600",
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

/** How long each step stays on screen before the next is revealed.
 *
 * This is a LEGIBILITY FLOOR, not fake work. The stages are real ones the
 * controller genuinely passed through, but they can resolve in single-digit
 * milliseconds -- `validating_answer` -> `saving_progress` are set on
 * consecutive lines around one await, so without a floor the customer sees
 * a flicker and cannot read either. Holding each real step for ~700ms is
 * what makes the trace readable. Nothing here invents a step that did not
 * happen, and a SLOW call still shimmers for its full real duration -- the
 * floor only ever extends a step, never truncates one. */
const MIN_STEP_MS = 700;

/**
 * Accumulates a single changing stage value into the ordered list of stages
 * observed so far, for controllers that expose only a "current stage" and
 * change it across real awaits (so each value genuinely gets its own
 * render). Controllers that set several stages inside ONE synchronous block
 * must expose an append-only trace instead, since React batches those into
 * a single observable value -- see `AssistantControllerState.activityTrace`.
 */
export function useObservedSequence(current: string | null): string[] {
  const [observed, setObserved] = useState<string[]>([]);
  useEffect(() => {
    if (current === null) return;
    setObserved(prev => (prev.length > 0 && prev[prev.length - 1] === current ? prev : [...prev, current]));
  }, [current]);
  return observed;
}

/**
 * Reveals the stages a real backend sequence passed through one at a time,
 * so the chat shows a growing checklist -- the reference bot's working-step
 * language, driven by real events.
 */
export function useWorkingTrace(labels: string[], running: boolean): WorkingTraceEntry[] {
  const [revealed, setRevealed] = useState(0);
  const [settled, setSettled] = useState(false);
  const seenRef = useRef<string[]>([]);

  // A continuing operation only ever APPENDS stages; a brand-new operation
  // replaces the list wholesale. Detecting that here (rather than keying on
  // something external like the question id) matters: the next question's
  // envelope lands synchronously, so an external key would wipe the trace
  // before the customer ever saw the steps that produced it.
  useEffect(() => {
    const prev = seenRef.current;
    const isSameOperation = labels.length >= prev.length && prev.every((l, i) => labels[i] === l);
    seenRef.current = labels;
    if (!isSameOperation) {
      setRevealed(0);
      setSettled(false);
    } else if (labels.length > prev.length) {
      setSettled(false);
    }
  }, [labels]);

  // Reveal the recorded stages one at a time, each held long enough to read.
  useEffect(() => {
    if (revealed >= labels.length) return;
    if (revealed === 0) {
      setRevealed(1);
      return;
    }
    const timer = setTimeout(() => setRevealed(r => r + 1), MIN_STEP_MS);
    return () => clearTimeout(timer);
  }, [revealed, labels.length]);

  // Settle the final step once the real work has finished AND that step has
  // had its readable moment.
  useEffect(() => {
    if (running || labels.length === 0 || revealed < labels.length) return;
    const timer = setTimeout(() => setSettled(true), MIN_STEP_MS);
    return () => clearTimeout(timer);
  }, [running, revealed, labels.length]);

  return labels.slice(0, revealed).map((label, i) => ({
    label,
    status: i < revealed - 1 || settled ? "done" : "pending",
  }));
}

/** The accumulated trace: settled steps stay visible with a check, the
 * live one shimmers under a spinner, and typing dots trail it while work
 * is genuinely still in flight. */
export function BotWorkingTrace({ entries }: { entries: WorkingTraceEntry[] }) {
  const BOT = useBotColors();
  const running = entries.some(e => e.status === "pending");
  const elapsed = useElapsedSeconds(running);
  const [expanded, setExpanded] = useState(false);
  const [finalSeconds, setFinalSeconds] = useState<number | null>(null);
  const startedAtRef = useRef<number | null>(null);

  useEffect(() => {
    if (running) {
      startedAtRef.current = Date.now();
      setFinalSeconds(null);
      setExpanded(false);
    } else if (startedAtRef.current !== null) {
      setFinalSeconds(Math.max(1, Math.round((Date.now() - startedAtRef.current) / 1000)));
      startedAtRef.current = null;
    }
  }, [running]);

  if (entries.length === 0) return null;

  // Finished work COLLAPSES to one line. Leaving every completed step
  // expanded turned the transcript into a wall of grey boxes that crowded
  // out the actual conversation -- a real assistant shows its work while
  // working, then gets out of the way. The detail is still one tap away.
  if (!running && !expanded) {
    return (
      <BotTraceSummary
        stepCount={entries.length}
        seconds={finalSeconds}
        onExpand={() => setExpanded(true)}
      />
    );
  }

  return (
    <View style={{ gap: 6 }}>
      {entries.map((e, i) => (
        <BotWorkingStep key={`${e.label}-${i}`} label={e.label} status={e.status} />
      ))}
      {running ? (
        <BotWorkingFooter elapsedSeconds={elapsed} stepCount={entries.length} />
      ) : (
        <Pressable
          onPress={() => setExpanded(false)}
          accessibilityRole="button"
          accessibilityLabel="Hide the steps"
          style={{ paddingLeft: 36, paddingTop: 2 }}
        >
          <Text style={{ fontSize: 13, color: BOT.textTertiary }}>Hide steps</Text>
        </Pressable>
      )}
    </View>
  );
}

/** One quiet line standing in for a finished run. */
function BotTraceSummary({
  stepCount, seconds, onExpand,
}: { stepCount: number; seconds: number | null; onExpand: () => void }) {
  const BOT = useBotColors();
  return (
    <Pressable
      onPress={onExpand}
      accessibilityRole="button"
      accessibilityLabel={`Show the ${stepCount} steps that ran`}
      style={{ flexDirection: "row", alignItems: "center", gap: 8, paddingLeft: 36, paddingVertical: 2 }}
    >
      <Ionicons name="checkmark-circle" size={15} color={BOT.success} />
      <Text style={{ fontSize: 13, color: BOT.textTertiary }}>
        Done · {stepCount} step{stepCount === 1 ? "" : "s"}{seconds !== null ? ` · ${seconds}s` : ""}
      </Text>
      <Ionicons name="chevron-down" size={13} color={BOT.textTertiary} />
    </Pressable>
  );
}

/** Seconds since the current run began. Real wall-clock elapsed time --
 * the one "how hard is it working" number this screen can honestly show. */
function useElapsedSeconds(active: boolean): number {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    if (!active) {
      setSeconds(0);
      return;
    }
    const startedAt = Date.now();
    const id = setInterval(() => setSeconds(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => clearInterval(id);
  }, [active]);
  return seconds;
}

/**
 * Claude-Code-style running status line: a shimmering "Working…" label with
 * the live elapsed time and how many steps have run.
 *
 * Deliberately NOT a token count. Token usage is real only on the DeepSeek
 * conversation path (ai_conversation records prompt/completion tokens); the
 * question flow this trace covers is a deterministic catalog walk that
 * spends no tokens at all, so any number shown here would be invented.
 * Elapsed time and step count are both genuinely measured.
 */
function BotWorkingFooter({ elapsedSeconds, stepCount }: { elapsedSeconds: number; stepCount: number }) {
  const BOT = useBotColors();
  const reduced = useReducedMotion();
  const shimmer = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    if (reduced) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(shimmer, { toValue: 0.65, duration: 650, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(shimmer, { toValue: 1, duration: 650, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [reduced, shimmer]);

  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 8, paddingLeft: 36, marginTop: 2 }}>
      <BotPulseDot color={BOT.brand} size={7} />
      <Animated.Text style={{ fontSize: 13, fontWeight: "600", color: BOT.brandLight, opacity: reduced ? 1 : shimmer }}>
        Working…
      </Animated.Text>
      <Text style={{ fontSize: 13, color: BOT.textTertiary }}>
        ({elapsedSeconds}s · {stepCount} step{stepCount === 1 ? "" : "s"})
      </Text>
    </View>
  );
}

export function BotAssistantBubble({ text, children }: { text?: string; children?: React.ReactNode }) {
  const BOT = useBotColors();
  const entrance = useTurnEntrance();
  return (
    <Animated.View style={[{ flexDirection: "row", alignItems: "flex-start", gap: 8 }, entrance]}>
      <View style={{ width: 28, height: 28, borderRadius: 14, alignItems: "center", justifyContent: "center", backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: BOT.border, marginTop: 2 }}>
        <FuvayIcon size={18} accessibilityLabel="Fuvay assistant" />
      </View>
      {text ? (
        <View style={{ maxWidth: "80%", borderRadius: 16, borderTopLeftRadius: 4, paddingHorizontal: 16, paddingVertical: 10, backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.borderSubtle }}>
          <Text style={{ fontSize: 15, lineHeight: 19, color: BOT.textPrimary }}>{text}</Text>
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
        <Text style={{ fontSize: 15, fontWeight: "600", color: BOT.bubbleOnBrand }}>{text}</Text>
      </View>
    </Animated.View>
  );
}

export function BotOptionChips({
  items, selected, disabled, onSelect,
}: { items: string[]; selected: string | null; disabled?: boolean; onSelect: (label: string) => void }) {
  const BOT = useBotColors();
  // Labels are the selection identity for this component. Duplicate labels
  // are therefore not two distinct actions; render one canonical chip rather
  // than producing duplicate React keys and an ambiguous selection.
  const uniqueItems = Array.from(new Set(items));
  return (
    <View style={{ gap: 8, paddingLeft: 36 }}>
      {uniqueItems.map((label, i) => (
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
          minHeight: 52, paddingHorizontal: 14, paddingVertical: 11, borderRadius: 10,
          flexDirection: "row", alignItems: "center", gap: 10,
          backgroundColor: isSelected ? BOT.brand : BOT.surface,
          borderWidth: 1, borderColor: isSelected ? BOT.brand : BOT.border,
          opacity: isInactive ? 0.4 : 1,
        }}
      >
        <View style={{ width: 24, alignItems: "center" }}>
          <Ionicons name={isSelected ? "checkmark-circle" : "ellipse-outline"} size={17} color={isSelected ? BOT.bubbleOnBrand : BOT.textFaint} />
        </View>
        <Text style={{ flex: 1, fontSize: 15, lineHeight: 20, fontWeight: "600", color: isSelected ? BOT.bubbleOnBrand : BOT.textSecondary }}>{label}</Text>
        <Ionicons name="chevron-forward" size={15} color={isSelected ? BOT.bubbleOnBrand : BOT.textFaint} />
      </Pressable>
    </Animated.View>
  );
}

export function BotCard({ children }: { children: React.ReactNode }) {
  const BOT = useBotColors();
  const entrance = useTurnEntrance();
  return (
    <Animated.View style={[{ marginLeft: 36, borderRadius: 12, padding: 16, backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.borderSubtle }, entrance]}>
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
        height: 46, borderRadius: 10, alignItems: "center", justifyContent: "center",
        backgroundColor: isDisabled && !loading && !busy ? BOT.surfaceRaised : BOT.brand,
        opacity: isDisabled && !loading && !busy ? 0.6 : 1,
      }}
    >
      <Text style={{ fontSize: 15, fontWeight: "700", color: isDisabled && !loading && !busy ? BOT.textDim : BOT.bubbleOnBrand }}>
        {loading || busy ? "Working…" : label}
      </Text>
    </Pressable>
  );
}
