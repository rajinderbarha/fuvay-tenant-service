import type { Metadata } from "next";
import "../styles/globals.css";
import "@serviceos/design-system/src/theme.css";
import { ToastViewport } from "@serviceos/design-system";

export const metadata: Metadata = {
  title: "ServiceOS — Super Admin",
  description: "ServiceOS Platform Administration Portal",
};

// Matches the key/logic in hooks/useTheme.ts — the actual theme source of
// truth for this app. The design-system's own ThemeProvider/themeInitScript
// used a *different* localStorage key ("serviceos-theme") that this app
// never wrote to, so its effect ran on every mount/refresh, read nothing,
// defaulted to "system", and silently overwrote whatever theme the user had
// actually chosen — this is why switching to light mode kept reverting to
// dark on refresh/navigation.
const THEME_INIT_SCRIPT = `
(function() {
  try {
    var stored = localStorage.getItem("serviceos-admin-theme");
    var theme = stored === "light" || stored === "dark"
      ? stored
      : (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.documentElement.setAttribute("data-theme", theme);
  } catch (e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Sets data-theme before hydration to avoid flash-of-wrong-theme. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body>
        {children}
        <ToastViewport />
      </body>
    </html>
  );
}
