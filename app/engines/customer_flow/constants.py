"""Customer flow constants — allowed flow types and component keys."""

VALID_FLOW_TYPES = {
    "service_booking",
    "appointment_booking",
    "lead_capture",
    "order_flow",
    "inquiry_flow",
    "product_inquiry",
    "unsupported",
}

VALID_COMPONENT_KEYS = {
    "ServiceBookingFlow",
    "AppointmentBookingFlow",
    "LeadCaptureFlow",
    "OrderFlow",
    "InquiryFlow",
    "ProductInquiryFlow",
    "UnsupportedFlow",
}

# Required engine per flow type
FLOW_ENGINE_MAP: dict[str, str] = {
    "service_booking":      "booking_engine",
    "appointment_booking":  "appointment_engine",
    "lead_capture":         "lead_engine",
    "order_flow":           "order_engine",
    "inquiry_flow":         "inquiry_engine",
    "product_inquiry":      "product_inquiry_engine",
    "unsupported":          "none",
}

FLOW_COMPONENT_MAP: dict[str, str] = {
    "service_booking":      "ServiceBookingFlow",
    "appointment_booking":  "AppointmentBookingFlow",
    "lead_capture":         "LeadCaptureFlow",
    "order_flow":           "OrderFlow",
    "inquiry_flow":         "InquiryFlow",
    "product_inquiry":      "ProductInquiryFlow",
    "unsupported":          "UnsupportedFlow",
}
