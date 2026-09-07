import { expect, it } from "vitest";
import { twoHourWindows } from "./booking-capacity";

it("shows four complete two-hour windows in an eight-hour workday", () => {
  expect(twoHourWindows("09:00", "17:00")).toEqual(["09:00–11:00", "11:00–13:00", "13:00–15:00", "15:00–17:00"]);
});
it("excludes breaks and incomplete trailing windows", () => {
  expect(twoHourWindows("09:00", "17:30", "12:00", "13:00")).toEqual(["09:00–11:00", "13:00–15:00", "15:00–17:00"]);
  expect(twoHourWindows("17:00", "09:00")).toEqual([]);
});
