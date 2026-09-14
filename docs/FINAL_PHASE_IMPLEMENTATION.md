# Final phase: pricing, course links, imports and performance

Implemented locally on 6 September 2026. No production deployment or live payment was performed.

## Admin pricing and paper generation

- Admin → Commerce → **Exam paper pricing** (`/admin/exam-pricing`). Create separate JEE and NEET slabs with a name, inclusive question-count range, INR price per paper and publication toggle. Delete removes a slab from new purchases while preserving existing purchases.
- Ranges support 5–180 questions. Active ranges for the same exam cannot overlap. Prices are stored as integer paise. There are no seeded or hardcoded selling prices; admins choose them.
- Students → **Practice papers** (`/exam-papers`). Students must pay for each JEE/NEET paper. Staff → Assessment & Support → **Paper generator** uses the same workspace without payment.
- Staff can paste source text or import PDF/TXT/MD up to 10 MB, 120 PDF pages and 80,000 characters. Extracted text is reviewable before generation. Scanned PDFs require OCR for question generation. Sources are private to the owner and are not published as upload URLs.
- A checkout stores its exam, question count, input and price. Editing/deleting pricing cannot change an existing checkout. Verification uses the stored order ID, HMAC signature and captured payment amount/currency. Gateway payment IDs cannot be reused.
- Verified payments create the normal order, line item and payment records. The existing webhook, reconciliation and refund workflows handle paper purchases. **Check payment** recovers a lost checkout callback. A refund revokes delivery.
- Generation runs in background batches of ten and validates the exact count, answer format and duplicate questions. Failed generation retries the same paper without a new payment. Completed papers are reused, not generated again. Staff output is saved to question banks as `ai-draft`; student output stays private.
- Interrupted generation expires after a 60-minute lease and becomes retryable when viewed. Generation identifiers prevent an older worker from overwriting a retry. This uses the application's background-task process, not a separate durable worker fleet.
- Completed papers show optional answers and support **Print / Save PDF** through the browser.

### Activation

1. Publish the required pricing slabs in the admin screen.
2. Configure the existing backend AI provider (`GLM_API_KEY`, optionally `GLM_MODEL`). The local preview currently has no configured AI provider and correctly disables generation/checkout.
3. Configure the existing Razorpay integration (`RAZORPAY_KEY` + `RAZORPAY_SECRET`, or the legacy ID/secret pair), webhook secret and delivery endpoint. Verify the gateway in test mode before enabling live sales. No credentials are supplied by this change.

Payment verification follows [Razorpay's standard integration flow](https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/integration-steps/).

## Custom course URLs

Course start, legacy instructor creation, admin creation and the course editor have a **Custom course link** field with a 350 ms debounced availability check. The server validates and normalizes the slug and enforces case-insensitive uniqueness through a database index. Draft/private course links are reserved too. Numeric and reserved routes are rejected. Editing a title preserves the existing course URL. Numeric course IDs remain valid.

## Asset imports

Course Upload & Backup now classifies Text, Document, Image, Audio, Video, 3D model, H5P, Game, GeoGebra and Virtual lab lessons in previews. Standalone PDF/DOCX/TXT/MD, PNG/JPEG/WebP/GIF, MP4/WebM, MP3/WAV and GLB files are supported. H5P/lab packages use their existing specialized libraries or a full course backup.

Original documents and images are retained as Resources. PDFs can retain scanned pages without inventing extracted text. Images render in lesson content; audio/video use the existing media player. GLB files become private model-library entries linked to 3D lessons. File content, size, model format and staged checksums are validated before restore. Existing backups remain version 1 and restore to new draft courses.

## UI performance

147 existing page modules now load on demand. The main application production bundle fell from **3,997.65 kB to approximately 246 kB** (uncompressed; shared vendor and selected-page bundles are additional). Repeated lab/course cards avoid per-item background blur. Vite uses native filesystem notifications; Docker/network mounts can opt into polling with `VITE_USE_POLLING=true`.

These are measured improvements, not a guarantee of zero latency on every device or network. Video and 3D viewer chunks remain large and load with those features.

## Migration and verification

- Alembic **0028** adds paper/pricing tables and the course-link unique index. It refuses existing duplicate links rather than silently renaming URLs. Apply before serving the updated application.
- This workspace's `backend/visual_qa.db` was backed up and migrated to 0028. Preview API: `127.0.0.1:8012`; frontend: `127.0.0.1:3002`.
- Backend: **136 relevant tests passed**, including payment/refund/reconciliation, staff sources, retry isolation, slug conflicts and mixed-file restores. External AI/payment services were mocked.
- Frontend: **373 tests passed**; lint and type checks passed; production build passed. Generated lab check: **59 labs / 142 files**.
- Browser: student, instructor and admin workflows checked at desktop/mobile sizes; slab create/delete, source upload, generation display, answer reveal, URL availability and menu layering exercised with isolated API fixtures. **17 public screens** passed desktop/mobile smoke checks. The live instructor paper screen was also inspected.
- Local evidence: `backend/astra-phase-regression-final.log`, `frontend/astra-phase-*-final.log`, `.toolchains/lab-qa/final-phase-results/`, `.toolchains/lab-qa/redesign-results/`.
