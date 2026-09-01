import type { AppLucideName } from "../components/AppLucideIcon";

export type FuvayAccentKey = "a1" | "a2" | "a3" | "a4" | "neutral";

export interface FuvayReferenceItem {
  title: string;
  icon: AppLucideName;
  accent: FuvayAccentKey;
  searchTerms: readonly string[];
}

const image = (seed: string, width: number, height: number) =>
  `https://picsum.photos/seed/${seed}/${width}/${height}`;

/**
 * Approved Home v2 content inventory. Components consume this single source so
 * screen copy, item count and ordering never drift away from the supplied design.
 * API records are matched to these entries only to provide real navigation.
 */
export const fuvayHomeReferenceContent = {
  quickServices: [
    { title: "AC repair", icon: "air-conditioner", accent: "a2", searchTerms: ["ac", "air", "cool"] },
    { title: "Plumbing", icon: "pipe-wrench", accent: "a3", searchTerms: ["plumb", "pipe", "drain"] },
    { title: "Electrics", icon: "lightning-bolt-outline", accent: "a1", searchTerms: ["electric", "power", "wire"] },
    { title: "Cleaning", icon: "sparkles", accent: "a4", searchTerms: ["clean"] },
    { title: "Chimney", icon: "water-boiler", accent: "a1", searchTerms: ["chimney", "hood"] },
    { title: "Painting", icon: "paintbrush", accent: "a2", searchTerms: ["paint"] },
    { title: "Carpentry", icon: "tools", accent: "a3", searchTerms: ["carpent", "wood"] },
    { title: "Pest control", icon: "bug-outline", accent: "a4", searchTerms: ["pest", "bug"] },
  ] satisfies readonly FuvayReferenceItem[],
  offer: {
    eyebrow: "LIMITED OFFER",
    title: "Flat 30% off AC servicing",
    subtitle: "Offer ends this Sunday.",
    action: "Claim",
    image: image("acoffer", 420, 560),
  },
  liveStages: [
    { title: "On the way", icon: "car-front" },
    { title: "In progress", icon: "tools" },
    { title: "Work done", icon: "check" },
    { title: "Completed", icon: "shield-check-outline" },
  ] satisfies ReadonlyArray<{ title: string; icon: AppLucideName }>,
  specialists: [
    { title: "AC Service", icon: "air-conditioner", accent: "neutral", searchTerms: ["ac", "air"] },
    { title: "Geyser Repair", icon: "water-boiler", accent: "neutral", searchTerms: ["geyser", "heater"] },
    { title: "AC Repair", icon: "air-conditioner", accent: "a1", searchTerms: ["ac", "air"] },
    { title: "Fridge Repair", icon: "fridge-outline", accent: "neutral", searchTerms: ["fridge", "refriger"] },
    { title: "Washing Machine", icon: "washing-machine", accent: "neutral", searchTerms: ["washing"] },
    { title: "RO Service", icon: "water-circle", accent: "neutral", searchTerms: ["ro", "purifier", "water"] },
    { title: "TV Repair", icon: "phone-portrait", accent: "neutral", searchTerms: ["tv", "television"] },
    { title: "Microwave Repair", icon: "microwave", accent: "neutral", searchTerms: ["microwave", "oven"] },
    { title: "Inverter Service", icon: "lightning-bolt-outline", accent: "a4", searchTerms: ["inverter", "power"] },
  ] satisfies readonly FuvayReferenceItem[],
  recommendations: [
    { title: "Annual AC health check", meta: "90 min · covers 2 units", price: "₹899", why: "Your AC was serviced 11 months ago", image: image("acservice", 400, 400), icon: "air-conditioner", accent: "a2", searchTerms: ["ac", "air"] },
    { title: "Water tank cleaning", meta: "2 hours · 1000L", price: "₹1,299", why: "Monsoon season starts next month", image: image("watertank", 400, 400), icon: "water-circle", accent: "a3", searchTerms: ["water", "tank", "clean"] },
    { title: "Geyser descaling", meta: "60 min · any brand", price: "₹649", why: "Booked twice by homes near you", image: image("geyser", 400, 400), icon: "water-boiler", accent: "a1", searchTerms: ["geyser", "heater"] },
  ] satisfies readonly (FuvayReferenceItem & { meta: string; price: string; why: string; image: string })[],
  categories: [
    { title: "Plumbing", icon: "pipe-wrench", accent: "a2", searchTerms: ["plumb", "pipe", "drain"] },
    { title: "Electrics", icon: "lightning-bolt-outline", accent: "a1", searchTerms: ["electric", "power", "wire"] },
    { title: "Heating", icon: "water-circle", accent: "a3", searchTerms: ["heat", "geyser"] },
    { title: "Chimney", icon: "water-boiler", accent: "a4", searchTerms: ["chimney", "hood"] },
    { title: "Cleaning", icon: "sparkles", accent: "a2", searchTerms: ["clean"] },
    { title: "Carpentry", icon: "tools", accent: "a3", searchTerms: ["carpent", "wood"] },
  ] satisfies readonly FuvayReferenceItem[],
  spotlight: {
    main: { tag: "TRENDING NOW", title: "Radiator balancing", description: "Even heat in every room and a lower gas bill.", rating: "4.8", count: "2.1K", image: image("radiator", 640, 420) },
    sides: [
      { tag: "Popular", title: "Deep AC clean", rating: "4.9", image: image("acclean", 320, 240), accent: "a2", searchTerms: ["ac", "clean"] },
      { tag: "Seasonal", title: "Full home wiring audit", rating: "4.7", image: image("wiringaudit", 320, 240), accent: "a3", searchTerms: ["electric", "wire"] },
    ],
  },
  festive: {
    eyebrow: "FESTIVE SEASON",
    title: "Diwali deep clean\nfor a spotless home",
    subtitle: "Full-home clean plus kitchen degrease, done in one visit.",
    offer: "₹500",
    offerLabel: "OFF",
    action: "Grab offer",
    deadline: "ENDS 12 NOV",
    image: image("diwalihome", 780, 620),
  },
  popularServices: [
    { title: "AC deep cleaning", duration: "75 min", rating: "4.8", booked: "48 booked today", image: image("acdeep", 420, 320), icon: "air-conditioner", accent: "a2", searchTerms: ["ac", "clean"] },
    { title: "Plumbing check", duration: "45 min", rating: "4.7", booked: "36 booked today", image: image("plumbcheck", 420, 320), icon: "pipe-wrench", accent: "a1", searchTerms: ["plumb", "pipe"] },
    { title: "Chimney sweep", duration: "90 min", rating: "4.9", booked: "52 booked today", image: image("chimsweep", 420, 320), icon: "water-boiler", accent: "a4", searchTerms: ["chimney"] },
    { title: "House deep clean", duration: "4 hours", rating: "4.6", booked: "29 booked today", image: image("houseclean", 420, 320), icon: "sparkles", accent: "a3", searchTerms: ["house", "clean"] },
  ] satisfies readonly (FuvayReferenceItem & { duration: string; rating: string; booked: string; image: string })[],
} as const;

