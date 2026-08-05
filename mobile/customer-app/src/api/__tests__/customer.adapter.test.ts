import { parseCustomerProfileDto, adaptCustomerProfile } from "../adapters/customer";
import { makeCustomerProfileDto } from "../../testing/fixtures";

describe("CustomerProfile adapter", () => {
  it("adapts a well-formed profile DTO", () => {
    const dto = parseCustomerProfileDto(makeCustomerProfileDto());
    const profile = adaptCustomerProfile(dto);
    expect(profile.fullName).toBe("Asha Rao");
    expect(profile.verified).toBe(true);
  });

  it("never splits the single real is_verified flag into separate mobile/email badges", () => {
    const dto = parseCustomerProfileDto(makeCustomerProfileDto({ is_verified: false }));
    const profile = adaptCustomerProfile(dto);
    expect(profile.verified).toBe(false);
    expect(profile).not.toHaveProperty("mobileVerified");
    expect(profile).not.toHaveProperty("emailVerified");
  });

  it("derives capabilities from confirmed real routes, never optimistically", () => {
    const dto = parseCustomerProfileDto(makeCustomerProfileDto());
    const profile = adaptCustomerProfile(dto);
    expect(profile.capabilities).toEqual({
      canEditProfile: true,
      canUpdateAvatar: false,
      canManageAddresses: false,
      canChangePassword: true,
      canManageSessions: true,
      canDeleteAccount: false,
    });
  });

  it("throws a contract validation error when the response is missing required real fields", () => {
    expect(() => parseCustomerProfileDto({ id: "c-1" })).toThrow();
  });
});
