# SashaInfinity Growth OS — implementation and acceptance

Release candidate: 2026-09-20. Schema head: `0051`.

This extends the existing LMS and commercial ledger. It is **not a production certification** and does not promise revenue, profitability or predictive accuracy.

## Where to use it

- Admin: `/admin/operations?view=growth` — revenue intelligence, billing/delivery, CRM, experiments, AI proposals and acceptance evidence.
- Customer: `/business-services` — catalog, reviewed agreements, invoices, licensed assets, recurring agreements and approved offers.
- Account menu: **Services & billing**.
- Existing Commercial tab remains the offer/contract authoring surface. A contract with a Growth billing policy must use the Growth invoice path to preserve tax and period safeguards.

## Three commercial journeys

| Pillar | Supported billing and fulfillment |
| --- | --- |
| Meiporul | Asset licenses, lab milestones, AMC and device-service invoices. A fulfilled asset license authorizes the tenant's active members through the existing private 3D file endpoint. Physical deployment and service completion require recorded acceptance evidence. |
| Seyappaduporul | Institution SaaS, franchise and managed-service agreements. Fulfilled institution SaaS with reference `campus` or `enterprise` participates in the existing campus plan gate. Existing Razorpay subscriptions continue to work. |
| Utporul | Premium credential, career-service and creator-commerce billing. Credentials require completed learning and pass the existing certificate issuance checks. Partner earnings accrue from captured invoices and reverse on refunds. |

### Purchase lifecycle

1. A customer with owner/admin/finance workspace access reviews a catalog offer. Experiments assign a stable account-level variant and the server computes its price.
2. Accepting creates an agreement, not a charge. An administrator sets tax classification, customer/supplier details, resource reference, recipient and any revenue-share recipient.
3. An invoice snapshots these settings and the agreed price. Recurring cycles have unique keys; milestones cannot exceed the agreement total, including rounding.
4. Razorpay checkout uses the stored invoice amount. Server-side signature/payment checks and the existing signed webhook pipeline confirm capture. A timed-out order creation is reconciled by receipt rather than blindly creating another order.
5. Capture queues delivery. Fulfillment activates source-scoped access; payment does not prove that a physical lab was installed or that a learner earned a credential.
6. Paid renewals can extend an already-fulfilled asset/institution/AMC/franchise service. Cancellation stops future invoice generation while preserving the purchased period. Existing issued invoices are not automatically forgiven.
7. Confirmed full refunds revoke the affected delivery. Campus refunds recompute paid-through from remaining ledger-supported charges. A valid separate purchase or manually administered entitlement is not removed.

Automatic recurring invoicing is **not an automatic bank debit**. Commercial refunds currently converge from verified Razorpay refunds or the existing administrator ledger workflow; this module does not initiate a new provider refund or bank transfer. Pending provider creation without unique recovery evidence remains blocked for operator reconciliation.

## Sales, marketing and experiments

- Existing campus leads feed the CRM inbox. Qualification is explainable: confirmed budget 30 points, decision-maker 30, attended demo 40. Follow-up tasks are deduplicated; paid linked contracts are required for a won stage.
- Campaign touches require consent; accepted agreements snapshot first/last touch within a 30-day lookback. Purchase conversions come from paid invoices, not browser-supplied purchase events.
- Marketing spend is reference-deduplicated. Commercial CAC and realized LTV are scoped to business customers in the commercial invoice ledger. Course learners and institutional customers are not silently treated as the same identity.
- The unified cash panel reuses the existing portfolio adapters for course/cart payments, tuition, vouchers, commercial revenue and newly recorded campus charges. It is a cash view, **not net profit or fully unified customer LTV**. Historical campus events without amount/currency evidence are not invented or automatically backfilled.
- Churn watch is a billing-risk heuristic (overdue invoices and agreements nearing expiry), not a trained churn model. Cohorts show acquisition and repeat-payment activity, not product engagement retention.
- Forecasting shows trailing net run-rate and separately weighted open pipeline. These are assumptions, not additive guaranteed forecasts.
- Pricing, landing-copy and campaign-copy experiments operate on the Services storefront. They do not create external ad campaigns. Server assignment, bounded discounts and paid-invoice conversion reporting prevent client-selected prices. Wilson intervals and minimum samples support review; no automatic winner is declared.
- AI uses the existing GLM/Gemini vault, sends catalog/owned-offer information rather than customer PII, validates proposal structure and caps discounts at 20%. Missing/failing providers return an error, never fabricated recommendations.
- Approval and publication are explicit. Publishing exposes the reviewed offer to that workspace; only finance members opted into **Business offers** receive in-app notifications. No automatic promotional email/WhatsApp is sent. Acceptance checks the price snapshot and 30-day validity, then creates an agreement idempotently.

## Financial and access controls

- Money is computed with decimal arithmetic. INR is the supported reviewed-tax workflow.
- Tax rates/classification must be supplied by an authorized reviewer. Invoice PDFs preserve the snapshot, supplier/customer information, HSN/SAC, place of supply, split taxes and reverse-charge flag. This is **not GST compliance sign-off**; IRN/e-invoicing, authorized-signatory requirements, classification, credits and filing obligations require professional review for the actual supplier.
- Partner balances have a 14-day hold. Refunds create clawbacks, including after an external payout. Recording settlement requires the exact available balance and a unique external bank reference. It does not execute a transfer.
- Tenant-scoped billing denies unrelated users and non-finance members. Feature access is evaluated against paid, fulfilled, unexpired purchases rather than creating indefinite shared grants.
- Migration `0051` is additive and has a frozen schema plus upgrade/downgrade tests. Apply migrations before starting the new API/worker against an existing database.
- The runtime worker runs `growth_maintenance` every 600 seconds. The demo intentionally disables background/provider execution.

## Demo and checks

Run `python scripts/seed_saas_demo.py --seed --serve --port 8016` with the project's Python environment. Start Vite with `VITE_PROXY_TARGET=http://127.0.0.1:8016` and `VITE_DEV_PORT=3016`. Fixtures and role credentials stay under ignored `.local/saas-demo/`; they are not packaged as production data.

Focused suites: `backend/tests/test_growth_os.py`, `test_commercial_revenue.py`, `test_production_runtime.py`; related campus, tenancy, webhook and 3D regression suites; frontend Growth execution tests and the full frontend suite.

`scripts/validate_growth_load.py` performs bounded authenticated read journeys using a private `GROWTH_LOAD_TOKEN` environment variable. It refuses remote targets without explicit `--allow-remote` and HTTPS, follows no redirects, prints no credentials and does not submit payments or sales messages.

## Production acceptance still required

| Gate | Required evidence |
| --- | --- |
| Real payments | Razorpay **test-mode** checkout, duplicate/late signed webhooks, refunds, timeout recovery and reconciliation on reachable staging. Review before live mode. |
| Tax | Supplier-specific classification/rates, invoice requirements and applicable e-invoicing/credit-note process approved by the responsible reviewer. |
| AI | Configured provider API endpoint/model/quota; real generation, invalid-output and fallback tests. A separate chat/coding billing plan is not itself API evidence. |
| PostgreSQL/Redis | Migration and restore into an isolated database, multi-worker races, worker termination and Redis failover on the intended runtime. |
| Capacity | Agreed concurrent-user target and realistic sustained mixed read/write/browser/provider workload. Local SQLite read tests do not establish this. |
| Operations | Customer-support handling for ambiguous payments, negative partner balances, fulfillment disputes, backup RPO/RTO, monitoring receivers and secret rotation. |

Acceptance entries in the admin UI are operator-recorded evidence, not independently verified certification. Launch remains blocked until the required external checks pass.

Provider references: [Razorpay order receipt lookup](https://razorpay.com/docs/api/orders/fetch-all/), [payment integration and signature verification](https://razorpay.com/docs/payments/server-integration/nodejs/integration-steps/), [CBIC invoice rules](https://cbic-gst.gov.in/gst-invoice-rules.html).
