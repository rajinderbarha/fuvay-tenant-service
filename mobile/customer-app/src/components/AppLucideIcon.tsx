import React from "react";
import AirVent from "lucide-react-native/dist/esm/icons/air-vent";
import ArrowLeft from "lucide-react-native/dist/esm/icons/arrow-left";
import ArrowRight from "lucide-react-native/dist/esm/icons/arrow-right";
import Bell from "lucide-react-native/dist/esm/icons/bell";
import BellDot from "lucide-react-native/dist/esm/icons/bell-dot";
import Boxes from "lucide-react-native/dist/esm/icons/boxes";
import Bug from "lucide-react-native/dist/esm/icons/bug";
import CalendarDays from "lucide-react-native/dist/esm/icons/calendar-days";
import CalendarClock from "lucide-react-native/dist/esm/icons/calendar-clock";
import CarFront from "lucide-react-native/dist/esm/icons/car-front";
import ChartNoAxesCombined from "lucide-react-native/dist/esm/icons/chart-no-axes-combined";
import Check from "lucide-react-native/dist/esm/icons/check";
import ChevronDown from "lucide-react-native/dist/esm/icons/chevron-down";
import ChevronLeft from "lucide-react-native/dist/esm/icons/chevron-left";
import ChevronRight from "lucide-react-native/dist/esm/icons/chevron-right";
import Circle from "lucide-react-native/dist/esm/icons/circle";
import CircleArrowRight from "lucide-react-native/dist/esm/icons/circle-arrow-right";
import Code2 from "lucide-react-native/dist/esm/icons/code-xml";
import CookingPot from "lucide-react-native/dist/esm/icons/cooking-pot";
import Droplets from "lucide-react-native/dist/esm/icons/droplets";
import FileCheck2 from "lucide-react-native/dist/esm/icons/file-check-2";
import Flame from "lucide-react-native/dist/esm/icons/flame";
import Globe2 from "lucide-react-native/dist/esm/icons/globe";
import Grid2X2 from "lucide-react-native/dist/esm/icons/grid-2x2";
import Hammer from "lucide-react-native/dist/esm/icons/hammer";
import Headphones from "lucide-react-native/dist/esm/icons/headphones";
import House from "lucide-react-native/dist/esm/icons/house";
import HousePlug from "lucide-react-native/dist/esm/icons/house-plug";
import LifeBuoy from "lucide-react-native/dist/esm/icons/life-buoy";
import MapPin from "lucide-react-native/dist/esm/icons/map-pin";
import Mic from "lucide-react-native/dist/esm/icons/mic";
import Microwave from "lucide-react-native/dist/esm/icons/microwave";
import Paintbrush from "lucide-react-native/dist/esm/icons/paintbrush";
import Pencil from "lucide-react-native/dist/esm/icons/pencil";
import Phone from "lucide-react-native/dist/esm/icons/phone";
import Plus from "lucide-react-native/dist/esm/icons/plus";
import MessageCircle from "lucide-react-native/dist/esm/icons/message-circle";
import Refrigerator from "lucide-react-native/dist/esm/icons/refrigerator";
import Search from "lucide-react-native/dist/esm/icons/search";
import ShieldCheck from "lucide-react-native/dist/esm/icons/shield-check";
import Smartphone from "lucide-react-native/dist/esm/icons/smartphone";
import Sparkles from "lucide-react-native/dist/esm/icons/sparkles";
import SprayCan from "lucide-react-native/dist/esm/icons/spray-can";
import UserRound from "lucide-react-native/dist/esm/icons/user-round";
import WashingMachine from "lucide-react-native/dist/esm/icons/washing-machine";
import Wrench from "lucide-react-native/dist/esm/icons/wrench";
import X from "lucide-react-native/dist/esm/icons/x";
import Zap from "lucide-react-native/dist/esm/icons/zap";
import type { LucideIcon } from "lucide-react-native";

import { useTheme } from "../design-system/theme";
import type { IconSizeToken } from "../design-system/tokens";

export type AppLucideName =
  | "account-outline" | "air-conditioner" | "analytics" | "arrow-back"
  | "arrow-forward" | "arrow-forward-circle" | "arrow-right"
  | "bell-badge-outline" | "bell-outline" | "bug-outline"
  | "calendar-clock" | "calendar-outline" | "car-front" | "check"
  | "chevron-back" | "chevron-down" | "chevron-right" | "circle-outline"
  | "close" | "code-slash" | "cube" | "file-document-check-outline"
  | "fridge-outline" | "globe" | "grid" | "headset-outline"
  | "home-lightning-bolt-outline" | "home-outline" | "lifebuoy-outline" | "lightning-bolt-outline"
  | "magnify" | "map-marker-path" | "message-circle" | "mic" | "microwave" | "paintbrush" | "pencil"
  | "person-outline" | "phone" | "phone-portrait" | "pipe-wrench" | "plus"
  | "shield-check-outline" | "shield-star-outline" | "sparkles"
  | "spray-bottle" | "stove" | "tools" | "washing-machine"
  | "water-boiler" | "water-circle";

const ICONS: Record<AppLucideName, LucideIcon> = {
  "account-outline": UserRound,
  "air-conditioner": AirVent,
  analytics: ChartNoAxesCombined,
  "arrow-back": ArrowLeft,
  "arrow-forward": ArrowRight,
  "arrow-forward-circle": CircleArrowRight,
  "arrow-right": ArrowRight,
  "bell-badge-outline": BellDot,
  "bell-outline": Bell,
  "bug-outline": Bug,
  "calendar-clock": CalendarClock,
  "calendar-outline": CalendarDays,
  "car-front": CarFront,
  check: Check,
  "chevron-back": ChevronLeft,
  "chevron-down": ChevronDown,
  "chevron-right": ChevronRight,
  "circle-outline": Circle,
  close: X,
  "code-slash": Code2,
  cube: Boxes,
  "file-document-check-outline": FileCheck2,
  "fridge-outline": Refrigerator,
  globe: Globe2,
  grid: Grid2X2,
  "headset-outline": Headphones,
  "home-lightning-bolt-outline": HousePlug,
  "home-outline": House,
  "lifebuoy-outline": LifeBuoy,
  "lightning-bolt-outline": Zap,
  magnify: Search,
  "map-marker-path": MapPin,
  "message-circle": MessageCircle,
  mic: Mic,
  microwave: Microwave,
  paintbrush: Paintbrush,
  pencil: Pencil,
  "person-outline": UserRound,
  phone: Phone,
  "phone-portrait": Smartphone,
  "pipe-wrench": Wrench,
  plus: Plus,
  "shield-check-outline": ShieldCheck,
  "shield-star-outline": ShieldCheck,
  sparkles: Sparkles,
  "spray-bottle": SprayCan,
  stove: CookingPot,
  tools: Hammer,
  "washing-machine": WashingMachine,
  "water-boiler": Flame,
  "water-circle": Droplets,
};

export interface AppLucideIconProps {
  name: AppLucideName;
  size?: IconSizeToken | number;
  color?: string;
  decorative?: boolean;
  strokeWidth?: number;
}

/** One Lucide icon contract for the customer product. */
export function AppLucideIcon({ name, size = "standard", color, decorative = true, strokeWidth = 1.8 }: AppLucideIconProps) {
  const { theme } = useTheme();
  const Glyph = ICONS[name];
  const px = typeof size === "number" ? size : theme.iconSizes[size];
  return (
    <Glyph
      size={px}
      color={color ?? theme.colors.textPrimary}
      strokeWidth={strokeWidth}
      absoluteStrokeWidth
      accessibilityElementsHidden={decorative}
      importantForAccessibility={decorative ? "no-hide-descendants" : "auto"}
    />
  );
}
