# Meta social booking setup

ServiceOS uses one signed webhook per Meta product and routes both channels
into the existing AI conversation and Home Services booking engines.

## Security first

- Never place Meta app secrets or access tokens in source control or a mobile
  bundle.
- Configure them from **Super Admin → Social Booking**. Secret values are
  encrypted at rest and are not returned to the browser.
- Saving or rotating a credential disables the channel. A successful
  connection test is required before an administrator can enable it again.
- Use a permanent system-user token for WhatsApp production traffic and the
  appropriate professional-account token for Instagram. Rotate leaked tokens
  immediately in Meta Business Manager / App Dashboard.

## Webhook URLs

Append these paths to the public HTTPS API origin:

- WhatsApp: `/v1/messaging/meta/webhook/whatsapp`
- Instagram: `/v1/messaging/meta/webhook/instagram`

The verify token is the long random value entered in the matching admin form.
POST requests must include a valid `X-Hub-Signature-256`; unsigned or invalid
traffic is rejected before JSON is processed.

Subscribe WhatsApp to its `messages` webhook field. Subscribe Instagram to
`messages` and `messaging_postbacks`. The configured business/account ID must
match the identity in each event or the event is acknowledged and ignored.

## Activation sequence

1. Save the channel configuration.
2. Copy the displayed callback path into the matching Meta product.
3. Complete Meta's webhook verification handshake.
4. Run **Test connection** in ServiceOS.
5. For Instagram, run **Publish chat entry** to publish the four icebreakers.
6. Enable the channel.
7. Send a real customer message and check **Recent conversations**.

Publishing the Instagram chat entry is an explicit administrator action. Saving
credentials or deploying the application does not silently change the live
Instagram profile. Publish it again whenever the configured icebreakers change.

## Instagram interaction design

- **Icebreakers** start new conversations with booking, tracking, estimate, and
  support entry points.
- **Generic templates** show the service catalog as scrollable cards using the
  service image and description. They intentionally do not show a price before
  provider matching has calculated the real customer price.
- **Quick replies** handle temporary choices such as questions, areas, and time
  slots. Longer or grouped choices include a visible numbered fallback.
- **Button templates** handle durable actions such as confirmation, quote and
  parts decisions, handover acknowledgement, and direct-payment confirmation.

WhatsApp continues to use its native reply buttons and list messages. Both
channels call the same booking, quote, completion-proof, and payment services;
the channel changes presentation, not business state.

## WhatsApp interaction design

- Reply buttons handle sets of up to three actions, including confirmation,
  estimate, parts, handover, and direct-payment decisions.
- List messages handle larger service, area, problem, booking, and appointment
  choices. ServiceOS paginates before Meta's ten-row limit.
- A booking-location CTA is sent after confirmation when the booking has a
  usable address. ServiceOS does not add an external payment CTA because direct
  payments go from the customer to the provider, not through ServiceOS.
- An optional WhatsApp Flow replaces the long appointment list after provider
  matching. The submitted slot is revalidated by the canonical booking service,
  and the final booking summary is still confirmed in chat.

### Enable the appointment Flow

1. In WhatsApp Manager, create an **Appointment booking** Flow.
2. Upload [`meta/whatsapp-booking-flow.json`](meta/whatsapp-booking-flow.json).
3. Validate and publish the Flow. Publishing is irreversible; create a new Flow
   when changing its screen contract.
4. Copy its numeric Flow ID into **Super Admin → Social Booking → WhatsApp →
   Published booking Flow ID**.
5. Save, run **Test connection**, and enable WhatsApp again. The connection test
   fails closed if the configured Flow is missing, unpublished, or belongs to a
   different WABA.

ServiceOS injects the matched service, provider, authoritative price, saved
address, and currently available slots into the published screen. The opaque
Flow token is signed, expires after 48 hours, and is bound to the exact chat and
draft. A completed Flow can select only a slot ID; it cannot submit provider or
price data. If the Flow cannot open, the customer can reply `TIMES` to receive
the existing WhatsApp list instead.

## Customer commands

- `/fuvay` starts a fresh booking conversation.
- `/track` reads the latest real ServiceBooking / ServiceJob state.
- `/human` pauses automation for administrator takeover.
- `/stop` opts out of automated replies.
- WhatsApp customers are matched by their verified WhatsApp number. A new
  customer record is provisioned only when a first-time customer sends the
  exact final confirmation phrase.
- Instagram customers use `/link +<country-code><number>` and `/verify <code>`
  once. Successful OTP verification links an existing account or provisions
  a new customer record; the Instagram-scoped ID is never trusted as a phone.

Final booking creation requires the exact customer reply `CONFIRM BOOKING`
after the server-generated booking summary is shown. Vague replies such as
“yes” or “okay” cannot create a booking.

After booking, the conversation remains usable throughout assignment, travel,
inspection, estimate approval, active work, parts approval, and completion.
Current estimates are shown with customer-visible line items and can be
approved, declined, or returned for changes in either channel.
