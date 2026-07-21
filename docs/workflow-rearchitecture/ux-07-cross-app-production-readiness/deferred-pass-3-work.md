# Deferred to Pass 3 (customer-app)

1. Dark-mode migration of the remaining 14 screens: BookingsListScreen,
   BookingDetailScreen, ChatScreen, JobTrackingScreen, ProfileScreen,
   ReviewScreen, NotificationsScreen, AddressBookScreen, ServiceHistoryScreen,
   ServiceDetailScreen, HelpSupportScreen, PaymentMethodsScreen, InvoiceScreen,
   QuoteApprovalScreen. Mechanical repeat of the Pass 2 pattern (see
   `round-4-pass-2-approval-gate.md`'s recommendation).
2. Responsive-width certification (320/360/390/430/768/1024) with real
   measurement/evidence, not just style-value reasoning.
3. 320px explicit certification document for the screens the mission names
   (home, SmartBot, service/address cards, price, booking summary/list/detail,
   review form, bottom nav, error states).
4. Language-content stress test with realistic long English/Hindi/Punjabi
   conversation content in SmartBot — verify wrapping, glyph rendering (matras/
   Gurmukhi marks), bubble/card/sheet height, and that switching language mid-
   conversation does not reset booking-flow progress (the reducer-based
   `chatBookingState` should already guarantee this structurally since language
   is independent state, but it was not empirically re-verified this pass).
5. Full accessibility semantic audit (CSV) across all screens: headings, all
   icon-only button labels, modal/bottom-sheet semantics, review-rating
   semantics beyond StarRating itself.
6. Keyboard/focus audit: focus order, visible indicators, dialog focus
   containment + return-after-close.
7. Touch-target audit (CSV) beyond the ad hoc 44px minimums already applied to
   Button/StarRating/language-modal-close/tab icons.
8. Contrast audit (CSV) for both light and dark across all screens.
9. Text-scaling report (increased system font size) across all screens.
10. Reduced-motion audit beyond `Skeleton` (typing indicator if one exists in
    the not-yet-migrated screens, sheet transitions, button animations).
11. Loading/empty/error-state audit (CSV) across all screens for dark +
    responsive + accessible presentation.
12. Playwright (or Expo-web) visual run against real production routes with
    real backend responses, plus the full visual-evidence-index.csv (light/
    dark pairs, 320px, Hindi/Punjabi conversation) named in the mission brief.
13. ESLint run and any resulting fixes.
