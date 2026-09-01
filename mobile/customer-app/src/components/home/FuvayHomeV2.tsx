import React, { useEffect, useMemo, useRef } from "react";
import {
  Animated,
  Easing,
  Image,
  ImageBackground,
  ImageSourcePropType,
  Pressable,
  ScrollView,
  View,
  useWindowDimensions,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import Svg, { Defs, Polygon, RadialGradient, Rect, Stop } from "react-native-svg";

import { useReducedMotion, useTheme } from "../../design-system/theme";
import { customerExperienceCopy } from "../../content/customerExperience";
import {
  fuvayHomeReferenceContent as reference,
  type FuvayAccentKey,
} from "../../content/fuvayReferenceContent";
import { fuvayGradientGeometry, type FuvayTheme } from "../../design-system/tokens/fuvay";
import type {
  HomeActiveBooking,
  HomeCampaign,
  HomeMasterService,
  HomeQuickIssue,
  HomeServiceGroup,
} from "../../domain/customerHome";
import { AppLucideIcon, type AppLucideName } from "../AppLucideIcon";
import { AppText } from "../AppText";
import { FuvayIcon } from "../FuvayIcon";
import { FuvayServiceCard } from "../fuvay/FuvayServiceCard";
import { FuvaySquircleTile } from "../fuvay/FuvaySquircleTile";
import { FuvayTile } from "../fuvay/FuvayTile";
import { ServiceSearch } from "./ServiceSearch";

const images = {
  services: [
    require("../../../assets/service-artwork-2d/air-conditioner-service-v1.png"),
    require("../../../assets/service-artwork-2d/chimney-service-v1.png"),
    require("../../../assets/service-artwork-2d/refrigerator-service-v1.png"),
    require("../../../assets/service-artwork-2d/washing-machine-service-v1.png"),
    require("../../../assets/service-artwork-2d/water-heater-service-v1.png"),
    require("../../../assets/service-artwork-2d/water-purifier-service-v1.png"),
  ] as ImageSourcePropType[],
} as const;

const iconRules: Array<[RegExp, AppLucideName]> = [
  [/refriger|fridge/i, "fridge-outline"],
  [/washing/i, "washing-machine"],
  [/chimney|hood/i, "stove"],
  [/purifier|\bro\b|water/i, "water-circle"],
  [/geyser|heater|flame/i, "water-boiler"],
  [/air|ac|cool|vent/i, "air-conditioner"],
  [/microwave|oven/i, "microwave"],
  [/plumb|pipe|drain/i, "pipe-wrench"],
  [/electric|power|wire|inverter/i, "lightning-bolt-outline"],
  [/paint/i, "paintbrush"],
  [/clean/i, "spray-bottle"],
  [/pest/i, "bug-outline"],
];

function iconFor(label: string): AppLucideName {
  return iconRules.find(([rule]) => rule.test(label))?.[1] ?? "tools";
}

function accentFor(t: FuvayTheme, key: FuvayAccentKey): string {
  return key === "neutral" ? t.tile.icon : t.accents[key];
}

function AmbientGlow({ anchor = "topRight" }: { anchor?: "topRight" | "bottomLeft" }) {
  const { theme } = useTheme();
  const t = theme.fuvay;
  const topRight = anchor === "topRight";

  // On iOS an absolutely positioned SVG with percentage dimensions can be
  // measured before a wrapping card reaches its final height. That left the
  // bottom-left glow ending above the final row of specialist labels. Use a
  // card-sized native gradient for this anchor so it always reaches the
  // rounded panel's real bottom edge.
  if (!topRight) {
    return (
      <LinearGradient
        pointerEvents="none"
        colors={t.surfaces.ambientGlow}
        locations={[0, 0.58, 1]}
        start={{ x: 1, y: 0 }}
        end={{ x: 0, y: 1 }}
        style={{ position: "absolute", top: 0, right: 0, bottom: 0, left: 0 }}
      />
    );
  }

  return (
    <Svg pointerEvents="none" width="120%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none" style={{ position: "absolute", left: "-10%", top: 0, bottom: 0 }}>
      <Defs>
        <RadialGradient id={`ambient-${anchor}`} cx={topRight ? "86" : "12"} cy={topRight ? "2" : "92"} r="72" gradientUnits="userSpaceOnUse">
          <Stop offset="0" stopColor={t.accents.a2} stopOpacity={t.isDark ? 0.18 : 0.12} />
          <Stop offset="1" stopColor={t.accents.a2} stopOpacity="0" />
        </RadialGradient>
      </Defs>
      <Rect width="100" height="100" fill={`url(#ambient-${anchor})`} />
    </Svg>
  );
}

const rotatingAccents: readonly FuvayAccentKey[] = ["a2", "a3", "a1", "a4"];

function serviceArtwork(uri: string | null | undefined, label: string, index = 0): ImageSourcePropType {
  if (uri) return { uri };
  const fallbackIndex = /chimney|hood/i.test(label)
    ? 1
    : /refriger|fridge/i.test(label)
      ? 2
      : /washing/i.test(label)
        ? 3
        : /geyser|heater/i.test(label)
          ? 4
          : /purifier|\bro\b/i.test(label)
            ? 5
            : /air|\bac\b|cool/i.test(label)
              ? 0
              : index % images.services.length;
  return images.services[fallbackIndex];
}

/** Prefer a varied set of richly-authored backend services, then fill any
 * remaining slots without inventing content or duplicating records. */
function selectDiverseServices(services: HomeMasterService[], limit: number): HomeMasterService[] {
  const selected: HomeMasterService[] = [];
  const selectedIds = new Set<string>();
  const selectedGroups = new Set<string>();
  const append = (service: HomeMasterService) => {
    if (selected.length >= limit || selectedIds.has(service.masterServiceId)) return;
    selected.push(service);
    selectedIds.add(service.masterServiceId);
    selectedGroups.add(service.serviceGroupId);
  };
  for (const service of services.filter(item => Boolean(item.description?.trim()))) {
    if (!selectedGroups.has(service.serviceGroupId)) append(service);
  }
  services.filter(service => Boolean(service.description?.trim())).forEach(append);
  services.forEach(append);
  return selected;
}

function bookingTitle(booking: HomeActiveBooking | null): string {
  return booking?.serviceName ?? booking?.issueSummary ?? customerExperienceCopy.home.fallbacks.activeService;
}

function bookingTime(booking: HomeActiveBooking | null): string {
  if (!booking) return customerExperienceCopy.home.fallbacks.activeTime;
  const date = booking.scheduledDate ?? booking.preferredDate;
  const slot = booking.scheduledTimeWindow ?? booking.preferredTimeWindow;
  return [friendlyVisitDay(date), slot].filter(Boolean).join(", ") || customerExperienceCopy.home.fallbacks.activeTime;
}

function friendlyVisitDay(value: string | null): string | null {
  if (!value) return null;
  const isoDay = value.match(/^\d{4}-\d{2}-\d{2}/)?.[0];
  const visit = isoDay ? new Date(`${isoDay}T00:00:00`) : new Date(value);
  if (Number.isNaN(visit.getTime())) return value;
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const target = new Date(visit.getFullYear(), visit.getMonth(), visit.getDate());
  const daysAhead = Math.round((target.getTime() - today.getTime()) / 86_400_000);
  if (daysAhead === 0) return "Today";
  if (daysAhead === 1) return "Tomorrow";
  return target.toLocaleDateString("en-IN", { weekday: "long" });
}

function bookingProvider(booking: HomeActiveBooking | null): string {
  return booking?.provider?.name
    ?? booking?.providerName
    ?? booking?.technician?.name
    ?? customerExperienceCopy.home.fallbacks.activeProvider;
}

function SurfaceCard({ children, style }: { children: React.ReactNode; style?: object }) {
  const { theme } = useTheme();
  return (
    <View
      style={[
        {
          backgroundColor: theme.fuvay.surfaces.panel,
          borderWidth: 1,
          borderColor: theme.fuvay.surfaces.edge,
          borderRadius: 20,
          shadowColor: theme.fuvay.softShadow.color,
          shadowOffset: { width: 0, height: theme.fuvay.softShadow.offsetY },
          shadowRadius: theme.fuvay.softShadow.radius,
          shadowOpacity: theme.fuvay.softShadow.opacity,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}

/** Exact reference panel treatment for cards whose content must clip without
 * clipping the surrounding soft shadow. The source canvas uses a solid panel
 * face here—not the header gradient or ambient glow. */
function PanelSurfaceCard({ children, style, clipped = false }: { children: React.ReactNode; style?: object; clipped?: boolean }) {
  const { theme } = useTheme();
  const t = theme.fuvay;
  return (
    <View
      style={{
        borderRadius: 20,
        shadowColor: t.softShadow.color,
        shadowOffset: { width: 0, height: t.softShadow.offsetY },
        shadowRadius: t.softShadow.radius,
        shadowOpacity: t.softShadow.opacity,
        elevation: t.isDark ? 5 : 0,
      }}
    >
      <View
        style={[
          {
            backgroundColor: t.surfaces.panel,
            borderWidth: 1,
            borderColor: t.surfaces.edge,
            borderRadius: 20,
            overflow: clipped ? "hidden" : "visible",
          },
          style,
        ]}
      >
        {children}
      </View>
    </View>
  );
}

function Meta({ children, color }: { children: string; color?: string }) {
  const { theme } = useTheme();
  return <AppText variant="metaLabel" style={{ color: color ?? theme.fuvay.surfaces.faint }}>{children}</AppText>;
}

function SectionHeading({ title, subtitle, meta }: { title: string; subtitle?: string; meta?: string }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
      <View style={{ flex: 1, gap: 3 }}>
        <AppText variant="headingSmall" style={{ color: theme.fuvay.surfaces.text }}>{title}</AppText>
        {subtitle ? <AppText variant="bodySmall" style={{ color: theme.fuvay.surfaces.sub }}>{subtitle}</AppText> : null}
      </View>
      {meta ? <Meta>{meta}</Meta> : null}
    </View>
  );
}

function RoundButton({ label, children, onPress, size = 46, shape = "circle" }: {
  label: string;
  children: React.ReactNode;
  onPress: () => void;
  size?: number;
  shape?: "circle" | "squircle";
}) {
  const { theme } = useTheme();
  const radius = shape === "circle" ? size / 2 : size * 0.3;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      hitSlop={8}
      style={({ pressed }) => ({ opacity: pressed ? 0.76 : 1 })}
    >
      <FuvayTile style={{ width: size, height: size }} borderRadius={radius}>{children}</FuvayTile>
    </Pressable>
  );
}

function ServiceTile({ title, icon, accent, columns, onPress }: { title: string; icon: AppLucideName; accent: FuvayAccentKey; columns: 3 | 4; onPress: () => void }) {
  const { theme } = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Book ${title}`}
      onPress={onPress}
      style={({ pressed }) => ({ width: columns === 3 ? "30%" : "22%", alignItems: "center", gap: 7, opacity: pressed ? 0.74 : 1 })}
    >
      <FuvayTile style={{ width: "100%", aspectRatio: 1 }} borderRadius={22}>
        <AppLucideIcon name={icon} size={22} color={accentFor(theme.fuvay, accent)} strokeWidth={1.75} />
      </FuvayTile>
      <AppText numberOfLines={2} variant="caption" align="center" style={{ color: theme.fuvay.surfaces.sub, fontSize: 9.5, lineHeight: 12 }}>
        {title}
      </AppText>
    </Pressable>
  );
}

function Header({
  customerName,
  location,
  unreadCount,
  nextBooking,
  searchValue,
  quickServices,
  quickMasterServices,
  quickIssues,
  onSearch,
  onProfile,
  onLocation,
  onNotifications,
  onNextBooking,
  onService,
  onMasterService,
}: {
  customerName: string;
  location: string;
  unreadCount: number;
  nextBooking: HomeActiveBooking | null;
  searchValue: string;
  quickServices: HomeServiceGroup[];
  quickMasterServices: HomeMasterService[];
  quickIssues: HomeQuickIssue[];
  onSearch: (value: string) => void;
  onProfile: () => void;
  onLocation: () => void;
  onNotifications: () => void;
  onNextBooking: () => void;
  onService: (group: HomeServiceGroup) => void;
  onMasterService: (service: HomeMasterService) => void;
}) {
  const { theme } = useTheme();
  const t = theme.fuvay;
  const copy = customerExperienceCopy.home;
  const allQuickItems = [
    ...quickServices.map(group => ({
      key: `group-${group.serviceGroupId}`,
      title: group.name,
      onPress: () => onService(group),
    })),
    ...quickMasterServices
      .filter(service => !quickServices.some(group => group.name.trim().toLocaleLowerCase() === service.name.trim().toLocaleLowerCase()))
      .map(service => ({
        key: `service-${service.masterServiceId}`,
        title: service.name,
        onPress: () => onMasterService(service),
      })),
  ];
  const quickColumns: 3 | 4 = allQuickItems.length < 7 ? 3 : 4;
  const quickItems = allQuickItems.slice(0, quickColumns === 3 ? 6 : 8);
  const orderedSearchIssues = [...quickIssues].sort((a, b) =>
    Number(!/\bac\b.*not cooling/i.test(a.label)) - Number(!/\bac\b.*not cooling/i.test(b.label)),
  );
  const searchSuggestions = [
    ...orderedSearchIssues.map(issue => `“${issue.label}”`),
    ...allQuickItems.map(item => `“${item.title}”`),
  ].filter((item, index, all) => all.indexOf(item) === index).slice(0, 7);
  return (
    <LinearGradient
      colors={t.surfaces.headerGradient as [string, string, string]}
      start={fuvayGradientGeometry.css170Start}
      end={fuvayGradientGeometry.css170End}
      style={{ paddingHorizontal: 18, paddingTop: 18, paddingBottom: 24, gap: 18, overflow: "hidden" }}
    >
      <AmbientGlow />
      <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
        <RoundButton label="Open profile" onPress={onProfile} shape="squircle">
          <AppLucideIcon name="person-outline" size={18} color={t.tile.icon} strokeWidth={1.75} />
        </RoundButton>
        <Pressable accessibilityRole="button" accessibilityLabel={`Change service location, currently ${location}`} onPress={onLocation} style={{ flex: 1, minWidth: 0, gap: 2 }}>
          <AppText numberOfLines={1} variant="bodyStrong" style={{ color: t.surfaces.text, fontSize: 13.5 }}>{customerName}</AppText>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 5 }}>
            <AppLucideIcon name="map-marker-path" size={11} color={t.surfaces.sub} strokeWidth={2} />
            <AppText numberOfLines={1} variant="caption" style={{ flex: 1, color: t.surfaces.sub }}>{location}</AppText>
          </View>
        </Pressable>
        <View>
          <RoundButton label={`Notifications, ${unreadCount} unread`} onPress={onNotifications}>
            <AppLucideIcon name="bell-outline" size={17} color={t.tile.icon} strokeWidth={1.75} />
          </RoundButton>
          {unreadCount > 0 ? <View style={{ position: "absolute", right: 9, top: 9, width: 7, height: 7, borderRadius: 4, backgroundColor: t.accents.a2 }} /> : null}
        </View>
      </View>

      <View style={{ gap: 12 }}>
        <AppText variant="displayMedium" style={{ color: t.surfaces.text }}>{copy.headline}</AppText>
        <Pressable accessibilityRole="button" accessibilityLabel="Open next visit" onPress={onNextBooking} disabled={!nextBooking}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 10, paddingHorizontal: 14, borderRadius: 16, backgroundColor: t.surfaces.hexFill }}>
            <View style={{ width: 34, height: 34, borderRadius: 17, alignItems: "center", justifyContent: "center", backgroundColor: theme.colors.mediaScrim }}>
              <AppLucideIcon name="calendar-clock" size={16} color={t.ink(t.surfaces.hexFill)} strokeWidth={2} />
            </View>
            <View style={{ flex: 1, gap: 1 }}>
              <Meta color={t.ink(t.surfaces.hexFill)}>{copy.nextVisit}</Meta>
              <AppText variant="bodyStrong" style={{ color: t.ink(t.surfaces.hexFill), fontSize: 13.5 }}>{bookingTime(nextBooking)}</AppText>
            </View>
            <AppLucideIcon name="chevron-right" size={16} color={t.ink(t.surfaces.hexFill)} strokeWidth={2} />
          </View>
        </Pressable>
      </View>

      <ServiceSearch
        value={searchValue}
        onChangeText={onSearch}
        placeholder={copy.searchPlaceholder}
        suggestions={searchSuggestions}
        suggestionPrefix="Try "
        suggestionSuffix=""
        appearance="fuvay"
        containerStyle={{ minHeight: 58, paddingLeft: 14, paddingRight: 7, borderRadius: 18 }}
        rightAccessory={(
          <View style={{ width: 44, height: 44, borderRadius: 14, backgroundColor: t.accents.a3, alignItems: "center", justifyContent: "center" }}>
            <AppLucideIcon name="mic" size={16} color={t.ink(t.accents.a3)} strokeWidth={2} />
          </View>
        )}
      />

      <View style={{ flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", rowGap: 14 }}>
        {quickItems.map((item, index) => (
          <ServiceTile key={item.key} title={item.title} icon={iconFor(item.title)} accent={rotatingAccents[index % rotatingAccents.length]} columns={quickColumns} onPress={item.onPress} />
        ))}
      </View>
    </LinearGradient>
  );
}

function OfferCard({ campaign, onPress }: { campaign?: HomeCampaign; onPress: () => void }) {
  const { theme } = useTheme();
  const t = theme.fuvay;
  if (!campaign) return null;
  return (
    <SurfaceCard style={{ overflow: "hidden", flexDirection: "row", minHeight: 184 }}>
      <Image source={{ uri: campaign.imageUrl }} resizeMode="cover" style={{ width: "45%", minHeight: 184 }} />
      <View style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 3, backgroundColor: t.accents.a1 }} />
      <View style={{ flex: 1, padding: 16, gap: 8 }}>
        <Meta color={t.accents.a1}>{campaign.badge}</Meta>
        <AppText variant="headingSmall" style={{ color: t.surfaces.text, lineHeight: 20 }}>{campaign.title}</AppText>
        <View style={{ width: 28, height: 2, backgroundColor: t.accents.a1 }} />
        <AppText variant="caption" style={{ color: t.surfaces.sub, lineHeight: 16 }}>{campaign.offerText ?? campaign.subtitle}</AppText>
        <Pressable accessibilityRole="button" accessibilityLabel={campaign.actionLabel} onPress={onPress} style={{ alignSelf: "flex-start", minHeight: 40, paddingHorizontal: 16, borderRadius: 20, backgroundColor: t.accents.a1, alignItems: "center", justifyContent: "center", marginTop: 4 }}>
          <AppText variant="labelStrong" style={{ color: t.ink(t.accents.a1) }}>{campaign.actionLabel}</AppText>
        </Pressable>
      </View>
    </SurfaceCard>
  );
}

function LiveBookingCard({ booking, onPress }: { booking: HomeActiveBooking; onPress: () => void }) {
  const { theme } = useTheme();
  const t = theme.fuvay;
  const stage = /complete|closed/i.test(booking.status) ? 3 : /done|repaired/i.test(booking.status) ? 2 : /progress|work.?started|inspection/i.test(booking.status) ? 1 : 0;
  const stageAccents = [t.accents.a2, t.accents.a1, t.accents.a3, t.accents.a4] as const;
  const stageAccent = stageAccents[stage];
  const statusLabels = ["ENGINEER EN ROUTE", "WORK STARTED", "WORK COMPLETE", "COMPLETED"] as const;
  const stageNotes = [
    "Your professional is on the way.",
    "Inspection or service work is in progress.",
    "Work is complete and final checks are underway.",
    "Service completed. Your invoice and warranty are available.",
  ] as const;
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={`${bookingTitle(booking)}, provider ${bookingProvider(booking)}`} onPress={onPress}>
      <PanelSurfaceCard style={{ padding: 18, gap: 16 }}>
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 9 }}>
            <LiveStatusDot color={stageAccent} />
            <Meta>{customerExperienceCopy.home.liveBooking}</Meta>
          </View>
          <View style={{ paddingVertical: 6, paddingHorizontal: 11, borderRadius: 99, backgroundColor: t.soft(stageAccent) }}>
            <Meta color={stageAccent}>{statusLabels[stage]}</Meta>
          </View>
        </View>
        <View style={{ flexDirection: "row", gap: 13, alignItems: "flex-start" }}>
          <Image source={serviceArtwork(booking.serviceImageUrl, bookingTitle(booking))} style={{ width: 58, height: 58, borderRadius: 18 }} resizeMode="cover" />
          <View style={{ flex: 1, gap: 5 }}>
            <AppText variant="headingSmall" style={{ color: t.surfaces.text }}>{bookingTitle(booking)}</AppText>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 7 }}>
              <AppLucideIcon name="calendar-clock" size={12} color={t.surfaces.sub} />
              <AppText variant="label" style={{ color: t.surfaces.sub }}>{bookingTime(booking)}</AppText>
            </View>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 7 }}>
              <AppLucideIcon name="person-outline" size={12} color={t.surfaces.faint} />
              <AppText variant="label" style={{ color: t.surfaces.faint }}>{bookingProvider(booking)}</AppText>
            </View>
          </View>
        </View>
        <View style={{ height: 1, backgroundColor: t.surfaces.rule }} />
        <View style={{ position: "relative", paddingTop: 4 }}>
          <View style={{ position: "absolute", top: 21, left: 19, right: 19, height: 2, backgroundColor: t.surfaces.rule }}>
            <View style={{ width: `${(stage / 3) * 100}%`, height: 2, borderRadius: 2, backgroundColor: stageAccent }} />
          </View>
          <View style={{ flexDirection: "row" }}>
            {reference.liveStages.map((item, index) => {
              const done = index <= stage;
              return (
                <View key={item.title} style={{ flex: 1, alignItems: "center", gap: 8 }}>
                  <LiveStageMarker icon={item.icon} done={done} current={index === stage} accent={stageAccent} />
                  <AppText variant="caption" align="center" style={{ color: done ? stageAccent : t.surfaces.faint, fontSize: 9.5 }}>{item.title}</AppText>
                </View>
              );
            })}
          </View>
        </View>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 11, paddingHorizontal: 13, borderRadius: 14, backgroundColor: t.soft(stageAccent) }}>
          <AppLucideIcon name="analytics" size={14} color={stageAccent} />
          <AppText variant="label" style={{ flex: 1, color: t.surfaces.sub }}>{stageNotes[stage]}</AppText>
        </View>
      </PanelSurfaceCard>
    </Pressable>
  );
}

function LiveStatusDot({ color }: { color: string }) {
  const reduced = useReducedMotion();
  const blink = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (reduced) return;
    const animation = Animated.loop(Animated.sequence([
      Animated.timing(blink, { toValue: 0.25, duration: 700, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      Animated.timing(blink, { toValue: 1, duration: 700, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
    ]));
    animation.start();
    return () => animation.stop();
  }, [blink, reduced]);

  return <Animated.View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: color, opacity: reduced ? 1 : blink }} />;
}

function LiveStageMarker({ icon, done, current, accent }: { icon: AppLucideName; done: boolean; current: boolean; accent: string }) {
  const { theme } = useTheme();
  const reduced = useReducedMotion();
  const t = theme.fuvay;
  const pulse = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!current || reduced) {
      pulse.setValue(0);
      return;
    }
    const animation = Animated.loop(Animated.timing(pulse, {
      toValue: 1,
      duration: t.motion.livePulseMs,
      easing: Easing.out(Easing.ease),
      useNativeDriver: true,
    }));
    animation.start();
    return () => animation.stop();
  }, [current, pulse, reduced, t.motion.livePulseMs]);

  return (
    <View style={{ width: 44, height: 44, alignItems: "center", justifyContent: "center" }}>
      {current && !reduced ? (
        <Animated.View
          pointerEvents="none"
          style={{
            position: "absolute",
            width: 36,
            height: 36,
            borderRadius: 18,
            borderWidth: 2,
            borderColor: accent,
            opacity: pulse.interpolate({ inputRange: [0, 0.7, 1], outputRange: [0.55, 0, 0] }),
            transform: [{ scale: pulse.interpolate({ inputRange: [0, 0.7, 1], outputRange: [1, 1.55, 1.55] }) }],
          }}
        />
      ) : null}
      <View style={{ width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center", backgroundColor: done ? accent : t.surfaces.card, borderWidth: 2, borderColor: done ? accent : t.surfaces.rule }}>
        <AppLucideIcon name={icon} size={16} color={done ? t.ink(accent) : t.surfaces.faint} strokeWidth={2} />
      </View>
    </View>
  );
}

function Specialists({ services, onService }: { services: HomeMasterService[]; onService: (service: HomeMasterService) => void }) {
  const { theme } = useTheme();
  const t = theme.fuvay;
  return (
    <LinearGradient colors={t.surfaces.headerGradient as [string, string, string]} start={fuvayGradientGeometry.bottomLeftStart} end={fuvayGradientGeometry.topRightEnd} style={{ borderRadius: 22, overflow: "hidden", paddingVertical: 22, gap: 16 }}>
      <AmbientGlow anchor="bottomLeft" />
      <View style={{ paddingHorizontal: 18, gap: 3 }}>
        <AppText variant="headingSmall" style={{ color: t.surfaces.text, fontSize: 16.5 }}>{customerExperienceCopy.home.sections.specialists}</AppText>
        <AppText variant="label" style={{ color: t.surfaces.sub }}>{customerExperienceCopy.home.specialistSubtitle}</AppText>
      </View>
      <View style={{ flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", rowGap: 18, paddingHorizontal: 18 }}>
        {services.slice(0, 9).map((service, index) => {
          const accent: FuvayAccentKey = index === 2 ? "a1" : index === 8 ? "a4" : "neutral";
          return (
          <Pressable key={service.masterServiceId} accessibilityRole="button" accessibilityLabel={`Browse ${service.name}`} onPress={() => onService(service)} style={({ pressed }) => ({ width: "30%", alignItems: "center", gap: 9, opacity: pressed ? 0.74 : 1 })}>
            <FuvayTile style={{ width: 82, height: 82 }} borderRadius={41} inset={11}>
              <AppLucideIcon name={iconFor(service.name)} size={30} color={accentFor(t, accent)} strokeWidth={1.75} />
            </FuvayTile>
            <AppText numberOfLines={2} variant="labelStrong" align="center" style={{ color: t.surfaces.text, fontSize: 10, lineHeight: 13 }}>{service.name}</AppText>
          </Pressable>
        );})}
      </View>
    </LinearGradient>
  );
}

function ActiveBookingRail({
  bookings,
  total,
  onBooking,
  onCall,
  onCancel,
}: {
  bookings: HomeActiveBooking[];
  total: number;
  onBooking: (booking: HomeActiveBooking) => void;
  onCall: (booking: HomeActiveBooking) => void;
  onCancel: (booking: HomeActiveBooking) => void;
}) {
  const { theme } = useTheme();
  const { width } = useWindowDimensions();
  const t = theme.fuvay;
  const cardWidth = Math.max(272, width - 36);
  if (!bookings.length) return null;
  return (
    <View style={{ gap: 13 }}>
      <SectionHeading title={customerExperienceCopy.home.sections.activeBookings} meta={`${total} UPCOMING`} />
      <ScrollView horizontal showsHorizontalScrollIndicator={false} snapToInterval={cardWidth + 12} decelerationRate="fast" contentContainerStyle={{ gap: 12, paddingHorizontal: 18 }} style={{ marginHorizontal: -18 }}>
        {bookings.map((booking, index) => (
          <SurfaceCard key={booking.bookingId} style={{ width: cardWidth, padding: 14, gap: 9 }}>
            <View style={{ flexDirection: "row", alignItems: "flex-start", gap: 11 }}>
              <RoundButton label={bookingTitle(booking)} onPress={() => onBooking(booking)} shape="squircle">
                <AppLucideIcon name={iconFor(bookingTitle(booking))} size={20} color={[t.accents.a2, t.accents.a4, t.accents.a3][index % 3]} />
              </RoundButton>
              <View style={{ flex: 1, gap: 4, paddingTop: 1 }}>
                <AppText variant="title" style={{ color: t.surfaces.text }}>{bookingTitle(booking)}</AppText>
                <View style={{ alignSelf: "flex-start", paddingVertical: 4, paddingHorizontal: 9, borderRadius: 99, backgroundColor: t.soft(t.accents.a2) }}>
                  <Meta color={t.accents.a2}>{booking.status.replaceAll("_", " ").toUpperCase()}</Meta>
                </View>
              </View>
            </View>
            <View style={{ height: 1, backgroundColor: t.surfaces.rule }} />
            <View style={{ flexDirection: "row", flexWrap: "wrap", rowGap: 7, columnGap: 12 }}>
              <View style={{ width: "100%" }}><InfoRow icon="calendar-outline" text={bookingTime(booking)} /></View>
              {booking.bookingNumber ? <View style={{ flex: 1, minWidth: "42%" }}><InfoRow icon="file-document-check-outline" text={booking.bookingNumber} /></View> : null}
              {booking.issueSummary && booking.issueSummary !== booking.serviceName ? <View style={{ flex: 1, minWidth: "42%" }}><InfoRow icon="tools" text={booking.issueSummary} /></View> : null}
              <View style={{ width: "100%" }}><InfoRow icon="shield-check-outline" text={booking.technician?.name ?? bookingProvider(booking)} faint /></View>
            </View>
            <View style={{ flexDirection: "row", gap: 8 }}>
              {isTechnicianAssigned(booking)
                ? <Pill label="Call" outline onPress={() => onCall(booking)} />
                : <Pill label="Cancel" outline color={t.accents.a1} onPress={() => onCancel(booking)} />}
              <Pill label="Details" onPress={() => onBooking(booking)} />
            </View>
          </SurfaceCard>
        ))}
      </ScrollView>
    </View>
  );
}

function isTechnicianAssigned(booking: HomeActiveBooking): boolean {
  return Boolean(booking.technician);
}

function isLiveBooking(booking: HomeActiveBooking): boolean {
  return isTechnicianAssigned(booking)
    || /^(accepted|assigned|scheduled|on_the_way|in_progress|arrived|work_started)$/i.test(booking.status)
    || /^(accepted|assigned|reassigned)$/i.test(booking.assignmentStatus ?? "");
}

function InfoRow({ icon, text, faint = false }: { icon: AppLucideName; text: string; faint?: boolean }) {
  const { theme } = useTheme();
  const color = faint ? theme.fuvay.surfaces.faint : theme.fuvay.surfaces.sub;
  return <View style={{ flexDirection: "row", alignItems: "center", gap: 7 }}><AppLucideIcon name={icon} size={12} color={color} /><AppText variant="label" style={{ color }}>{text}</AppText></View>;
}

function Pill({ label, onPress, outline = false, color }: { label: string; onPress: () => void; outline?: boolean; color?: string }) {
  const { theme } = useTheme();
  const accent = color ?? theme.fuvay.accents.a2;
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={label} onPress={onPress} style={({ pressed }) => ({ flex: 1, minHeight: 44, paddingHorizontal: 14, borderRadius: 99, borderWidth: outline ? 1 : 0, borderColor: outline ? theme.fuvay.surfaces.edge : "transparent", backgroundColor: outline ? "transparent" : accent, alignItems: "center", justifyContent: "center", opacity: pressed ? 0.76 : 1 })}>
      <AppText variant="labelStrong" style={{ color: outline ? theme.fuvay.surfaces.sub : theme.fuvay.ink(accent) }}>{label}</AppText>
    </Pressable>
  );
}

function Recommendations({ services, onService }: { services: HomeMasterService[]; onService: (service: HomeMasterService) => void }) {
  const { theme } = useTheme();
  const t = theme.fuvay;
  const randomRanks = useRef(new Map<string, number>());
  const recommendations = useMemo(
    () => services
      .map(service => {
        if (!randomRanks.current.has(service.masterServiceId)) randomRanks.current.set(service.masterServiceId, Math.random());
        return service;
      })
      .sort((a, b) => (randomRanks.current.get(a.masterServiceId) ?? 0) - (randomRanks.current.get(b.masterServiceId) ?? 0))
      .slice(0, 3),
    [services],
  );
  return (
    <View style={{ gap: 14 }}>
      <SectionHeading title={customerExperienceCopy.home.sections.recommendations} subtitle={customerExperienceCopy.home.recommendationSubtitle} />
      <View style={{ gap: 11 }}>
        {recommendations.map((service, index) => {
          const accent = accentFor(t, rotatingAccents[index % rotatingAccents.length]);
          return (
            <PanelSurfaceCard key={service.masterServiceId} clipped style={{ flexDirection: "row" }}>
              <Image source={serviceArtwork(service.iconUrl, service.name, index)} style={{ width: 112, minHeight: 154 }} resizeMode="cover" />
              <View style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 3, backgroundColor: accent }} />
              <View style={{ flex: 1, paddingVertical: 13, paddingHorizontal: 14, gap: 7 }}>
                <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}><AppLucideIcon name={iconFor(service.name)} size={12} color={accent} /><Meta color={accent}>{service.serviceGroupName.toUpperCase()}</Meta></View>
                <AppText variant="title" style={{ color: t.surfaces.text }}>{service.name}</AppText>
                <AppText variant="caption" numberOfLines={2} style={{ color: t.surfaces.sub }}>{service.description ?? `Professional ${service.serviceGroupName.toLocaleLowerCase()} service`}</AppText>
                <View style={{ marginTop: 2, flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
                  <AppText variant="caption" style={{ color: t.surfaces.faint }}>Available in your area</AppText>
                  <Pressable accessibilityRole="button" accessibilityLabel={`Book ${service.name}`} onPress={() => onService(service)} style={{ minHeight: 44, paddingHorizontal: 18, borderRadius: 99, backgroundColor: accent, flexDirection: "row", alignItems: "center", gap: 6 }}>
                    <AppText variant="labelStrong" style={{ color: t.ink(accent) }}>Book</AppText><AppLucideIcon name="arrow-right" size={13} color={t.ink(accent)} />
                  </Pressable>
                </View>
              </View>
            </PanelSurfaceCard>
          );
        })}
      </View>
    </View>
  );
}

function CategoryGrid({ groups, onService }: { groups: HomeServiceGroup[]; onService: (group: HomeServiceGroup) => void }) {
  const { theme } = useTheme();
  const t = theme.fuvay;
  const visibleGroups = groups.slice(0, 8);
  const columns = visibleGroups.length < 7 ? 3 : 4;
  const rows = Array.from(
    { length: Math.ceil(visibleGroups.length / columns) },
    (_, rowIndex) => visibleGroups.slice(rowIndex * columns, (rowIndex + 1) * columns),
  );

  return (
    <View style={{ gap: 14 }}>
      <SectionHeading title={customerExperienceCopy.home.sections.categories} />
      <View style={{ gap: 10 }}>
        {rows.map((row, rowIndex) => (
          <View key={`category-row-${rowIndex}`} style={{ flexDirection: "row", justifyContent: "space-between" }}>
            {row.map((group, columnIndex) => {
              const index = rowIndex * columns + columnIndex;
              const accent = rotatingAccents[index % rotatingAccents.length];
              return (
                <FuvaySquircleTile
                  key={group.serviceGroupId}
                  icon={iconFor(group.name)}
                  label={group.name}
                  accent={accentFor(t, accent)}
                  onPress={() => onService(group)}
                />
              );
            })}
            {Array.from({ length: columns - row.length }, (_, spacerIndex) => (
              <View key={`category-spacer-${spacerIndex}`} style={{ width: "22%" }} />
            ))}
          </View>
        ))}
      </View>
    </View>
  );
}

function Spotlight({ campaigns, onCampaign }: { campaigns: HomeCampaign[]; onCampaign: (campaign: HomeCampaign) => void }) {
  const { theme } = useTheme();
  const t = theme.fuvay;
  const [main, ...sides] = campaigns;
  if (!main) return null;
  return (
    <View style={{ gap: 14 }}>
      <SectionHeading title="Spotlight" />
      <View style={{ gap: 12 }}>
        <SurfaceCard style={{ overflow: "hidden" }}>
          <Image source={{ uri: main.imageUrl }} style={{ width: "100%", height: 172 }} resizeMode="cover" />
          <View style={{ position: "absolute", left: 12, top: 12, paddingVertical: 5, paddingHorizontal: 11, borderRadius: 99, backgroundColor: t.accents.a4 }}><Meta color={t.ink(t.accents.a4)}>{main.badge}</Meta></View>
          <View style={{ padding: 15, gap: 9 }}>
            <AppText variant="headingSmall" style={{ color: t.surfaces.text, fontSize: 18 }}>{main.title}</AppText>
            <AppText variant="bodySmall" style={{ color: t.surfaces.sub }}>{main.subtitle}</AppText>
            {main.offerText ? <InfoRow icon="sparkles" text={main.offerText} /> : null}
            <Pill label={main.actionLabel} color={t.accents.a4} onPress={() => onCampaign(main)} />
          </View>
        </SurfaceCard>
        {sides.slice(0, 3).map((item, index) => (
          <SurfaceCard key={item.campaignId} style={{ overflow: "hidden", flexDirection: "row", minHeight: 118 }}>
            <Image source={{ uri: item.imageUrl }} style={{ width: 108 }} resizeMode="cover" />
            <View style={{ flex: 1, paddingVertical: 12, paddingHorizontal: 13, gap: 6 }}>
              <View style={{ alignSelf: "flex-start", paddingVertical: 3, paddingHorizontal: 9, borderRadius: 99, backgroundColor: t.soft(accentFor(t, rotatingAccents[index])) }}><Meta color={accentFor(t, rotatingAccents[index])}>{item.badge}</Meta></View>
              <AppText variant="bodyStrong" style={{ color: t.surfaces.text }}>{item.title}</AppText>
              <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 }}><AppText variant="caption" numberOfLines={1} style={{ flex: 1, color: t.surfaces.faint }}>{item.offerText ?? item.subtitle}</AppText><Pressable accessibilityRole="button" accessibilityLabel={`${item.actionLabel} ${item.title}`} onPress={() => onCampaign(item)} style={{ minHeight: 36, paddingHorizontal: 16, borderRadius: 99, borderWidth: 1, borderColor: accentFor(t, rotatingAccents[index]), justifyContent: "center" }}><AppText variant="labelStrong" style={{ color: accentFor(t, rotatingAccents[index]) }}>{item.actionLabel}</AppText></Pressable></View>
            </View>
          </SurfaceCard>
        ))}
      </View>
    </View>
  );
}

function FestiveBanner({ campaign, onPress }: { campaign?: HomeCampaign; onPress: () => void }) {
  const { theme } = useTheme();
  const t = theme.fuvay;
  if (!campaign) return null;
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={`${campaign.actionLabel}: ${campaign.title}`} onPress={onPress}>
      <ImageBackground source={{ uri: campaign.imageUrl }} resizeMode="cover" imageStyle={{ borderRadius: 22 }} style={{ minHeight: 236, borderRadius: 22, overflow: "hidden", justifyContent: "flex-end" }}>
        <LinearGradient colors={[theme.colors.mediaScrim, theme.colors.mediaScrimStrong, theme.colors.campaignBadgeScrim]} style={{ position: "absolute", inset: 0 }} />
        <View style={{ position: "absolute", right: 16, top: 16, width: 74, height: 84, alignItems: "center", justifyContent: "center" }}>
          <Svg width={74} height={84} viewBox="0 0 74 84" style={{ position: "absolute" }}><Polygon points="37,0 74,21 74,63 37,84 0,63 0,21" fill={t.surfaces.hexFill} /></Svg>
          <AppText numberOfLines={2} align="center" variant="labelStrong" style={{ color: t.ink(t.surfaces.hexFill) }}>{campaign.offerText ?? campaign.badge}</AppText>
        </View>
        <View style={{ padding: 18, gap: 10 }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}><View style={{ width: 18, height: 1, backgroundColor: t.surfaces.hexFill }} /><Meta color={t.surfaces.hexFill}>{campaign.badge}</Meta></View>
          <AppText variant="headingLarge" style={{ color: theme.colors.mediaForeground }}>{campaign.title}</AppText>
          <AppText variant="bodySmall" style={{ color: theme.colors.mediaForegroundMuted }}>{campaign.subtitle}</AppText>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 12, marginTop: 4 }}>
            <View style={{ minHeight: 44, paddingHorizontal: 20, borderRadius: 99, backgroundColor: theme.colors.mediaForeground, flexDirection: "row", alignItems: "center", gap: 8 }}><AppText variant="button" style={{ color: t.ink(theme.colors.mediaForeground) }}>{campaign.actionLabel}</AppText><AppLucideIcon name="arrow-right" size={15} color={t.ink(theme.colors.mediaForeground)} /></View>
          </View>
        </View>
      </ImageBackground>
    </Pressable>
  );
}

function PopularServices({ services, onService }: { services: HomeMasterService[]; onService: (service: HomeMasterService) => void }) {
  const { theme } = useTheme();
  const t = theme.fuvay;
  const popularServices = useMemo(() => selectDiverseServices(services, 6), [services]);
  return (
    <View style={{ gap: 14 }}>
      <SectionHeading title="Popular services" />
      <View style={{ gap: 11 }}>
        {popularServices.map((service, index) => {
          const accent = accentFor(t, rotatingAccents[index % rotatingAccents.length]);
          return (
            <FuvayServiceCard
              key={service.masterServiceId}
              icon={iconFor(service.name)}
              title={service.name}
              description={service.description ?? service.serviceGroupName}
              meta={service.serviceGroupName.toUpperCase()}
              accent={accent}
              onPress={() => onService(service)}
            />
        );})}
      </View>
    </View>
  );
}

function AssistantCard({ onPress }: { onPress: (prompt?: string) => void }) {
  const { theme } = useTheme();
  const t = theme.fuvay;
  const copy = customerExperienceCopy.home.assistant;
  return (
    <LinearGradient colors={[t.accents.a2, t.accents.a4, t.surfaces.edge]} style={{ padding: 2, borderRadius: 24 }}>
      <LinearGradient colors={t.surfaces.headerGradient as [string, string, string]} start={fuvayGradientGeometry.css170Start} end={fuvayGradientGeometry.css170End} style={{ borderRadius: 22, paddingHorizontal: 18, paddingTop: 20, paddingBottom: 18, gap: 16, overflow: "hidden" }}>
        <AmbientGlow />
        <View style={{ position: "absolute", left: 18, top: 0, width: 46, height: 3, backgroundColor: t.accents.a2 }} />
        <View style={{ flexDirection: "row", alignItems: "flex-start", gap: 14 }}>
          <View style={{ width: 58, height: 66, alignItems: "center", justifyContent: "center" }}><Svg width={58} height={66} viewBox="0 0 58 66" style={{ position: "absolute" }}><Polygon points="29,0 58,16.5 58,49.5 29,66 0,49.5 0,16.5" fill={t.surfaces.hexPanel} /></Svg><AppLucideIcon name="sparkles" size={24} color={t.accents.a2} /></View>
          <View style={{ flex: 1, gap: 6 }}><Meta color={t.accents.a2}>{copy.eyebrow}</Meta><AppText variant="headingMedium" style={{ color: t.surfaces.text }}>{copy.title}</AppText><AppText variant="label" style={{ color: t.surfaces.sub, lineHeight: 16 }}>{copy.subtitle}</AppText></View>
        </View>
        <View style={{ gap: 8 }}>
          {copy.prompts.map((prompt, index) => <Pressable key={prompt} accessibilityRole="button" accessibilityLabel={prompt} onPress={() => onPress(prompt)} style={({ pressed }) => ({ minHeight: 44, paddingHorizontal: 14, borderRadius: 14, backgroundColor: t.surfaces.card, borderWidth: 1, borderColor: pressed ? t.accents.a2 : t.surfaces.edge, flexDirection: "row", alignItems: "center", gap: 10 })}><AppLucideIcon name={["air-conditioner", "water-circle", "lightning-bolt-outline"][index] as AppLucideName} size={14} color={t.accents.a2} /><AppText variant="bodySmall" style={{ flex: 1, color: t.surfaces.sub }}>“{prompt}”</AppText><AppLucideIcon name="arrow-back" size={13} color={t.surfaces.faint} /></Pressable>)}
        </View>
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 }}><Meta>{copy.responseTime}</Meta><Pressable accessibilityRole="button" accessibilityLabel="Ask Fuvay for help choosing a service" onPress={() => onPress()} style={{ minHeight: 44, paddingHorizontal: 22, borderRadius: 99, backgroundColor: t.accents.a2, flexDirection: "row", alignItems: "center", gap: 8 }}><AppText variant="button" style={{ color: t.ink(t.accents.a2) }}>{copy.action}</AppText><AppLucideIcon name="arrow-right" size={15} color={t.ink(t.accents.a2)} /></Pressable></View>
      </LinearGradient>
    </LinearGradient>
  );
}

export interface FuvayHomeV2Props {
  customerName: string;
  location: string;
  unreadCount: number;
  searchValue: string;
  serviceGroups: HomeServiceGroup[];
  masterServices: HomeMasterService[];
  quickIssues: HomeQuickIssue[];
  activeBookings: HomeActiveBooking[];
  activeBookingTotal: number;
  heroCampaign?: HomeCampaign;
  spotlightCampaigns: HomeCampaign[];
  bannerCampaign?: HomeCampaign;
  onSearch: (value: string) => void;
  onProfile: () => void;
  onLocation: () => void;
  onNotifications: () => void;
  onBooking: (booking: HomeActiveBooking) => void;
  onCallBooking: (booking: HomeActiveBooking) => void;
  onCancelBooking: (booking: HomeActiveBooking) => void;
  onServiceGroup: (group: HomeServiceGroup) => void;
  onMasterService: (service: HomeMasterService) => void;
  onCampaign: (campaign: HomeCampaign) => void;
  onAssistant: (prompt?: string) => void;
}

export function FuvayHomeV2(props: FuvayHomeV2Props) {
  const { theme } = useTheme();
  const active = useMemo(
    () => props.activeBookings.find(isLiveBooking) ?? props.activeBookings[0] ?? null,
    [props.activeBookings],
  );
  const moreBookings = useMemo(
    () => props.activeBookings.filter(booking => booking.bookingId !== active?.bookingId),
    [active?.bookingId, props.activeBookings],
  );
  return (
    <View style={{ backgroundColor: theme.fuvay.surfaces.shell }}>
      <Header
        customerName={props.customerName}
        location={props.location}
        unreadCount={props.unreadCount}
        nextBooking={active}
        searchValue={props.searchValue}
        quickServices={props.serviceGroups}
        quickMasterServices={props.masterServices}
        quickIssues={props.quickIssues}
        onSearch={props.onSearch}
        onProfile={props.onProfile}
        onLocation={props.onLocation}
        onNotifications={props.onNotifications}
        onNextBooking={() => active ? props.onBooking(active) : undefined}
        onService={props.onServiceGroup}
        onMasterService={props.onMasterService}
      />
      <View style={{ paddingHorizontal: 18, paddingTop: 20, paddingBottom: 8, gap: 26 }}>
        <OfferCard campaign={props.heroCampaign} onPress={() => props.heroCampaign ? props.onCampaign(props.heroCampaign) : props.onAssistant()} />
        {active ? <LiveBookingCard booking={active} onPress={() => props.onBooking(active)} /> : null}
        <Specialists services={props.masterServices} onService={props.onMasterService} />
        <ActiveBookingRail bookings={moreBookings} total={Math.max(moreBookings.length, props.activeBookingTotal - (active ? 1 : 0))} onBooking={props.onBooking} onCall={props.onCallBooking} onCancel={props.onCancelBooking} />
        <Recommendations services={props.masterServices} onService={props.onMasterService} />
        <CategoryGrid groups={props.serviceGroups} onService={props.onServiceGroup} />
        <Spotlight campaigns={props.spotlightCampaigns} onCampaign={props.onCampaign} />
        <FestiveBanner campaign={props.bannerCampaign} onPress={() => props.bannerCampaign ? props.onCampaign(props.bannerCampaign) : props.onAssistant()} />
        <PopularServices services={props.masterServices} onService={props.onMasterService} />
        <AssistantCard onPress={props.onAssistant} />
      </View>
    </View>
  );
}
