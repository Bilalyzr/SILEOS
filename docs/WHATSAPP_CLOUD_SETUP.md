# SashaInfinity WhatsApp Cloud API setup

WhatsApp is an account-wide SashaInfinity communication channel powered by Meta's official WhatsApp Cloud API. Every authenticated user manages one global phone and consent record, regardless of whether they are a learner, instructor, institution member or platform administrator. Institution campaigns and campaigns from the global **Communications Center** reuse that consent; joining another institution does not create another opt-in.

SashaInfinity sends approved templates only, records each recipient and delivery state, and re-checks consent when a message is delivered. Managers and administrators can inspect eligible recipients but cannot grant consent for another person. Access tokens, app secrets, verify tokens, phone identifiers and business account identifiers belong only in the backend environment.

## Meta account setup

1. Create or select a Meta Business Portfolio, a Meta developer app with the WhatsApp product, a WhatsApp Business Account and a sending phone number. Enable two-step verification for the sending number.
2. Grant the system user the `whatsapp_business_messaging` permission. Template administration outside SashaInfinity may also need `whatsapp_business_management`.
3. Create and get approval for every SashaInfinity template that will be used. Put only those exact names in `WHATSAPP_APPROVED_TEMPLATES`; the application rejects every other name.
4. Configure the production callback as `https://<backend-host>/api/v1/whatsapp/webhook`. Enter the same private value in Meta's verify-token field and `WHATSAPP_VERIFY_TOKEN`. Subscribe the WhatsApp Business Account to the `messages` webhook field.
5. Set `WHATSAPP_APP_SECRET`. POST callbacks must include Meta's `X-Hub-Signature-256`; invalid or missing signatures are rejected.

## Backend environment

```text
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_BUSINESS_ACCOUNT_ID=
WHATSAPP_BUSINESS_PHONE=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_APP_SECRET=
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_API_VERSION=v23.0
WHATSAPP_APPROVED_TEMPLATES=campus_announcement,attendance_alert,assessment_reminder
```

`WHATSAPP_BUSINESS_PHONE` contains international digits without `+` and is used only to form the opt-in chat link. Use a long-lived system-user access token in production and rotate it through the deployment secret store. The UI exposes only ready/missing configuration states and approved template names.

## Consent and sending flow

1. A signed-in user opens **Communication preferences** at `/communication-preferences`, enters their own number and starts opt-in. The account endpoints are `GET /api/v1/whatsapp/status`, `POST /api/v1/whatsapp/opt-in` and `DELETE /api/v1/whatsapp/opt-in`.
2. The user opens the generated WhatsApp conversation and sends the one-time JOIN challenge. A valid signed inbound webhook confirms the phone and consent; entering a number alone is not confirmation.
3. An authorized institution manager can select an approved template for eligible members of that institution. A platform administrator can use the global **Communications Center** for an explicitly selected, allowed account audience. Campaigns and their recipients are written atomically before background delivery starts. Recipient expansion uses bounded 500-row keyset pages, so large audiences do not require loading every user into application memory.
4. Meta message identifiers are stored. Signed webhook updates advance messages through accepted, sent, delivered, read or failed states. Duplicate callbacks are safe. If a status arrives before its outbound message ID is committed, a durable inbox acknowledges it, retries reconciliation with bounded backoff and expires an identifier that never belongs to this deployment after seven days.
5. A user can opt out in the application or send `STOP` to the connected business number. `STOP` revokes the global consent for every matching normalized account phone and atomically cancels queued or retrying institution and platform messages for those accounts.
6. Before claiming a message for delivery, SashaInfinity re-checks the account's confirmed consent and the audience rule. Institution sends also re-check active institution membership; platform sends re-check the selected allowed role. Pending, revoked, suspended, cross-institution or otherwise ineligible recipients are skipped. The `sending` claim is the dispatch boundary: a message already in flight when withdrawal arrives cannot be recalled from Meta, while every message not yet claimed is cancelled.

Institution WhatsApp screens are campaign tools for that institution. They do not own a separate member consent record. Their contact directory and delivery workflow resolve each member to the same account-level consent used everywhere else in SashaInfinity.

## Global Communications Center

The **Communications Center** at `/admin/communications` is the account-wide campaign and consent view for platform administrators. Its APIs expose provider readiness and consent totals at `GET /api/v1/whatsapp/admin/overview`, privacy-limited contacts at `GET /api/v1/whatsapp/admin/contacts`, campaign history at `GET /api/v1/whatsapp/admin/campaigns`, and campaign creation at `POST /api/v1/whatsapp/admin/campaigns`. Creating a platform campaign requires an explicit whitelisted role audience, an approved template and an idempotency key. These controls do not reveal backend secrets and do not bypass user consent.

Treat these APIs as privileged operational tools: keep the administrator guard enabled, log campaign creation, restrict template variables to the approved contract, and review audience size before enabling production delivery. Do not use the webhook or opt-in endpoints as a general-purpose messaging relay.

## Webhook and data security

- Serve `/api/v1/whatsapp/webhook` only over HTTPS in production. Keep the verification token and app secret in the backend secret store. The supplied Nginx configurations give this exact public route a 1 MB request-body limit; retain an equivalent edge limit if another proxy is used.
- Require and verify Meta's `X-Hub-Signature-256` on every POST callback before reading or changing consent and delivery state.
- Keep JOIN challenges short-lived and single-use. Normalize phone numbers before matching them, and never display another user's full number in a manager or administrator view.
- Accept only configured, Meta-approved template names. Optional media headers must use HTTPS URLs that Meta can fetch; never put a private storage URL or credential into a template.
- Preserve idempotency for campaign creation and webhook-event processing. A retry must not create a second logical campaign or silently restore revoked consent. Provider delivery is at-least-once across an ambiguous timeout or worker crash, so approved templates should be safe to repeat and duplicate delivery should be monitored.
- The built-in delivery tick interleaves institution and platform queues and uses at most four workers in one application process; SQLite preview delivery is serialized. For a multi-process or multi-instance production deployment, run the tick from one dedicated worker or add a distributed lock and provider-aware rate-limited queue.
- Treat `STOP` as account-wide withdrawal. A future opt-in must repeat the JOIN confirmation flow.

The local preview intentionally clears all WhatsApp provider configuration. It can demonstrate account preferences, institution campaign state and the global Communications Center setup state without contacting Meta or sending a real message. Entering a phone number in preview does not enable external delivery.

## Staging acceptance

- Use Meta's test number first, then a dedicated staging number.
- Test webhook verification, invalid signatures, duplicate callbacks, reordered delivery states, an expired JOIN challenge and opt-out before a retry.
- Confirm every production template's exact name, language and variable order.
- Send to internal consented recipients and verify accepted, delivered, read and failed states in Meta, account preferences, the institution campaign view and the global Communications Center.
- Verify that one account consent is reused across multiple institution memberships and that opting out from account settings or sending `STOP` blocks every later institution and platform send.
- Verify that non-institution accounts can opt in, while institution managers still cannot target inactive, suspended or cross-institution members.
- Document support ownership, token rotation and retention requirements before enabling real institution or platform campaigns.

References: [WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api), [Cloud API webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks), and [message templates](https://developers.facebook.com/docs/whatsapp/business-management-api/message-templates).
