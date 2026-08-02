import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { JobDetailsDTO, JobIdentityDTO } from "../../../services/jobDetail/types";

function Cell({ label, value }: { label: string; value: string }) {
  const { theme } = useTheme();
  return (
    <View style={{ flex: 1, minWidth: 90 }}>
      <AppText variant="caption" color="tertiary">{label}</AppText>
      <AppText variant="bodyStrong">{value}</AppText>
    </View>
  );
}

/** Type/Brand are read defensively from an unstructured snapshot field on
 * the backend -- absent for most real jobs today (spec section 12). Only
 * the *_required flags are trustworthy; the value itself is best-effort. */
export function JobDetailsGrid({ job, details }: { job: JobIdentityDTO; details: JobDetailsDTO }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.base }}>
      <Cell label="Job type" value={job.job_type_label ?? "—"} />
      {details.type_required ? <Cell label="Type" value={details.type_brand_value ?? "Not recorded"} /> : null}
      {details.brand_required ? <Cell label="Brand" value={details.type_brand_value ?? "Not recorded"} /> : null}
    </View>
  );
}
