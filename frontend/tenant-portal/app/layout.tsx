import type { Metadata } from "next";
import "../styles/globals.css";
export const metadata: Metadata = {
  title: "ServiceOS — Tenant Portal",
  description: "Manage your ServiceOS business",
};
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
