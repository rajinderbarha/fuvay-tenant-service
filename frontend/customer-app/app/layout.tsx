import type { Metadata } from "next";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "ServiceOS — Home Services",
  description: "Book trusted home service providers near you.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
