// Silence noisy RN Animated/NativeModule warnings in test output; add
// project-wide test setup here as it grows.
jest.mock("@react-native-async-storage/async-storage", () =>
  require("@react-native-async-storage/async-storage/jest/async-storage-mock")
);
jest.mock("@react-native-community/netinfo", () =>
  require("@react-native-community/netinfo/jest/netinfo-mock")
);

// react-native-screens' native views (RNSScreen) aren't available under
// react-test-renderer -- disable native screen optimization in tests so
// native-stack/bottom-tabs render with plain Views instead of crashing.
try {
  // eslint-disable-next-line global-require
  require("react-native-screens").enableScreens(false);
} catch {
  // react-native-screens not present in this environment -- best effort only.
}
