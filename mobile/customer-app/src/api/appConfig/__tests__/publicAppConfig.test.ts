import { isVersionBelow } from "../publicAppConfig";

describe("public app version gate", () => {
  it.each([
    ["1.0.0", "1.0.0", false],
    ["1.9.9", "2.0.0", true],
    ["2.1.0", "2.0.9", false],
    ["1.0", "1.0.1", true],
  ])("compares %s against %s", (current, minimum, expected) => {
    expect(isVersionBelow(current, minimum)).toBe(expected);
  });
});
