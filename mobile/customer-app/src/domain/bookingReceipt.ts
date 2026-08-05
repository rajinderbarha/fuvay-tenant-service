import { ServerDate } from "./dates";
import { BookingReceiptStage } from "./bookingStatus";
import { ServicePriceState, InspectionPricing } from "./servicePricing";
import { NotificationCapability } from "./notificationCapability";

export interface ReceiptAnswerField {
  key: string;
  label: string;
  displayValue: string;
}

export interface ReceiptAddress {
  label: string | null;
  formatted: string;
  zipcode: string | null;
}

export interface FinalizedPricingPresentation {
  state: ServicePriceState;
  inspection: InspectionPricing | null;
}

export interface BookingReceipt {
  bookingId: string;
  bookingNumber: string | null;
  currentStage: BookingReceiptStage;
  statusLabel: string;
  activityText: string | null;
  supportingText: string | null;
  service: {
    name: string | null;
    jobType: string | null;
    issueSummary: string | null;
    answers: ReceiptAnswerField[];
  };
  address: ReceiptAddress;
  pricing: FinalizedPricingPresentation;
  notificationCapability: NotificationCapability;
  preferredDate: ServerDate | null;
}
