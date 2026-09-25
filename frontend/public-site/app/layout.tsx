import type { CSSProperties } from "react";
import type { Metadata } from "next";
import { Footer, Header } from "../components/SiteChrome";
import { getPlatformBranding } from "../lib/branding";
import { siteUrl } from "../lib/site";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const brand = await getPlatformBranding();
  const shareImage = brand.social_share_image_url ?? brand.brand_mark_url ?? "/brand/fuvay-logo.png";
  return {
    metadataBase: new URL(siteUrl),
    title: { default: `${brand.brand_name} | Trusted Home Services in Punjab`, template: `%s | ${brand.brand_name}` },
    description: `Book local home-service providers in Punjab by PIN code through WhatsApp, Instagram or the ${brand.brand_name} customer app.`,
    keywords: ["home services Punjab", "AC repair Punjab", "appliance repair Ludhiana", "ਘਰੇਲੂ ਸੇਵਾਵਾਂ ਪੰਜਾਬ", brand.brand_name],
    alternates: { canonical: "/" },
    icons: { icon: brand.favicon_url ?? "/icon.png", apple: brand.apple_touch_icon_url ?? brand.favicon_url ?? "/apple-icon.png" },
    openGraph: { type: "website", locale: "en_IN", alternateLocale: ["pa_IN", "hi_IN"], siteName: brand.brand_name, images: [{ url: shareImage, alt: `${brand.brand_name} home services` }] },
    twitter: { card: "summary_large_image", images: [shareImage] },
  };
}

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const branding = await getPlatformBranding();
  const brandStyle = {
    "--brand": branding.primary_color, "--accent": branding.accent_color,
    "--green": branding.primary_color, "--green-dark": branding.accent_color,
  } as CSSProperties;
  return <html lang="en-IN" style={brandStyle}><body><Header branding={branding}/><main>{children}</main><Footer branding={branding}/></body></html>;
}
