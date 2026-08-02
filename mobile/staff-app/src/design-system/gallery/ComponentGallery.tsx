import React, { useState } from "react";
import { View } from "react-native";
import { useTheme, ThemePreference } from "../themes";
import { AppText } from "../components/typography/AppText";
import { Heading } from "../components/typography/Heading";
import { Label, Caption } from "../components/typography/Label";
import { LinkText } from "../components/typography/LinkText";
import { NumericText } from "../components/typography/NumericText";
import { ScrollScreen } from "../components/foundation/ScrollScreen";
import { Card, Section, Stack, Inline, Divider, Spacer } from "../components/foundation/Layout";
import { PrimaryButton, SecondaryButton, TertiaryButton, DestructiveButton } from "../components/actions/Buttons";
import { IconButton } from "../components/actions/IconButton";
import { ButtonGroup } from "../components/actions/ButtonGroup";
import {
  TextField, PasswordField, SearchField, TextArea, SelectField, DateField, TimeField,
  Checkbox, Radio, Switch, SegmentedControl, CurrencyField, QuantityField,
} from "../components/forms";
import {
  InlineAlert, ErrorBanner, SuccessBanner, OfflineBanner, BlockingBanner,
} from "../components/feedback/Banner";
import { LoadingSpinner, Skeleton, ProgressBar } from "../components/feedback/Loading";
import { EmptyState, ErrorState, RetryState, PermissionDeniedState, RestrictedAccountState, PartialDataNotice } from "../components/feedback/States";
import { StatusBadge, PriorityBadge } from "../components/data-display/Badges";
import { MetricCard } from "../components/data-display/MetricCard";
import { InfoRow, KeyValueList, SectionHeader, ListRow } from "../components/data-display/InfoRow";
import { Avatar } from "../components/data-display/Avatar";
import { CustomerAlias, MaskedIdentifier, PrivacyNotice, JobScopedLocation, RelayContactButton } from "../components/data-display/Privacy";
import { Money } from "../components/data-display/Money";
import { DateTimeText, RelativeTime } from "../components/data-display/DateTimeText";
import { Rating } from "../components/data-display/Rating";
import { AttachmentThumbnail } from "../components/data-display/AttachmentThumbnail";
import { Timeline } from "../components/data-display/Timeline";
import { WorkflowStepper } from "../components/workflow/WorkflowStepper";
import { NextActionCard } from "../components/workflow/NextActionCard";
import { BlockerCard } from "../components/workflow/BlockerCard";
import { JobCard } from "../components/workflow/JobCard";
import { CurrentJobCard } from "../components/workflow/CurrentJobCard";
import { AssignmentCard } from "../components/workflow/AssignmentCard";
import { AvailabilityStatus } from "../components/workflow/AvailabilityStatus";
import { EstimateSummary } from "../components/workflow/EstimateSummary";
import { PartsRequestCard } from "../components/workflow/PartsRequestCard";
import { ChecklistItem, ChecklistItemModel } from "../components/workflow/ChecklistItem";
import { CompletionProofCard } from "../components/workflow/CompletionProofCard";
import { DirectPaymentConfirmationCard, DirectPaymentState } from "../components/workflow/DirectPaymentConfirmationCard";
import { BottomSheet } from "../components/overlays/BottomSheet";
import { ActionSheet } from "../components/overlays/ActionSheet";
import { ConfirmationDialog } from "../components/overlays/ConfirmationDialog";
import { FullScreenModal } from "../components/overlays/FullScreenModal";
import { MediaPickerTrigger, MediaPreview, EvidenceGrid, MediaUploadError } from "../components/media";
import { WORKFLOW_STATUS_MAP } from "../workflowStatus";
import { CurrentJobCardModel } from "../types";

/**
 * Dev-only visual QA surface (spec D.15). Renders every design-system
 * component in its required states across Light/Dark and a large-text /
 * narrow-width simulation. This is NOT Storybook (no real Storybook is
 * configured) -- it's a single in-app screen, wired in only behind a dev
 * flag in src/root/App.tsx, never part of production navigation, and it
 * fetches nothing from the backend.
 */

function GallerySection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Section spacing="xl">
      <Heading level="small" style={{ marginBottom: 12 }}>{title}</Heading>
      <Stack gap="base">{children}</Stack>
    </Section>
  );
}

function Swatch({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View style={{ marginBottom: 8 }}>
      <Caption color="tertiary" style={{ marginBottom: 4 }}>{label}</Caption>
      {children}
    </View>
  );
}

const SAMPLE_JOB: CurrentJobCardModel = {
  jobId: "j1", jobNumber: "JOB-1042", serviceName: "AC Repair", jobTypeLabel: "Repair",
  customerAlias: "Customer A.", scheduleLabel: "Today, 2:00 PM", locationLabel: "Koramangala, Bengaluru",
  statusCode: "quote_required", statusLabel: "Estimate Pending",
  workflowSteps: [
    { key: "assigned", label: "Assigned", state: "completed" },
    { key: "on_the_way", label: "On the way", state: "completed" },
    { key: "inspection", label: "Inspection", state: "current" },
    { key: "estimate", label: "Estimate", state: "upcoming" },
    { key: "work", label: "Work", state: "upcoming" },
  ],
  blocker: { code: "ESTIMATE_APPROVAL_PENDING", title: "Waiting on customer", message: "Customer hasn't approved the estimate yet.", severity: "warning" },
  requiredAction: { code: "SEND_ESTIMATE", label: "Send Estimate", enabled: true, tone: "primary" },
};

const CHECKLIST_ITEMS: ChecklistItemModel[] = [
  { itemId: "1", label: "Verify unit power supply", required: true, completed: true },
  { itemId: "2", label: "Photo of nameplate", required: true, completed: false, evidenceRequired: true, evidenceProvided: false },
  { itemId: "3", label: "Optional: clean filter", required: false, completed: false },
];

export function ComponentGallery() {
  const { theme, mode, preference, setPreference } = useTheme();
  const [largeText, setLargeText] = useState(false);
  const [narrow, setNarrow] = useState(false);
  const [checked, setChecked] = useState(false);
  const [radioValue, setRadioValue] = useState("a");
  const [switchValue, setSwitchValue] = useState(true);
  const [segment, setSegment] = useState<"today" | "upcoming">("today");
  const [qty, setQty] = useState(1);
  const [sheetVisible, setSheetVisible] = useState(false);
  const [actionSheetVisible, setActionSheetVisible] = useState(false);
  const [dialogVisible, setDialogVisible] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);

  const fontScale = largeText ? 1.6 : 1;
  const maxWidth = narrow ? 320 : undefined;

  return (
    <ScrollScreen contentContainerStyle={{ padding: 16, paddingBottom: 64 }}>
      <View style={{ maxWidth, alignSelf: narrow ? "center" : "stretch", width: narrow ? 320 : "100%" }}>
        <Heading level="large">Component Gallery</Heading>
        <Caption color="tertiary" style={{ marginBottom: 16 }}>
          Dev-only QA surface. Not shown in production navigation. Not Storybook.
        </Caption>

        <Card style={{ marginBottom: 24 }}>
          <Label strong style={{ marginBottom: 8 }}>Gallery controls</Label>
          <Inline gap="sm" wrap style={{ marginBottom: 8 }}>
            <SecondaryButton label={`Theme: ${preference}`} onPress={() => {
              const next: ThemePreference = preference === "system" ? "light" : preference === "light" ? "dark" : "system";
              setPreference(next);
            }} />
            <SecondaryButton label={largeText ? "Large text: ON" : "Large text: OFF"} onPress={() => setLargeText(v => !v)} />
            <SecondaryButton label={narrow ? "Width: narrow" : "Width: full"} onPress={() => setNarrow(v => !v)} />
          </Inline>
          <Caption color="tertiary">Resolved mode: {mode}</Caption>
        </Card>

        <GallerySection title="Typography">
          <Heading level="large" style={{ fontSize: 28 * fontScale }}>Heading Large</Heading>
          <Heading level="medium" style={{ fontSize: 22 * fontScale }}>Heading Medium</Heading>
          <Heading level="small" style={{ fontSize: 18 * fontScale }}>Heading Small</Heading>
          <AppText variant="body" style={{ fontSize: 16 * fontScale }}>Body text, default color, wraps normally when long: the quick brown fox jumps over the lazy dog repeatedly to test wrapping.</AppText>
          <AppText variant="bodyStrong" style={{ fontSize: 16 * fontScale }}>Body strong</AppText>
          <Label>Label default</Label>
          <Caption>Caption / tertiary</Caption>
          <NumericText size="large">1,234.50</NumericText>
          <LinkText onPress={() => {}}>Link text (pressable)</LinkText>
          <LinkText onPress={() => {}} disabled>Link text (disabled)</LinkText>
        </GallerySection>

        <GallerySection title="Foundation / Layout">
          <Card>
            <AppText>Card (elevation sm, default)</AppText>
          </Card>
          <Card elevation="none">
            <AppText>Card (elevation none, border only)</AppText>
          </Card>
          <Inline gap="sm">
            <View style={{ width: 40, height: 40, backgroundColor: theme.colors.brandPrimary, borderRadius: 8 }} />
            <View style={{ width: 40, height: 40, backgroundColor: theme.colors.brandPrimary, borderRadius: 8 }} />
          </Inline>
          <Divider />
          <Spacer size="sm" />
        </GallerySection>

        <GallerySection title="Actions / Buttons">
          <Swatch label="Default">
            <PrimaryButton label="Primary" onPress={() => {}} />
          </Swatch>
          <Swatch label="Loading (label area does not resize)">
            <PrimaryButton label="Primary" onPress={() => {}} loading />
          </Swatch>
          <Swatch label="Disabled with reason">
            <PrimaryButton label="Submit" onPress={() => {}} disabled disabledReason="Complete all required fields first" />
          </Swatch>
          <Swatch label="All tones">
            <ButtonGroup>
              <SecondaryButton label="Secondary" onPress={() => {}} />
              <TertiaryButton label="Tertiary" onPress={() => {}} />
              <DestructiveButton label="Destructive" onPress={() => {}} />
            </ButtonGroup>
          </Swatch>
          <Swatch label="Icon buttons">
            <Inline gap="sm">
              <IconButton icon="add" accessibilityLabel="Add" onPress={() => {}} />
              <IconButton icon="trash-outline" accessibilityLabel="Delete" tone="danger" onPress={() => {}} />
              <IconButton icon="add" accessibilityLabel="Add" onPress={() => {}} disabled />
              <IconButton icon="refresh" accessibilityLabel="Refresh" onPress={() => {}} loading />
            </Inline>
          </Swatch>
        </GallerySection>

        <GallerySection title="Forms">
          <TextField label="Name" placeholder="Enter name" required />
          <TextField label="Name (error)" value="" errorText="This field is required" required />
          <TextField label="Name (disabled)" value="Locked value" editable={false} disabledReason="Set by your business, contact your admin to change" />
          <PasswordField label="Password" placeholder="Enter password" />
          <SearchField placeholder="Search jobs…" value="" onChangeText={() => {}} />
          <TextArea label="Notes" placeholder="Long-form notes…" helperText="Visible to your team only" />
          <SelectField label="Job type" placeholder="Choose job type" onPress={() => {}} />
          <Inline gap="sm">
            <View style={{ flex: 1 }}><DateField onPress={() => {}} /></View>
            <View style={{ flex: 1 }}><TimeField onPress={() => {}} /></View>
          </Inline>
          <Checkbox label="I have verified the nameplate" checked={checked} onChange={setChecked} />
          <Radio label="Option A" selected={radioValue === "a"} onSelect={() => setRadioValue("a")} />
          <Radio label="Option B" selected={radioValue === "b"} onSelect={() => setRadioValue("b")} />
          <Switch label="Available for new jobs" value={switchValue} onChange={setSwitchValue} />
          <SegmentedControl
            options={[{ label: "Today", value: "today" }, { label: "Upcoming", value: "upcoming" }]}
            value={segment}
            onChange={setSegment}
          />
          <CurrencyField label="Visit fee" value="500" onChangeText={() => {}} />
          <QuantityField label="Quantity" value={qty} onChange={setQty} />
        </GallerySection>

        <GallerySection title="Feedback / Banners">
          <InlineAlert tone="info" title="Info" message="Informational message." />
          <InlineAlert tone="success" title="Success" message="Saved successfully." />
          <InlineAlert tone="warning" title="Warning" message="Please double-check this." />
          <InlineAlert tone="danger" title="Danger" message="Something needs attention." />
          <ErrorBanner message="Could not load jobs. Pull to retry." />
          <SuccessBanner message="Job accepted." />
          <OfflineBanner lastSyncedLabel="5 minutes ago" />
          <BlockingBanner
            title="Estimate approval required"
            message="You can't start work until the customer approves the estimate."
            blockCode="ESTIMATE_APPROVAL_PENDING"
            permittedNextActionLabel="View estimate"
          />
        </GallerySection>

        <GallerySection title="Feedback / Loading & Progress">
          <Inline gap="base">
            <LoadingSpinner size="small" />
            <LoadingSpinner size="large" />
          </Inline>
          <Skeleton width="100%" height={16} />
          <Skeleton width="60%" height={16} />
          <ProgressBar progress={0.4} />
          <ProgressBar progress={1} tone="success" />
        </GallerySection>

        <GallerySection title="Feedback / States">
          <EmptyState icon="briefcase-outline" title="No jobs yet" message="New assignments will show up here." />
          <ErrorState icon="alert-circle-outline" title="Something went wrong" message="We couldn't load this page." actionLabel="Retry" onAction={() => {}} />
          <RetryState icon="cloud-offline-outline" title="You're offline" message="Check your connection and try again." onRetry={() => {}} />
          <PermissionDeniedState message="You don't have access to this section." />
          <RestrictedAccountState message="Your account access has been restricted. Contact your business admin." />
          <PartialDataNotice message="Some data may be out of date." onRetry={() => {}} />
        </GallerySection>

        <GallerySection title="Data display / Status & Priority">
          <Caption color="tertiary" style={{ marginBottom: 4 }}>Every WORKFLOW_STATUS_MAP entry</Caption>
          <Inline gap="sm" wrap>
            {Object.keys(WORKFLOW_STATUS_MAP).map(code => <StatusBadge key={code} statusCode={code} />)}
            <StatusBadge statusCode="__unknown_status__" />
          </Inline>
          <Inline gap="sm" wrap>
            <PriorityBadge priority="low" />
            <PriorityBadge priority="normal" />
            <PriorityBadge priority="high" />
            <PriorityBadge priority="urgent" />
          </Inline>
        </GallerySection>

        <GallerySection title="Data display / Metrics & Rows">
          <Inline gap="sm">
            <MetricCard label="Today's jobs" value="4" tone="neutral" />
            <MetricCard label="Completed" value="12" tone="success" />
          </Inline>
          <KeyValueList items={[{ label: "Job number", value: "JOB-1042" }, { label: "Type", value: "Repair" }]} />
          <SectionHeader title="Recent activity" />
          <ListRow title="AC Repair" subtitle="Today, 2:00 PM" />
        </GallerySection>

        <GallerySection title="Data display / Avatar & Privacy">
          <Inline gap="sm">
            <Avatar name="Ravi Kumar" />
            <Avatar name="A" size={56} />
          </Inline>
          <CustomerAlias alias="Customer A." />
          <CustomerAlias alias="" />
          <MaskedIdentifier maskedValue="•••• 4821" label="Phone" />
          <PrivacyNotice text="Customer contact details are relayed through ServiceOS to protect privacy." />
          <JobScopedLocation localityLabel="Koramangala, Bengaluru" />
          <RelayContactButton onPress={() => {}} />
        </GallerySection>

        <GallerySection title="Data display / Money, Date, Rating, Media, Timeline">
          <Money amount={1250.5} />
          <DateTimeText isoString={new Date().toISOString()} format="datetime" />
          <RelativeTime isoString={new Date(Date.now() - 3600_000).toISOString()} />
          <Rating value={4} />
          <AttachmentThumbnail label="Nameplate.jpg" onPress={() => {}} />
          <Timeline steps={[
            { label: "Assigned", state: "completed" },
            { label: "On the way", state: "completed" },
            { label: "Inspection", state: "current" },
            { label: "Work done", state: "upcoming" },
          ]} />
        </GallerySection>

        <GallerySection title="Workflow / Stepper, Actions, Blockers">
          <WorkflowStepper steps={SAMPLE_JOB.workflowSteps} />
          <NextActionCard title="Next required action" action={{ code: "SEND_ESTIMATE", label: "Send Estimate", enabled: true, tone: "primary" }} onPress={() => {}} />
          <NextActionCard title="Next required action" action={{ code: "START_WORK", label: "Start Work", enabled: false, disabledReason: "Waiting on customer approval", tone: "primary" }} onPress={() => {}} />
          <BlockerCard blocker={{ code: "ESTIMATE_APPROVAL_PENDING", title: "Waiting on customer", message: "Customer hasn't approved the estimate yet.", severity: "warning" }} />
        </GallerySection>

        <GallerySection title="Workflow / Job cards">
          <JobCard job={{ jobId: "j1", jobNumber: "JOB-1042", serviceName: "AC Repair", customerAlias: "Customer A.", scheduleLabel: "Today, 2:00 PM", locationLabel: "Koramangala", statusCode: "assigned" }} onPress={() => {}} />
          <JobCard job={{ jobId: "j2", jobNumber: "JOB-1043", serviceName: "Very long service name that should wrap or truncate gracefully across lines", customerAlias: "Customer B.", scheduleLabel: "Tomorrow", statusCode: "__unknown_status__" }} onPress={() => {}} />
          <CurrentJobCard model={SAMPLE_JOB} onPressCard={() => {}} onPressAction={() => {}} />
          <AssignmentCard jobNumber="JOB-1050" serviceName="Water Heater Install" customerAlias="Customer C." scheduleLabel="Today, 4:00 PM" onAccept={() => {}} onDecline={() => {}} />
          <AssignmentCard jobNumber="JOB-1051" serviceName="Geyser Repair" customerAlias="Customer D." scheduleLabel="Today, 5:00 PM" onAccept={() => {}} onDecline={() => {}} loading />
          <AvailabilityStatus value="available" onToggleAvailable={() => {}} />
          <AvailabilityStatus value="off_duty" onToggleAvailable={() => {}} disabled />
        </GallerySection>

        <GallerySection title="Workflow / Estimate & Parts">
          <EstimateSummary
            version={2}
            decisionState="sent"
            lineItems={[
              { label: "Compressor replacement", quantity: 1, unitAmount: 3200, totalAmount: 3200 },
              { label: "Refrigerant refill", quantity: 1, unitAmount: 800, totalAmount: 800 },
            ]}
            visitFeeAmount={200}
            totalAmount={4200}
          />
          <EstimateSummary version={1} decisionState="not_requested" lineItems={[]} totalAmount={0} />
          <PartsRequestCard partName="Compressor" quantity={1} status="customer_approval_pending" />
          <PartsRequestCard partName="Refrigerant" quantity={2} status="business_rejected" reason="Not covered under warranty" />
        </GallerySection>

        <GallerySection title="Workflow / Checklist & Completion">
          {CHECKLIST_ITEMS.map(item => <ChecklistItem key={item.itemId} item={item} onToggle={() => {}} />)}
          <ChecklistItem item={CHECKLIST_ITEMS[0]} onToggle={() => {}} disabled />
          <CompletionProofCard workSummary="Replaced compressor and refilled refrigerant." photoCount={2} requiredPhotoCount={3} />
        </GallerySection>

        <GallerySection title="Workflow / Direct payment confirmation">
          {(["not_reported", "provider_reported", "customer_confirmation_pending", "confirmed", "disputed"] as DirectPaymentState[]).map(state => (
            <DirectPaymentConfirmationCard key={state} amount={1500} state={state} onReportPayment={() => {}} />
          ))}
          <DirectPaymentConfirmationCard amount={1500} state="not_reported" onReportPayment={() => {}} loading />
        </GallerySection>

        <GallerySection title="Media (presentation only)">
          <Inline gap="sm" wrap>
            <MediaPickerTrigger onPress={() => {}} />
            <MediaPreview media={{ id: "1", uri: undefined, status: "pending" }} onPressRemove={() => {}} />
            <MediaPreview media={{ id: "2", uri: undefined, status: "uploading", progress: 0.6 }} />
            <MediaPreview media={{ id: "3", uri: undefined, status: "failed" }} />
          </Inline>
          <EvidenceGrid items={[{ id: "1", status: "uploaded" }, { id: "2", status: "uploading", progress: 0.3 }]} onAdd={() => {}} maxItems={5} />
          <MediaUploadError message="Upload failed. Check your connection." onRetry={() => {}} />
        </GallerySection>

        <GallerySection title="Overlays">
          <Inline gap="sm" wrap>
            <SecondaryButton label="Open bottom sheet" onPress={() => setSheetVisible(true)} />
            <SecondaryButton label="Open action sheet" onPress={() => setActionSheetVisible(true)} />
            <SecondaryButton label="Open confirmation dialog" onPress={() => setDialogVisible(true)} />
            <SecondaryButton label="Open full-screen modal" onPress={() => setModalVisible(true)} />
          </Inline>
        </GallerySection>

        <BottomSheet visible={sheetVisible} onClose={() => setSheetVisible(false)}>
          <AppText variant="bodyStrong" style={{ marginBottom: 8 }}>Bottom sheet content</AppText>
          <AppText color="secondary">Dismissible, safe-area aware.</AppText>
        </BottomSheet>

        <ActionSheet
          visible={actionSheetVisible}
          title="Choose an action"
          options={[{ key: "call", label: "Call through ServiceOS" }, { key: "message", label: "Message" }, { key: "cancel", label: "Cancel job", destructive: true }]}
          onSelect={() => setActionSheetVisible(false)}
          onClose={() => setActionSheetVisible(false)}
        />

        <ConfirmationDialog
          visible={dialogVisible}
          title="Decline this job?"
          message="This action can't be undone."
          destructive
          confirmLabel="Decline"
          onConfirm={() => setDialogVisible(false)}
          onCancel={() => setDialogVisible(false)}
        />

        <FullScreenModal visible={modalVisible} title="Job details" onClose={() => setModalVisible(false)}>
          <AppText>Full-screen modal content.</AppText>
        </FullScreenModal>
      </View>
    </ScrollScreen>
  );
}
