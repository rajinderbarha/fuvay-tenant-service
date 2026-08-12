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
    // Playwright specs must never be collected by Vitest. The historical
    // root-level reproduction spec otherwise starts browser-test machinery
    // under jsdom and makes `npm test` appear to hang indefinitely.
    exclude: ["**/node_modules/**", "**/.next/**", "**/browser-tests/**", "**/tests-repro-upload.spec.ts"],
  },
});
