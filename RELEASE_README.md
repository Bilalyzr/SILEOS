# SashaInfinity LMS + SILeos portable handover

**Labs/3D import repair:** read `RESTORE_GUIDE.md` first and see
`docs/releases/2026-09-07-lab-repair.md` for the corrected package and checks.

Release date: **2026-09-07**. Read `docs/releases/2026-09-07.md` for Codex notes,
verification results, features, exclusions and remaining launch prerequisites.

## Application setup

1. Extract into a new directory. Install Git, Node.js 22, Python 3.11+, Docker and
   Docker Compose as needed. Flutter setup is documented under `flutter_app/`.
2. Copy `.env.example` to `.env` and supply your database, JWT, payment and provider
   settings. Do not reuse credentials from examples or demo seed scripts.
3. Consult `BUILD.md` for Docker setup and `docs/PLATFORM_SCHEMA.md` for migrations.
   The base Compose stack serves the web frontend through nginx on port 3100.
   Read the selected Compose file before starting it; production scripts are not
   required to preview this release.
4. For a host frontend, run `npm install --legacy-peer-deps` in `frontend/`, then
   `npm run dev`. Configure `VITE_PROXY_TARGET` to your API (default
   `http://localhost:8000`) and `VITE_DEV_PORT` to choose a nondefault frontend port.
   The previous machine's preview used frontend 3002 and backend 8012; those running
   processes and local configuration are not part of the archive.
5. Install backend requirements in your own virtual environment. With the target
   `DATABASE_URL` configured and a backup made, run `alembic upgrade head` from
   `backend/`. Head is `0029`. Start `uvicorn app.main:app` using your intended port.
6. Provision your own accounts and course data. Private databases and user uploads
   are intentionally excluded. Public source lab assets and seed packs are included.

Keep the outer `backend/` and `frontend/` as the source of truth. Never run a
production deployment/prune script just to open this handover locally.

## Creative assets

Open `output/video/SILeos/PREVIEW.html` through a local static web server, or play
`SILeos-Coming-Soon-1080p.mp4` and `SILeos-WhatsApp-720p.mp4` directly in that folder.
The same folder contains the complete rebuild prompt, script, brand assets and
public product screenshots/recordings.

For a portable video editor project, use `output/video/SILeos/editable-project/`.
With Node.js installed, run `npm run dev` there. HyperFrames 0.8.30 is pinned in its
package file. Fonts, audio and GSAP are already local; no signed download URLs or
provider login are needed to reuse the included assets. Network is needed on first
use to obtain the editor/runtime. Original production helper scripts under
`videos/sileos-launch/` can contain machine-specific capture paths; the standalone
editable project is the portable rendering entry point.

## Verify and reproduce the archive

The release ZIP includes `RELEASE_MANIFEST.json` with the source commit and per-file
SHA-256 checksums. A separate `.sha256` file gives the whole ZIP checksum.
From a Git checkout of the desired commit:

```sh
python scripts/export_release.py --date 2026-09-07
```

This exports exactly `HEAD` into `output/releases/`, verifies the archive CRC and
each included file hash, and writes a manifest alongside it. Commit intended source
changes first. Local untracked/private files and Git history are not exported.
