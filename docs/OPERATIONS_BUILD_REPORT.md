# Operations, course recovery and mobile learning — 2026-09-06

## Delivered

**Course Upload & Backup** creates draft courses from documents, video and audio; recognizes versioned course backups; previews contents and warnings; restores new courses with remapped IDs/assets; and supports private upload history and cleanup. See [COURSE_BACKUPS.md](COURSE_BACKUPS.md).

**Admin Operations Center** (`/admin/operations`) groups daily approval/grading/intervention/recording queues, searchable and sortable paginated data, matching CSV exports, course completion and delayed-check outcomes, payment/refund/subscription reporting, and operational health. CSV cells are protected against spreadsheet formula evaluation. Date changes cannot allow an older revenue request to overwrite the current report.

Health reports database reachability, upload-disk capacity, transcription configuration/job counts, and actual recording-worker/payment-reconciliation heartbeats. Missing/stale heartbeats are explicitly unknown/stale. It does not claim to probe every infrastructure service. Revenue separates currencies and captured cash from refunds by their actual timestamps; subscription MRR is labeled an estimate. Delayed-score comparisons use verified practice/follow-up evidence and report unknown when insufficient.

**Mobile learning workspace** is available from the Dashboard: goal creation/editing/pausing, daily tasks and snoozing, course-lesson navigation, practice/delayed checks including multiple selections, and instructor intervention reviews with notes. Ended live classes link to searchable recording transcripts, chapters and notes, with playback obtained from the existing authorized recording endpoint. Transcript timestamps are displayed; mobile chapter-to-player seeking is not implemented. Advanced course authoring and package management are available in the responsive web Content Studio.

**Frontend quality**: removed unused code/imports, corrected incompatible API/types and hook dependencies, and cleared the existing TypeScript/lint backlog without weakening rules. Fixed public-role handling, course editor null-state updates and publish-after-save behavior, plus missing API imports and UI props. The new screens have automated interaction tests.

**Mobile foundations**: completed existing catalog API signatures, restored generated model/provider files, connected the unfinished monthly chart to the existing revenue time series, bundled checksum-verified Inter/Plus Jakarta Sans fonts with OFL licenses, and repaired the screenshot harness. Added safe desktop login decoration, offline avatar fallbacks and a retryable quiz-start error instead of an unsafe navigation pop.

## Verified

- Web: **343 tests passed** across 54 files; TypeScript and production bundle succeeded. Lint also passes with zero warnings; the final check is recorded in `frontend/operations-final-lint.log`.
- Flutter web release compilation succeeded at `flutter_app/build/web`; existing plugins emit WebAssembly compatibility notices. This is a JavaScript web build, not an Android/iOS release.

- Local preview database backed up before migrations 0024, 0025 and 0026; current schema is 0026.
- Real preview course **11**, `[Demo] Course Upload and Restore`, created as a draft through the upload screen. Original course content was preserved.
- Focused backup/migration additions: **23 passed**, covering documents and Unicode, media, authorization, checksums, unsafe paths, idempotence, rollback, expired-file cleanup, interactive games/H5P/GeoGebra/GLB round trips, custom tools, migration reentrancy, and course/account deletion behavior.
- Complete backend release run: **1,635 passed, 4 skipped**. A final package-only run passed **17 tests**, including the subsequently added timezone-offset expiry regression. Migration compatibility respects the legacy `create_all` contract. No production database was used.
- Flutter: **48 tests passed**, including 26 screen captures and 5 new learning/reporting contract tests. Android/iOS device playback and release installation are still unverified.
- PostgreSQL **15.19**: initialized an isolated legacy checkpoint, upgraded 0020 through **0026**, restored a portable course, dumped the database, restored into a second fresh database, compared all **129 table counts**, and checked Tamil content. Result: `.toolchains/release-restore-rehearsal/result.json`.
- Final recovery dump: **547,761 bytes**, SHA-256 `296c4d5c0aabdbc1102903dd66849cc9f663a0e7cc76c86ba01f9e42fb48d89d`. Rehearsal data is disposable and contains no production records.

## Runtime and remaining checks

React preview remains on port 3002, API on 8012, restarted with the final package changes. The worker uses the workspace multilingual `small` model in the separate transcription virtual environment. The other checkout on ports 3001/8011 was left alone. The isolated PostgreSQL rehearsal server was stopped after verification. Production dependencies must be installed from requirements; `.astra-tools` is a local validation/runtime aid, not a deployable dependency bundle.

The compatible local mobile toolchain is Flutter **3.35.7 / Dart 3.9.2**. The newer tested SDK could not run this repository's existing generator versions. The Android SDK is absent on this computer; no APK or iOS-device verification is claimed. Existing mobile analyzer deprecations/style warnings remain separate from compile errors.

Real English/Tamil classroom transcription accuracy still requires the user's recording paths. Synthetic English and Tamil text/search handling are not a substitute for that acoustic validation.

Final administrator browser verification is awaiting explicit account approval. Automatic approval review rejected the local demo administrator sign-in and a subsequent credential-verification attempt; neither was executed. Existing automated authorization tests and the earlier course-upload browser check remain valid evidence. No production deployment, git push or PR merge was performed.
