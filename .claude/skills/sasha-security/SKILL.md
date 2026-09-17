---
name: sasha-security
description: Hardening, uploads, and auth surfaces
---

Blueprint 13.2 + this repo's live patterns. Load for security-sensitive work.

- Uploads: validate magic bytes not extensions; uuid names; store OUTSIDE public dirs when private (the backend/ebooks pattern); path reassertion after join; size caps; delete the stored blob AFTER commit, never orphan the new one on rollback.
- Private files stream through authenticated endpoints with Cache-Control private no-store; the download filename is the sanitized slug, NEVER the stored path.
- Authz: every route declares its dependency; cross-owner references 403; drafts and unpublished inventory 404 to non-owners (no existence leak).
- Money endpoints: persist intent BEFORE gateway calls; idempotent convergence on gateway ids; never trust client amounts.
- Webhooks: signature verified, handlers idempotent.
- OWASP dependency audit in CI; SBOM when it lands.
