import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./test-setup.ts"],
    globals: true,
    exclude: ["**/node_modules/**", "**/.next/**"],
  },
});
