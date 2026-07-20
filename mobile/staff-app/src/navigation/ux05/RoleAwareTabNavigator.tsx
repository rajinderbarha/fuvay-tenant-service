import React from "react";
import { useAuth } from "../../context/AuthContext";
import { deriveRole } from "../../lib/ux05/permissions";
import { TechnicianTabNavigator } from "./TechnicianTabNavigator";
import { StaffTabNavigator } from "./StaffTabNavigator";

/**
 * Root tab-set selector (workstream 2). Uses the same fail-closed
 * deriveRole() as everywhere else: an unrecognized/unlabeled StaffUser
 * degrades to the TechnicianTabNavigator, never the Staff one -- so an
 * ambiguous role never grants access to staff-only areas (WorkQueue/More)
 * through the frontend nav layer. This is the sole call site that decides
 * which of the two tab sets mounts; each tab set itself is unaware of role.
 */
export function RoleAwareTabNavigator() {
  const { user } = useAuth();
  const role = user ? deriveRole(user) : "technician";
  return role === "staff" ? <StaffTabNavigator /> : <TechnicianTabNavigator />;
}
