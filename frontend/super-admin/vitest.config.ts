import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    dedupe: ["react", "react-dom"],
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./test-setup.ts"],
    globals: true,
    exclude: ["**/node_modules/**", "**/.next/**"],
  },
});
