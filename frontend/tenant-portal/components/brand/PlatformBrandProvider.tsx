"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export interface PlatformBranding {
  brand_name: string; short_name: string; tagline: string;
  logo_light_url: string | null; logo_dark_url: string | null;
  brand_mark_url: string | null; favicon_url: string | null;
  apple_touch_icon_url: string | null; email_logo_url: string | null;
  document_logo_url: string | null; social_share_image_url: string | null;
  primary_color: string; accent_color: string; updated_at: string | null;
}

export const DEFAULT_PLATFORM_BRANDING: PlatformBranding = {
  brand_name: "Fuvay", short_name: "Fuvay", tagline: "Far Away Is Fare Way",
  logo_light_url: null, logo_dark_url: null, brand_mark_url: null,
  favicon_url: null, apple_touch_icon_url: null, email_logo_url: null,
  document_logo_url: null, social_share_image_url: null,
  primary_color: "#0F6B60", accent_color: "#2F9E8F", updated_at: null,
};

const PlatformBrandContext = createContext(DEFAULT_PLATFORM_BRANDING);
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function setIcon(rel: string, url: string | null) {
  const selector = 'link[data-platform-branding="' + rel + '"]';
  let link = document.head.querySelector<HTMLLinkElement>(selector);
  if (!url) { link?.remove(); return; }
  if (!link) { link = document.createElement("link"); link.rel = rel; link.dataset.platformBranding = rel; document.head.appendChild(link); }
  link.href = url;
}

function applyBranding(brand: PlatformBranding, surfaceLabel: string) {
  const root = document.documentElement;
  root.style.setProperty("--brand", brand.primary_color);
  root.style.setProperty("--accent", brand.accent_color);
  root.style.setProperty("--brand-hover", brand.accent_color);
  root.style.setProperty("--brand-muted", "color-mix(in srgb, " + brand.primary_color + " 12%, transparent)");
  root.style.setProperty("--accent-muted", "color-mix(in srgb, " + brand.accent_color + " 12%, transparent)");
  setIcon("icon", brand.favicon_url);
  setIcon("apple-touch-icon", brand.apple_touch_icon_url ?? brand.favicon_url);
  document.title = brand.brand_name + " — " + surfaceLabel;
}

async function loadBranding(signal?: AbortSignal): Promise<PlatformBranding> {
  const response = await fetch(API_BASE + "/v1/public/app-config/branding", { signal });
  if (!response.ok) throw new Error("Branding is unavailable");
  const payload = await response.json();
  return { ...DEFAULT_PLATFORM_BRANDING, ...(payload.data ?? payload) };
}

export function PlatformBrandProvider({ children, surfaceLabel }: { children: ReactNode; surfaceLabel: string }) {
  const [branding, setBranding] = useState(DEFAULT_PLATFORM_BRANDING);
  useEffect(() => {
    const controller = new AbortController();
    const refresh = () => {
      void loadBranding(controller.signal).then(value => { setBranding(value); applyBranding(value, surfaceLabel); })
        .catch(() => applyBranding(DEFAULT_PLATFORM_BRANDING, surfaceLabel));
    };
    refresh();
    window.addEventListener("platform-branding-updated", refresh);
    return () => { controller.abort(); window.removeEventListener("platform-branding-updated", refresh); };
  }, [surfaceLabel]);
  const value = useMemo(() => branding, [branding]);
  return <PlatformBrandContext.Provider value={value}>{children}</PlatformBrandContext.Provider>;
}

export function usePlatformBranding() { return useContext(PlatformBrandContext); }
