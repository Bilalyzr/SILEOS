# Sasha Build Kit — skill index

21 self-authored skills distilled from `SILEOS_Master_Blueprint.md` and the live Sasha LMS codebase. Format: `.claude/skills/<name>/SKILL.md` with frontmatter (name, description). Load by topic match on the description.

## Tier 1 — load every session
| Skill | Covers | Distilled from |
|---|---|---|
| `sasha-conventions` | Definition of done, testing honesty, reporting protocol | Build brief (SILEOS_Z_AI_Build_Prompt §1/§3) |
| `sasha-wp-protocol` | Executing a scoped build: plan → increments → gates → ledger | Build brief §1 "How you will work" + superpowers pipeline docs |
| `sasha-architecture-map` | Where code goes: repo layers, placement rules | Blueprint §6 + repo reality |

## Tier 2 — load when touching that subsystem
| Skill | Covers | Distilled from |
|---|---|---|
| `sasha-tenancy-rls` | tenant_id, RLS-at-the-DB, breach vectors | Blueprint §7.4, §13.2 |
| `sasha-component-registry` | Adding lesson content types — the seven seams | Blueprint §3.2/§3.3 + repo lessonContentSync contract |
| `sasha-assessment-rules` | Quiz engine invariants, grading, banks | Blueprint §3.4 + quiz-engine spec 2026-09-03 |
| `sasha-elearning-standards` | xAPI spine (live), SCORM/LTI deferred | Blueprint §3.5, §9.6 |
| `sasha-3d-pipeline` | Ingestion chain, hard budgets, malicious files | Blueprint §8.4 |
| `sasha-ilo-authoring` | ILO manifest, parameter-based assessment | Blueprint §8.1 |
| `sasha-tier-ladder` | T0–T7 degradation, marks-at-every-tier rule | Blueprint §8.6 |
| `sasha-webxr` | XR sessions, safety, no-headset-gates | Blueprint §13.4 |
| `sasha-particle-sim` | GPU sims, determinism reality, probe grading | Blueprint §8.5.1 + critique ADR-0001.7 |
| `sasha-geogebra` | Applets, free-course rule, licence status | Blueprint §8.3 + the 2026-09-04 integration |
| `sasha-h5p` | Adopt-don't-rebuild, sandbox rules | Blueprint §8.5.2 + repo h5p router |
| `sasha-ai-services` | AI governance four rules, 503-not-fake | Blueprint §15 + routers/ai.py |
| `sasha-india-rails` | DigiLocker/APAAR/Bhashini, verify-spec-first | Blueprint §13.3 |
| `sasha-mobile-offline` | Sync queue, conflict policy, offline-first | Blueprint §3.12 |
| `sasha-architecture-map` (above) | — | — |

## Tier 3 — load when auditing or hardening
| Skill | Covers | Distilled from |
|---|---|---|
| `sasha-a11y` | WCAG 2.2 AA checkables, keyboard parity | Blueprint §3.13 |
| `sasha-perf-budget` | Device budgets, measure-don't-estimate | Blueprint §8.4, §13.1 |
| `sasha-security` | Uploads, authz, money-path safety | Blueprint §13.2 + repo patterns |
| `sasha-data-rights` | DPDP/GDPR erasure across every store | Blueprint §13.3 |

## Maintenance rule
When the same mistake happens twice in one area, fix the SKILL, not just the code — see `Sasha_Build_Kit_Bootstrap.md` "Maintenance".

## Confidence + inferences
See `CONFIDENCE_REPORT.md` beside this file — the inferences listed there are the spots the owner should check first.
