import type { Metadata } from "next";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "ServiceOS — Super Admin",
  description: "ServiceOS Platform Administration Portal",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
