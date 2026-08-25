const { cleanup } = require("@testing-library/react-native");
const { queryClient } = require("./src/api/queryClient");
const {
  __resetNetworkStateForTests,
  stopNetworkMonitoring,
} = require("./src/api/networkState");

afterEach(() => {
  // React Query retains cache-GC timers and the native network adapter retains a
  // subscription unless the shared application providers are fully disposed.
  // Dispose both explicitly so Jest exits naturally and each test starts clean.
  cleanup();
  queryClient.clear();
  stopNetworkMonitoring();
  __resetNetworkStateForTests();
});
