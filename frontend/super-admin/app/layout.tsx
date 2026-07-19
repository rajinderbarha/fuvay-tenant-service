import type { Metadata } from "next";
import "../styles/globals.css";
import "@serviceos/design-system/src/theme.css";
import { ThemeProvider, ToastViewport, themeInitScript } from "@serviceos/design-system";

export const metadata: Metadata = {
  title: "ServiceOS — Super Admin",
  description: "ServiceOS Platform Administration Portal",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* Sets data-theme before hydration to avoid flash-of-wrong-theme. */}
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body>
        <ThemeProvider>
          {children}
          <ToastViewport />
        </ThemeProvider>
      </body>
    </html>
  );
}
