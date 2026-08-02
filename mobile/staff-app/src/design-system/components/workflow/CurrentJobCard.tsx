import React from "react";
import { View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { Card } from "../foundation/Layout";
import { StatusBadge } from "../data-display/Badges";
import { CustomerAlias } from "../data-display/Privacy";
import { WorkflowStepper } from "./WorkflowStepper";
import { NextActionCard } from "./NextActionCard";
import { BlockerCard } from "./BlockerCard";
import { CurrentJobCardModel } from "../../types";

export interface CurrentJobCardProps {
  model: CurrentJobCardModel;
  onPressCard: (jobId: string) => void;
  onPressAction: () => void;
}

/**
 * Home screen's "current job" summary. Receives the exact
 * CurrentJobCardModel contract (spec section 9) -- never customer phone/
 * email/unrestricted address/tenant pricing/raw exceptions/arbitrary URLs.
 */
export function CurrentJobCard({ model, onPressCard, onPressAction }: CurrentJobCardProps) {
  const { theme } = useTheme();
  return (
    <Card>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: theme.spacing.sm }}>
        <View>
          <AppText variant="bodyStrong">{model.jobNumber} · {model.serviceName}</AppText>
          <AppText variant="caption" color="tertiary">{model.jobTypeLabel}{model.typeLabel ? ` · ${model.typeLabel}` : ""}{model.brandLabel ? ` · ${model.brandLabel}` : ""}</AppText>
        </View>
        <StatusBadge statusCode={model.statusCode} />
      </View>

      <View style={{ flexDirection: "row", justifyContent: "space-between", marginBottom: theme.spacing.base }}>
        <CustomerAlias alias={model.customerAlias} />
        <AppText variant="caption" color="tertiary">{model.scheduleLabel}</AppText>
      </View>

      {model.workflowSteps.length > 0 ? (
        <View style={{ marginBottom: theme.spacing.base }}>
          <WorkflowStepper steps={model.workflowSteps} />
        </View>
      ) : null}

      {model.blocker ? (
        <View style={{ marginBottom: theme.spacing.sm }}>
          <BlockerCard blocker={model.blocker} />
        </View>
      ) : null}

      {model.requiredAction ? (
        <NextActionCard title="Next required action" action={model.requiredAction} onPress={onPressAction} />
      ) : null}
    </Card>
  );
}
