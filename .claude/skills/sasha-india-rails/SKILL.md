---
name: sasha-india-rails
description: Government and registrar integrations in India
---

Blueprint 13.3 India rails. Load for DigiLocker/APAAR/ABC/UDISE+/Bhashini work.

- None are built. Each gates a commercial motion (verification, credit transfer, school onboarding, vernacular reach).
- STANDING RULE: verify the CURRENT API specification from the operator before writing a line — training data is stale for all of these. Record the spec version and date in the feature doc.
- Aadhaar-adjacent anything (APAAR/DigiLocker auth): treat as high-sensitivity PII — purpose limitation, minimal data, no logging of identifiers, explicit consent flows. When in doubt, ask the owner; never improvise.
- DPDP Act 2023 applies regardless: consent management, data-principal rights (access, correction, erasure), and VERIFIABLE PARENTAL CONSENT for under-18s — the big one for K-12.
