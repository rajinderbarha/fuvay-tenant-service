"use client";
/**
 * MODULE-L5-12 — renders earned trust badges with the lucide icon and colour the
 * admin configured. Shared by the provider status page (own badges) and staff
 * views (a team member's badges).
 */
import React from "react";
import {
  Award, Star, Shield, ShieldCheck, Crown, Trophy, Medal, Gem, Sparkles,
  BadgeCheck, Flame, Zap, Heart, ThumbsUp, TrendingUp, CheckCircle2, Rocket, Target,
} from "lucide-react";
import type { EarnedBadge } from "../lib/api";

const ICONS: Record<string, React.ComponentType<{ size?: number; color?: string }>> = {
  award: Award, star: Star, shield: Shield, "shield-check": ShieldCheck, crown: Crown,
  trophy: Trophy, medal: Medal, gem: Gem, sparkles: Sparkles, "badge-check": BadgeCheck,
  flame: Flame, zap: Zap, heart: Heart, "thumbs-up": ThumbsUp, "trending-up": TrendingUp,
  "check-circle": CheckCircle2, rocket: Rocket, target: Target,
};

export function TrustBadgeChip({ badge, size = 16 }: { badge: EarnedBadge; size?: number }) {
  const Cmp = ICONS[badge.icon ?? ""] ?? Award;
  const c = badge.color || "#f59e0b";
  return (
    <span title={badge.description ?? badge.name} style={{
      display: "inline-flex", alignItems: "center", gap: 6, padding: "5px 10px 5px 7px",
      borderRadius: 999, background: `${c}18`, border: `1px solid ${c}55`,
      fontSize: 13, fontWeight: 600, color: "var(--text-primary, #1a1a1a)" }}>
      <span style={{ display: "inline-flex" }}><Cmp size={size} color={c} /></span>
      {badge.name}
    </span>
  );
}

export function TrustBadges({ badges, empty = "No badges earned yet." }: {
  badges: EarnedBadge[]; empty?: string;
}) {
  if (!badges.length) {
    return <p style={{ fontSize: 13, color: "var(--text-tertiary, #888)", margin: 0 }}>{empty}</p>;
  }
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      {badges.map(b => <TrustBadgeChip key={b.assignment_id} badge={b} />)}
    </div>
  );
}
