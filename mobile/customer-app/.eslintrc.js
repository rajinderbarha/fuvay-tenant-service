// ESLint config focused on the ONE bug class that actually cost us this
// session: Rules-of-Hooks violations that only surface as a red-screen crash
// at runtime, never at typecheck time.
//
// Two real crashes this session were exactly this:
//   * HomeScreen: a `useMemo` placed AFTER early returns -> "Rendered more
//     hooks than during the previous render".
//   * AssistantScreen: an effect whose deps drifted from what it read.
//
// TypeScript cannot see either one. `react-hooks/rules-of-hooks` is set to
// "error" because every violation of it is a real crash, not a style opinion.
module.exports = {
  root: true,
  parser: "@typescript-eslint/parser",
  parserOptions: { ecmaVersion: 2021, sourceType: "module", ecmaFeatures: { jsx: true } },
  plugins: ["@typescript-eslint", "react-hooks"],
  env: { es2021: true, node: true },
  settings: { react: { version: "detect" } },
  ignorePatterns: ["node_modules/", "android/", "ios/", "*.config.js", "babel.config.js"],
  rules: {
    // A violation here is always a runtime crash. Never downgrade this.
    "react-hooks/rules-of-hooks": "error",
    // Stale-closure bugs are real but noisier to retrofit, so this warns:
    // it surfaces them without blocking the build on pre-existing cases.
    "react-hooks/exhaustive-deps": "warn",
  },
};
