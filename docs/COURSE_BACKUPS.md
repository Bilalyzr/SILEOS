# Course Upload & Backup

Open **Content Studio → Course Upload & Backup** as an instructor, or the corresponding course-content entry as an administrator.

Routes: `/instructor/course-packages` and `/admin/course-packages`.

## Create a course from files

1. Select PDF, DOCX, TXT, Markdown, MP4, WebM, MP3 or WAV files.
2. Choose **Detect and preview upload**. Each file becomes one draft lesson.
3. Review the proposed title, lesson outline and import warnings.
4. Choose **Create draft course from files** and open the course editor.
5. Review the lessons, arrange sections, add assessments, and publish through the existing course workflow.

Limits: up to 30 files, 200 MB combined. Text documents are limited to 400,000 extracted characters per lesson. PDF/Word text extraction does not preserve page layout or embedded images, and scanned PDFs require OCR beforehand. Uploaded video/audio is retained for the lesson player; this workflow does not automatically transcribe it. Classroom recording transcription remains in Recording Lessons.

## Back up and restore a course

1. Select a course you can edit and choose **Download course backup**.
2. Keep the downloaded `course-ID.sasha-course.zip` in your backup storage.
3. Upload that file to Course Upload & Backup. The server recognizes the manifest, validates the format version, and checks payload and asset checksums.
4. Review the preview and warnings, optionally change the title, and choose **Restore as new draft course**.

Restore always creates a **new draft owned by the restoring instructor/admin**. It never replaces an existing course. Repeating the restore request for the same preview returns the already-created course rather than creating a duplicate. Restored lessons also require review before publication.

## Contents of a portable course backup

Included: course metadata and custom tool selections; sections and lesson ordering; lessons and supported local uploaded assets; quizzes, questions and answer keys; assignments and rubrics; concept links and course outcomes; Studio settings and Assessment Studio drafts; referenced games, H5P packages, GeoGebra applets and GLB models.

IDs and relationships are remapped during restore. Games and assessment material remain drafts. Interactive assets use the existing validators and quotas. GeoGebra's free-course restriction and the 3D course-type restriction still apply.

The September 7 repair also includes quiz 3D tasks and their model dependencies.
Retired quiz labs are preserved as draft lesson investigations using the supplied
replacement simulations, with a warning to review grading. Course lesson links
are remapped to the supplied catalog. See `RESTORE_GUIDE.md` at the repository root.

Excluded: learner accounts, enrollments, submissions, grades, attempts, payment/order records, live-class attendance, and recording workbench/history. Private source data is not copied into a distributable course file.

Remote YouTube/Bunny/CDN URLs stay references. Their media bytes and external service credentials are not downloaded into the ZIP. Missing or external local-style references are shown as warnings. A course backup is therefore distinct from a complete server recovery backup.

## Storage and limits

- Private staging: sibling `course_transfers/` directory beside the configured uploads directory.
- Preview window: 24 hours; up to five active previews per instructor.
- Expired staged files are reclaimed in bounded batches when the upload/history endpoints are used. Restore history and the resulting course remain intact. Old orphaned staging directories left after account deletion are also reclaimed. This is not a scheduled background deletion job.
- Restored local assets: `uploads/course-restores/<transfer-id>/`; H5P and GLB assets use their existing application storage paths.
- Archives: maximum 200 MB compressed/uploaded, 500 MB expanded, 10,000 entries, and 5,000 items per bounded group. Unsupported paths, symlinks, encrypted archives, duplicate entries, unsupported versions and checksum mismatches are rejected.
- Format v1: `manifest.json`, `course.json`, `assets/`. Checksums verify integrity; they are not a digital signature of the source instructor.

## Deployment and full recovery

Course packages now include authored concept-lab configurations referenced by lessons. Restore assigns new lab identifiers and creates private drafts owned by the restoring author; review and publish those labs before making the course available. Bundled lab references require the matching destination catalog. See [Learning labs and redesign](LABS_AND_REDESIGN.md). Revision 0027 adds private investigation notebooks.

Install `backend/requirements.txt` (includes `bleach==6.2.0`) and run `alembic upgrade head`. Revisions 0024–0026 introduce transfer/heartbeat storage, map legacy course tool settings, and preserve deletion behavior for courses/accounts. The PostgreSQL SQL parity script is `backend/migrations/20260906_operations_course_packages.sql`; use one managed migration approach rather than independently maintaining both.

A full system backup must also preserve PostgreSQL, uploads, certificates, H5P/GLB storage, recordings, and the deployment's secret/configuration storage. Do not distribute a database backup as a course package.

`backend/scripts/rehearse_course_restore.py` tests course restore and `pg_dump`/`pg_restore` on **new localhost databases whose names end in `_rehearsal`**. It refuses to seed a database with existing users or bootstrap a nonempty database. Supply `--pg-bin`, `--output`, `--restore-db`, and optionally `--bootstrap`. Its output includes the database version, table checks, backup size and SHA-256. The original application tables are owned by `init_db/create_all`; the Alembic baseline alone does not build that legacy schema.
