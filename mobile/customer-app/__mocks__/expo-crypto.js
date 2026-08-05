// Deterministic-enough UUID mock for jest -- expo-crypto's real randomUUID
// needs the native module, unavailable under plain jest-node.
let counter = 0;
module.exports = {
  randomUUID: jest.fn(() => {
    counter += 1;
    return `00000000-0000-4000-8000-${String(counter).padStart(12, "0")}`;
  }),
};
