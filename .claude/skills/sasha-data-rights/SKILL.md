---
name: sasha-data-rights
description: Compliance: DPDP, GDPR, erasure requests
---

Blueprint 13.3. Load for data deletion, export, or compliance work.

- DPDP Act 2023 (primary market): consent records, purpose limitation, data-principal rights — access, correction, ERASURE. Verifiable parental consent for under-18s is the K-12 blocker.
- GDPR if any EU learner: export and deletion workflows, DPA, breach notification.
- Erasure must cover EVERY store: Postgres rows, object storage (ebook blobs), search index, xAPI statements, and a documented backup policy. Partial erasure IS failed erasure — enumerate the stores before claiming done.
- Deletion safety versus rights (sold ebooks not deletable, grade retention): delete PERSONAL data, keep transactional records pseudonymised; document each exception.
- Audit-log the erasure itself (who, when, scope).
