export interface PlatformBranding {
  brand_name: string; short_name: string; tagline: string;
  logo_light_url: string | null; logo_dark_url: string | null;
  brand_mark_url: string | null; favicon_url: string | null;
  apple_touch_icon_url: string | null; email_logo_url: string | null;
  document_logo_url: string | null; social_share_image_url: string | null;
  primary_color: string; accent_color: string; updated_at: string | null;
}

export const DEFAULT_BRANDING: PlatformBranding = {
  brand_name: "Fuvay", short_name: "Fuvay", tagline: "Far Away Is Fare Way",
  logo_light_url: null, logo_dark_url: null, brand_mark_url: null,
  favicon_url: null, apple_touch_icon_url: null, email_logo_url: null,
  document_logo_url: null, social_share_image_url: null,
  primary_color: "#0F6B60", accent_color: "#2F9E8F", updated_at: null,
};

export async function getPlatformBranding(): Promise<PlatformBranding> {
  const api = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const response = await fetch(api + "/v1/public/app-config/branding", { next: { revalidate: 60 } });
    if (!response.ok) return DEFAULT_BRANDING;
    const payload = await response.json();
    return { ...DEFAULT_BRANDING, ...(payload.data ?? payload) };
  } catch {
    return DEFAULT_BRANDING;
  }
}
