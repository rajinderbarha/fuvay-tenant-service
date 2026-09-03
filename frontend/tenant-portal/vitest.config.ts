import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

const workspaceModules = fileURLToPath(new URL("../../node_modules/", import.meta.url));

export default defineConfig({
  resolve: {
    // The workspace test renderer is hoisted at the repository root. Force
    // component imports onto that same React instance; otherwise the portal's
    // nested Next.js React copy produces invalid-hook-call failures.
    alias: {
      react: `${workspaceModules}react`,
      "react-dom": `${workspaceModules}react-dom`,
    },
    dedupe: ["react", "react-dom"],
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./test-setup.ts"],
    globals: true,
    // Keep generated and dependency trees out of component-test discovery.
    exclude: ["**/node_modules/**", "**/.next/**"],
  },
});
