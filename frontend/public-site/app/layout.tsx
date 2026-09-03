import type { Metadata } from "next";
import { Footer, Header } from "../components/SiteChrome";
import { siteUrl } from "../lib/site";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: "Fuvay | Trusted Home Services in Punjab", template: "%s | Fuvay" },
  description: "Book local home-service providers in Punjab by PIN code through WhatsApp, Instagram or the Fuvay customer app.",
  keywords: ["home services Punjab", "AC repair Punjab", "appliance repair Ludhiana", "ਘਰੇਲੂ ਸੇਵਾਵਾਂ ਪੰਜਾਬ", "Fuvay"],
  alternates: { canonical: "/" },
  openGraph: { type: "website", locale: "en_IN", alternateLocale: ["pa_IN", "hi_IN"], siteName: "Fuvay", images: [{ url: "/brand/fuvay-logo.png", width: 512, height: 512, alt: "Fuvay home services" }] },
  twitter: { card: "summary_large_image", images: ["/brand/fuvay-logo.png"] },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en-IN"><body><Header/><main>{children}</main><Footer/></body></html>;
}
