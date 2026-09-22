# SashaInfinity Education OS — runtime release candidate

## Product structure

SashaInfinity remains the parent platform with one administration and reporting structure. Meiporul owns immersive/3D experiences and operational device programs; Seyappaduporul owns tutoring and campus workflows; Utporul owns skill courses, coding and assessments. Existing course/content integration, role access, revenue reporting, instructor insights and onboarding tours are reused rather than duplicated.

The orange-gradient Runtime panel extends the existing admin Operations screen. It connects maintenance status, worker freshness, failed-job recovery, execution history, processing queues and last-recorded AI provider health. Links lead to the existing provider vault, content/recording health, revenue and pillar controls.

## Included in this release

- Dedicated supervised maintenance worker with Redis leadership, durable database leases, bounded retries, dead-job visibility and audited admin recovery.
- Private metrics endpoint, structured request telemetry, optional scrubbed error reporting and Prometheus alert rules.
- Worker-aware staging/base/blue-green Compose configurations and a migration/worker gate before traffic switch.
- Isolated multi-role demo seeder using existing business services, bundled learning assets and explicitly synthetic financial examples.
- Local read-only load/restore validation and a source packager with credential-pattern checks, per-file hashes, ZIP readback verification and excluded runtime data.
- Focused worker ownership, recovery, authorization, privacy, migration and UI tests.
- Retained upstream Add to Cart, invoice-date validation, non-negative/finite course pricing, legacy certificate compatibility, explicit enrollment progress, company/revenue export and backup fixes. IDS decisions now distinguish authentication failures from ordinary business permission denials.
- Verified offline first-time admin MFA enrollment and a staging email that the login validator accepts.
- Meiporul gallery category/search filters and keyboard model navigation in the existing accessible dialog system; restored referenced H5P fonts.
- Packaging regression checks retain all frontend TypeScript/CSS source, including the certificate designer, while excluding issued certificates and other runtime data.
- Preserved the latest upstream passed-quiz retake gate at `/start`, without reintroducing the broken gate in submission handling.

## Verification and release status

This is a **release candidate**, not a declaration that a large-consumer production deployment has been certified. Local frontend lint/type-check/build and tests were exercised; backend results and final artifact identifiers are reported with the handoff. Detailed evidence remains under ignored `.local/` so copied local paths, credentials or diagnostic payloads are not published.

Final local evidence on 14 September 2026:

- Full backend run: **1,912 passed, 2 skipped** (999 seconds). Late upstream compatibility changes were additionally covered by a **140-test** targeted run and a final **208-test** assessment/authoring/compatibility/packaging run. These runs overlap and must not be added together as unique coverage.
- Final frontend: **490 passed across 88 files**; lint, TypeScript and production build passed. Vite still reports large optional chunks; low-end device/network performance remains a launch check.
- All **10 synthetic role logins** passed HTTP authentication/profile/admin-boundary checks, including admin MFA.
- Fixture coverage: **78 populated tables out of 246**. Empty domains and external-provider acceptance are documented, not presented as tested.

The local read-only exercise completed 120 requests at concurrency 8 without HTTP failures (p95 118.8 ms), and the SQLite restore passed integrity/count checks for 246 tables. These figures describe this machine and fixture workload only, not production capacity or PostgreSQL restore guarantees.

Launch requires working Linux containers, a restored PostgreSQL rehearsal, real sandbox payment/AI/mail/WhatsApp/video/coding acceptance, TLS/subdomain configuration, worker-failover tests and sustained representative load. Optional Prometheus rules need an Alertmanager destination. Define execution-history retention and operational ownership before launch.

No public production deployment is performed by creating the ZIP or pushing a release branch. The repository's main-branch deployment workflow remains separate. Review and stage the branch before merging it.

The local Docker Desktop startup attempt failed while initializing its inference-service listener (`dockerInference`). No containers or PostgreSQL staging acceptance were completed. Do not factory-reset Docker or remove data volumes to work around this release gate; repair the host or use a separate staging host.

The upstream repository tree also contains a tracked `.secret_key` file. The release snapshot excludes it and other private runtime files, but a release branch cannot erase historical exposure. Review and rotate any previously tracked credentials that were used outside development before launch.

## Documentation map

- [Runtime/deployment/recovery runbook](PRODUCTION_RUNTIME.md)
- [Demo data and feature acceptance matrix](DEMO_FEATURE_MATRIX.md)
- Existing [build manual](../BUILD.md), [architecture notes](../CLAUDE.md) and [deployment guide](../deploy/README.md)

## Distribution

Run `python scripts/package_saas_release.py` to produce a reviewed source snapshot and ZIP under `deliverables/`. `RELEASE_MANIFEST.json` lists every included source file and SHA256. The adjacent `.sha256` file identifies the archive. Runtime databases, generated role passwords, private environment files, service-account credentials, dependencies and compiled outputs are excluded. Run the demo seeder after extracting to create fresh local test data.

Mobile Firebase configuration files are also excluded; provision project-specific files during the mobile build. The archived Flutter source is included, but this runtime release does not claim an Android/iOS store-build acceptance test.

The source-only release also omits the legacy root WordPress theme/static-site export, duplicate nested repository, generated frontend builds and historical transcript/dump files. They remain in the original download and Git history; no live uploaded files, data volumes or production pages are deleted by packaging or pushing this separate branch.
