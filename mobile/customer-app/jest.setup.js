// UX-06 Round 2: real Jest AsyncStorage mock, per the library's own documented
// integration steps (https://react-native-async-storage.github.io/async-storage/docs/advanced/jest).
jest.mock("@react-native-async-storage/async-storage", () =>
  require("@react-native-async-storage/async-storage/jest/async-storage-mock")
);

// Add/Edit Address phase: without this, every test mounting AppProviders
// (which starts network monitoring on mount) crashes with "Cannot read
// properties of undefined (reading 'isInternetReachable')" from the real
// native module's jest-environment fallback -- the library ships its own
// mock for exactly this, mirroring the AsyncStorage mock above.
jest.mock("@react-native-community/netinfo", () =>
  require("@react-native-community/netinfo/jest/netinfo-mock")
);
