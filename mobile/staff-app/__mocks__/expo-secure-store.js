// Deterministic in-memory SecureStore mock for jest (Phase F). The real
// jest-expo default mock for native Expo modules doesn't reliably emulate
// get/set/delete round-tripping, which several session-storage tests rely on.
let store = {};

module.exports = {
  __resetMockStore: () => { store = {}; },
  getItemAsync: jest.fn(async (key) => (key in store ? store[key] : null)),
  setItemAsync: jest.fn(async (key, value) => { store[key] = value; }),
  deleteItemAsync: jest.fn(async (key) => { delete store[key]; }),
};
