module.exports = {
  preset: "jest-expo",
  setupFilesAfterEnv: ["@testing-library/jest-native/extend-expect", "<rootDir>/jest.setup.js"],
  // jest-expo's own transformIgnorePatterns (tuned for the installed Expo SDK)
  // is left untouched rather than overridden — an earlier hand-written pattern
  // here failed to whitelist expo-modules-core and broke every test suite.
  collectCoverageFrom: [
    "src/design-system/**/*.{ts,tsx}",
    "src/config/**/*.{ts,tsx}",
    "src/api/**/*.{ts,tsx}",
    "src/storage/**/*.{ts,tsx}",
    "src/observability/**/*.{ts,tsx}",
    "src/components/**/*.{ts,tsx}",
    "!src/**/*.d.ts",
  ],
};
