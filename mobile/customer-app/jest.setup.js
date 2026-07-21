// UX-06 Round 2: real Jest AsyncStorage mock, per the library's own documented
// integration steps (https://react-native-async-storage.github.io/async-storage/docs/advanced/jest).
jest.mock("@react-native-async-storage/async-storage", () =>
  require("@react-native-async-storage/async-storage/jest/async-storage-mock")
);
