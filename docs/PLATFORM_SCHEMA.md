# SashaInfinity LMS â€” Complete Platform Schema

> Auto-generated from the SQLAlchemy models on branch `digital-library` @ 9d94336 (2026-09-03), which is `revenue-platform` @ 00c267c plus the in-progress Digital Library tables. **The models in `backend/app/models/` are the source of truth**; regenerate this file after schema changes (script pattern: import `app.models`, walk `Base.metadata.tables`).

## How schema changes work in this repo (READ FIRST)

- **Two parallel paths, keep them consistent:** `init_db()` (`app/core/database.py`, called at startup) runs `create_all()` from the models â€” fine for FRESH databases only. Existing databases are migrated with **Alembic** (`backend/alembic/`, `alembic upgrade head`). Every migration since `0002` uses guarded `has_table`/`has_column` checks and `batch_alter_table` for SQLite column/constraint changes. Never rely on `create_all` to alter an existing table.
- Migration chain: `0001` (baseline stamp) â†’ `0002` (live classes) â†’ `0003` (learning experience) â†’ `0004` (learning games) â†’ `0005` (digital library, in progress).
- Some older commerce tables (coupons, memberships, bundles, company invoicing) were added via raw SQL files in `backend/migrations/*.sql` applied manually â€” see CLAUDE.md.
- SQLite (tests/dev) returns tz-naive datetimes; production is Postgres 15. Prices are stored in **rupees** (`Numeric(10,2)` for courses/bundles, `Integer` whole-rupees for ebooks); paise conversion (`int(round(price*100))`, min 100) happens only at the Razorpay boundary.

## Feature-area map (which tables belong to what)

| Area | Tables | Owner code |
|---|---|---|
| Identity & auth | users, instructor_profiles, user_sessions(+related) | app/models/user.py, services/auth_service.py (JWT + TOTP for admins) |
| Courses & content | courses, lessons, enrollments, lesson_progress, student_course_activity, categories/tags tables | app/models/course.py, enrollment.py; lessons carry `lesson_content_type` âˆˆ {video,h5p,game} with `h5p_content_id`/`game_id` FKs validated as ATOMIC PAIRS in courses.py `_resolve_lesson_content_fields` |
| Assessment | quizzes, quiz_questions, quiz_question_answers, quiz_attempts, assignments, assignment_submissions | app/models/quiz.py, assignment.py; server-side timers, manual grading queue, gradebook.py |
| Commerce core | orders, order_items, payments, webhook_events, coupons | Triple-redundant fulfillment: /verify + webhook inbox + reconciliation sweeper, all idempotent on `Payment.gateway_payment_id` converging in fulfillment_service.py. `orders`/`order_items` accept exactly one of course/bundle/invoice/(ebook â€” in progress); `order_items.course_id` is NULLABLE as of 0005 (ebook lines) |
| Memberships | membership_tiers, membership_subscriptions (+ enrollment rows with enrollment_source='membership') | models/membership.py, services/membership_access.py; Razorpay Subscriptions; suspend on lapse, never touch rows with order_id |
| Bundles & seats | bundles, bundle_courses (+ cohort seat_price) | models/bundle.py; fulfillment snapshot in order notes |
| Company portal & invoicing | companies, company_* tables, internships, company_invoices, company_seat_pools | models/company*.py, invoice_service.py (GST, idempotent settle_invoice, private PDFs) |
| Live classes | live_class_schedules, live_classes, live_class_join_tokens, live_class_attendance, live_class_polls, live_class_poll_votes, live_class_events | models/live_class.py; self-hosted Jitsi, backend-minted room-pinned JWTs (JITSI_JWT_SECRET â‰  platform JWT_SECRET), recordings â†’ Bunny |
| H5P | h5p_contents, h5p_results | models/h5p.py; untrusted zips hardened server-side; player iframe sandbox="allow-scripts" ONLY (never allow-same-origin); advisory scores |
| Certificates | certificates (+ designer template storage) | elements_config JSON â†’ certificate_html_renderer.py â†’ headless-Chrome (ReportLab fallback); strict allowlists |
| Gamification | xp_events, user_game_stats, badges, user_badges | services/gamification_service.py â€” event-sourced, `award()` is FLUSH-ONLY (caller owns the transaction), idempotent UNIQUE event_key, SAVEPOINT duplicate isolation; ~16 badges; opt-out leaderboard, never leaks email |
| Learning games | games, game_results (+ lessons.game_id) | models/game.py, routers/games.py, schemas/game_config.py (strict per-template validation, 64KB cap); max_score DERIVED (10Ã—items), never stored; advisory scores; docs/LEARNING_GAMES.md |
| Digital library (IN PROGRESS) | ebooks, ebook_grants (+ orders.ebook_id, order_items.ebook_id) | models/ebook.py, services/library_storage.py (private files under backend/ebooks/, magic-byte validation); spec+plan in docs/superpowers/; Tasks 3-12 unbuilt |
| Misc | blog posts, wishlists, carts, instructor_reviews, page_views, notifications, candidates, cohorts | various |

## Full table reference (auto-generated)


<!-- AUTO-GENERATED from SQLAlchemy models â€” 90 tables -->

### `admin_impersonation_logs`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| admin_user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| target_user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| started_at | DATETIME | NOT NULL, server_default |
| ended_at | DATETIME |  |
| reason | TEXT |  |
| actor_role | VARCHAR(32) | indexed, default='admin' |

Constraints/indexes: INDEX(actor_role); INDEX(admin_user_id); INDEX(id); INDEX(target_user_id)

### `assignment_submissions`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| assignment_id | INTEGER | FK â†’ assignments.id, NOT NULL |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| text_content | TEXT | default='' |
| files | JSON | default=[] |
| is_late | BOOLEAN | NOT NULL, default=False |
| grade | NUMERIC(9, 2) |  |
| feedback | TEXT | default='' |
| status | VARCHAR(9) | NOT NULL, default=<SubmissionStatus.SUBMITTED: 'submitted'> |
| rubric_scores | JSON |  |
| graded_by | INTEGER | FK â†’ users.id |
| graded_by_role | VARCHAR(20) |  |
| submitted_at | DATETIME | server_default |
| graded_at | DATETIME |  |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); UNIQUE(assignment_id, user_id)

### `assignments`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| course_id | INTEGER | FK â†’ courses.id, NOT NULL |
| created_by | INTEGER | FK â†’ users.id, NOT NULL |
| title | VARCHAR(200) | NOT NULL |
| description | TEXT | default='' |
| instructions | TEXT | default='' |
| due_date | DATETIME |  |
| total_points | INTEGER | default=100 |
| allowed_file_types | JSON | default=[] |
| max_file_size | INTEGER | default=10 |
| max_files | INTEGER | default=5 |
| submission_type | VARCHAR(50) | default='both' |
| attachments | JSON | default=[] |
| late_policy | VARCHAR(10) | NOT NULL, default='allow' |
| late_penalty_pct | INTEGER | NOT NULL, default=0 |
| rubric | JSON | default=[] |
| status | VARCHAR(9) | NOT NULL, default=<AssignmentStatus.PUBLISHED: 'published'> |
| order | INTEGER | default=0 |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id)

### `badges`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| slug | VARCHAR(60) | NOT NULL, UNIQUE, indexed |
| name | VARCHAR(120) | NOT NULL |
| description | VARCHAR(255) | NOT NULL, default='' |
| icon | VARCHAR(40) | NOT NULL, default='award' |
| rule_type | VARCHAR(40) | NOT NULL |
| rule_value | INTEGER |  |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); UNIQUE INDEX(slug)

### `blog_comments`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| blog_post_id | INTEGER | FK â†’ blog_posts.id, NOT NULL |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| content | TEXT | NOT NULL |
| status | VARCHAR(20) | default='APPROVED' |
| created_at | DATETIME |  |
| updated_at | DATETIME |  |

Constraints/indexes: INDEX(id)

### `blog_posts`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| author_id | INTEGER | FK â†’ users.id, NOT NULL |
| title | VARCHAR(500) | NOT NULL |
| slug | VARCHAR(500) | NOT NULL, UNIQUE, indexed |
| content | TEXT | NOT NULL |
| excerpt | TEXT |  |
| featured_image | VARCHAR(500) |  |
| status | VARCHAR(20) | default='DRAFT' |
| post_date | DATETIME |  |
| post_modified | DATETIME |  |
| meta_title | VARCHAR(500) |  |
| meta_description | TEXT |  |
| category | VARCHAR(100) |  |
| tags | VARCHAR(500) |  |
| related_course_ids | VARCHAR(500) |  |
| related_internship_ids | VARCHAR(500) |  |
| view_count | INTEGER | default=0 |
| comment_count | INTEGER | default=0 |
| created_at | DATETIME |  |
| updated_at | DATETIME |  |

Constraints/indexes: INDEX(id); UNIQUE INDEX(slug)

### `bundle_courses`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| bundle_id | INTEGER | FK â†’ bundles.id, NOT NULL, indexed |
| course_id | INTEGER | FK â†’ courses.id, NOT NULL |

Constraints/indexes: INDEX(bundle_id); INDEX(id)

### `bundles`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| name | VARCHAR(200) | NOT NULL |
| description | TEXT | default='' |
| slug | VARCHAR(255) | NOT NULL, UNIQUE, indexed |
| bundle_price | NUMERIC(10, 2) | NOT NULL |
| is_active | BOOLEAN | NOT NULL, default=True |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); UNIQUE INDEX(slug)

### `candidate_eligibility`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL, UNIQUE, indexed |
| source | VARCHAR(32) | NOT NULL |
| eligible | BOOLEAN | NOT NULL, default=True |
| reason | TEXT | default='' |
| decided_by | INTEGER | FK â†’ users.id |
| decided_at | DATETIME | server_default |
| cohort_id | INTEGER | FK â†’ cohorts.id |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(source, eligible); UNIQUE INDEX(user_id)

### `candidate_profiles`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL, UNIQUE, indexed |
| is_visible | BOOLEAN | NOT NULL, default=False |
| resume_url | VARCHAR(500) | default='' |
| bio | TEXT | default='' |
| skills | JSON |  |
| preferred_roles | JSON |  |
| availability_date | DATE |  |
| linkedin_url | VARCHAR(500) | default='' |
| github_url | VARCHAR(500) | default='' |
| portfolio_url | VARCHAR(500) | default='' |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); UNIQUE INDEX(user_id)

### `certificate_element_templates`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| element_name | VARCHAR(255) | NOT NULL |
| element_type | VARCHAR(50) | NOT NULL |
| element_content | TEXT | default='' |
| element_image_url | VARCHAR(500) | default='' |
| element_styles | JSON | default={} |
| default_position_x | INTEGER | default=0 |
| default_position_y | INTEGER | default=0 |
| default_width | INTEGER | default=100 |
| default_height | INTEGER | default=50 |
| is_active | BOOLEAN | default=True |
| usage_count | INTEGER | default=0 |
| created_by | INTEGER | FK â†’ users.id, NOT NULL |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id)

### `certificate_verifications`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| certificate_id | INTEGER | FK â†’ issued_certificates.id |
| certificate_hash | VARCHAR(255) | NOT NULL |
| verified_by_ip | VARCHAR(45) | default='' |
| verified_by_user_agent | TEXT | default='' |
| verification_result | VARCHAR(50) | default='valid' |
| verified_at | DATETIME | server_default |

Constraints/indexes: INDEX(id)

### `certificates`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| post_author | INTEGER | FK â†’ users.id, NOT NULL |
| post_date | DATETIME | server_default |
| post_content | TEXT | default='' |
| post_title | TEXT | NOT NULL |
| post_excerpt | TEXT | default='' |
| post_status | VARCHAR(20) | default='publish' |
| post_name | VARCHAR(200) | indexed, default='' |
| post_modified | DATETIME | server_default |
| post_parent | INTEGER | default=0 |
| menu_order | INTEGER | default=0 |
| post_type | VARCHAR(20) | default='tutor_certificates' |
| certificate_orientation | VARCHAR(50) | default='landscape' |
| certificate_size | VARCHAR(50) | default='A4' |
| certificate_width | INTEGER | default=1400 |
| certificate_height | INTEGER | default=1080 |
| background_image | VARCHAR(255) | default='' |
| background_color | VARCHAR(7) | default='#ffffff' |
| title_font_size | INTEGER | default=48 |
| title_font_color | VARCHAR(7) | default='#000000' |
| title_font_family | VARCHAR(100) | default='Arial' |
| body_font_size | INTEGER | default=24 |
| body_font_color | VARCHAR(7) | default='#000000' |
| body_font_family | VARCHAR(100) | default='Arial' |
| elements_config | JSON | default={} |
| show_student_name | BOOLEAN | default=True |
| show_course_name | BOOLEAN | default=True |
| show_completion_date | BOOLEAN | default=True |
| show_certificate_id | BOOLEAN | default=True |
| show_instructor_signature | BOOLEAN | default=True |
| show_admin_signature | BOOLEAN | default=False |
| enable_qr_code | BOOLEAN | default=False |
| qr_code_size | INTEGER | default=100 |
| qr_code_position | VARCHAR(50) | default='bottom-right' |
| is_global | BOOLEAN | NOT NULL, default=False |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(post_name)

### `cohort_memberships`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| cohort_id | INTEGER | FK â†’ cohorts.id, NOT NULL, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| joined_at | DATETIME | server_default |

Constraints/indexes: INDEX(cohort_id); INDEX(id); INDEX(user_id); UNIQUE(cohort_id, user_id)

### `cohort_sessions`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| cohort_id | INTEGER | FK â†’ cohorts.id, NOT NULL, indexed |
| scheduled_at | DATETIME | NOT NULL |
| duration_minutes | INTEGER | NOT NULL, default=60 |
| topic | VARCHAR(500) | default='' |
| session_type | VARCHAR(32) | default='lecture' |
| created_by | INTEGER | FK â†’ users.id |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(cohort_id); INDEX(id)

### `cohorts`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| college_id | INTEGER | FK â†’ colleges.id, indexed |
| course_id | INTEGER | FK â†’ courses.id, indexed |
| spoc_user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| name | VARCHAR(255) | NOT NULL |
| slug | VARCHAR(255) | default='' |
| max_students | INTEGER | default=0 |
| seat_price | NUMERIC(10, 2) |  |
| starts_on | DATE |  |
| ends_on | DATE |  |
| is_active | BOOLEAN | NOT NULL, default=True |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(college_id); INDEX(course_id); INDEX(id); INDEX(spoc_user_id)

### `colleges`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| name | VARCHAR(255) | NOT NULL |
| slug | VARCHAR(255) | NOT NULL, UNIQUE, indexed |
| city | VARCHAR(100) | default='' |
| state | VARCHAR(100) | default='' |
| contact_name | VARCHAR(255) | default='' |
| contact_email | VARCHAR(255) | default='' |
| created_by | INTEGER | FK â†’ users.id |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); UNIQUE INDEX(slug)

### `companies`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| owner_user_id | INTEGER | FK â†’ users.id, NOT NULL, UNIQUE, indexed |
| name | VARCHAR(200) | NOT NULL |
| slug | VARCHAR(220) | NOT NULL, UNIQUE, indexed |
| website | VARCHAR(255) | default='' |
| industry | VARCHAR(100) | default='' |
| team_size | VARCHAR(50) | default='' |
| description | TEXT | default='' |
| logo_url | VARCHAR(500) | default='' |
| contact_email | VARCHAR(150) | NOT NULL, indexed |
| contact_phone | VARCHAR(30) | default='' |
| gstin | VARCHAR(20) | default='' |
| legal_name | VARCHAR(255) | default='' |
| billing_address | TEXT | default='' |
| state_code | VARCHAR(2) | default='' |
| is_approved | BOOLEAN | NOT NULL, indexed, default=False |
| approval_source | VARCHAR(20) | NOT NULL, default='self_serve' |
| approved_by | INTEGER | FK â†’ users.id |
| approved_at | DATETIME |  |
| rejected_at | DATETIME |  |
| rejection_reason | TEXT | default='' |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(contact_email); INDEX(id); INDEX(is_approved); UNIQUE INDEX(owner_user_id); UNIQUE INDEX(slug)

### `company_interests`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| company_id | INTEGER | FK â†’ companies.id, NOT NULL, indexed |
| candidate_user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| status | VARCHAR(20) | NOT NULL, indexed, default='interested' |
| company_message | TEXT | default='' |
| responded_at | DATETIME |  |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(candidate_user_id); INDEX(candidate_user_id, status); INDEX(company_id); INDEX(id); INDEX(status); UNIQUE(company_id, candidate_user_id)

### `company_invoice_items`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| invoice_id | INTEGER | FK â†’ company_invoices.id, NOT NULL, indexed |
| description | VARCHAR(255) | NOT NULL |
| course_id | INTEGER | FK â†’ courses.id |
| bundle_id | INTEGER | FK â†’ bundles.id |
| quantity | INTEGER | NOT NULL |
| unit_price | NUMERIC(10, 2) | NOT NULL |
| line_total | NUMERIC(12, 2) | NOT NULL |

Constraints/indexes: INDEX(id); INDEX(invoice_id)

### `company_invoices`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| company_id | INTEGER | FK â†’ companies.id, NOT NULL, indexed |
| invoice_number | VARCHAR(30) | UNIQUE |
| status | VARCHAR(9) | NOT NULL, default=<InvoiceStatus.DRAFT: 'draft'> |
| subtotal | NUMERIC(12, 2) | NOT NULL |
| cgst | NUMERIC(12, 2) | NOT NULL, default=0 |
| sgst | NUMERIC(12, 2) | NOT NULL, default=0 |
| igst | NUMERIC(12, 2) | NOT NULL, default=0 |
| total | NUMERIC(12, 2) | NOT NULL |
| tax_note | VARCHAR(255) | default='' |
| due_date | DATETIME |  |
| issued_at | DATETIME |  |
| paid_at | DATETIME |  |
| paid_via | VARCHAR(50) | default='' |
| payment_reference | VARCHAR(100) | default='' |
| pdf_path | VARCHAR(500) | default='' |
| notes | TEXT | default='' |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(company_id); INDEX(id); UNIQUE(invoice_number)

### `company_managers`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| company_id | INTEGER | FK â†’ companies.id, NOT NULL, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL, UNIQUE |
| invited_by | INTEGER | FK â†’ users.id |
| invited_at | DATETIME | NOT NULL, server_default |
| accepted_at | DATETIME |  |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(company_id); INDEX(id); UNIQUE(user_id)

### `company_seat_assignments`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| pool_id | INTEGER | FK â†’ company_seat_pools.id, NOT NULL, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| assigned_by | INTEGER | FK â†’ users.id, NOT NULL |
| assigned_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(pool_id); UNIQUE(pool_id, user_id)

### `company_seat_pools`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| company_id | INTEGER | FK â†’ companies.id, NOT NULL, indexed |
| invoice_id | INTEGER | FK â†’ company_invoices.id, NOT NULL, indexed |
| order_id | INTEGER | FK â†’ orders.id |
| course_id | INTEGER | FK â†’ courses.id |
| bundle_id | INTEGER | FK â†’ bundles.id |
| total_seats | INTEGER | NOT NULL |
| used_seats | INTEGER | NOT NULL, default=0 |

Constraints/indexes: INDEX(company_id); INDEX(id); INDEX(invoice_id)

### `coupon_course_restrictions`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| coupon_id | INTEGER | FK â†’ coupons.id, NOT NULL |
| course_id | INTEGER | FK â†’ courses.id, NOT NULL |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(id)

### `coupon_usage`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| coupon_id | INTEGER | FK â†’ coupons.id, NOT NULL |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| order_id | INTEGER | FK â†’ orders.id |
| discount_amount | NUMERIC(10, 2) | NOT NULL |
| used_at | DATETIME | server_default |

Constraints/indexes: INDEX(id)

### `coupons`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| code | VARCHAR(50) | NOT NULL, UNIQUE, indexed |
| description | TEXT | default='' |
| discount_type | VARCHAR(10) | NOT NULL |
| discount_value | NUMERIC(10, 2) | NOT NULL |
| applicability | VARCHAR(16) | NOT NULL, default='all_courses' |
| usage_limit | INTEGER |  |
| usage_count | INTEGER | NOT NULL, default=0 |
| per_user_limit | INTEGER | default=1 |
| minimum_purchase_amount | NUMERIC(10, 2) | default=0 |
| valid_from | DATETIME | server_default |
| valid_until | DATETIME |  |
| is_active | BOOLEAN | default=True |
| created_by | INTEGER | FK â†’ users.id, NOT NULL |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |
| cohort_id | INTEGER | FK â†’ cohorts.id |

Constraints/indexes: INDEX(id); UNIQUE INDEX(code)

### `course_announcements`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| course_id | INTEGER | FK â†’ courses.id, NOT NULL |
| post_author | INTEGER | FK â†’ users.id, NOT NULL |
| post_title | TEXT | NOT NULL |
| post_content | TEXT | default='' |
| post_excerpt | TEXT | default='' |
| post_status | VARCHAR(20) | default='publish' |
| post_date | DATETIME | server_default |
| post_modified | DATETIME | server_default |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id)

### `course_categories`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| name | VARCHAR(200) | NOT NULL, UNIQUE |
| slug | VARCHAR(200) | NOT NULL, UNIQUE |
| description | TEXT | default='' |
| parent_id | INTEGER | FK â†’ course_categories.id |
| term_order | INTEGER | default=0 |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); UNIQUE(name); UNIQUE(slug)

### `course_category_relations`

| column | type | constraints |
|---|---|---|
| course_id | INTEGER | PK, FK â†’ courses.id |
| category_id | INTEGER | PK, FK â†’ course_categories.id |

### `course_certificates`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| course_id | INTEGER | FK â†’ courses.id, NOT NULL |
| certificate_id | INTEGER | FK â†’ certificates.id, NOT NULL |
| required_completion_percentage | INTEGER | default=100 |
| required_quiz_pass | BOOLEAN | default=False |
| required_assignment_pass | BOOLEAN | default=False |
| auto_generate | BOOLEAN | default=True |
| email_to_student | BOOLEAN | default=True |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(id)

### `course_reviews`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| course_id | INTEGER | FK â†’ courses.id, NOT NULL |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| rating | INTEGER | NOT NULL |
| review_title | VARCHAR(255) | default='' |
| review_content | TEXT | default='' |
| review_status | VARCHAR(20) | default='approved' |
| status | VARCHAR(20) | NOT NULL, default='pending' |
| admin_notes | TEXT | default='' |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id)

### `course_tag_relations`

| column | type | constraints |
|---|---|---|
| course_id | INTEGER | PK, FK â†’ courses.id |
| tag_id | INTEGER | PK, FK â†’ course_tags.id |

### `course_tags`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| name | VARCHAR(200) | NOT NULL, UNIQUE |
| slug | VARCHAR(200) | NOT NULL, UNIQUE |
| description | TEXT | default='' |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); UNIQUE(name); UNIQUE(slug)

### `courses`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| post_author | INTEGER | FK â†’ users.id, NOT NULL |
| post_date | DATETIME | server_default |
| post_date_gmt | DATETIME | server_default |
| post_content | TEXT | default='' |
| post_title | TEXT | NOT NULL |
| post_excerpt | TEXT | default='' |
| post_status | VARCHAR(20) | default='draft' |
| comment_status | VARCHAR(20) | default='open' |
| ping_status | VARCHAR(20) | default='open' |
| post_password | VARCHAR(255) | default='' |
| post_name | VARCHAR(200) | indexed, default='' |
| to_ping | TEXT | default='' |
| pinged | TEXT | default='' |
| post_modified | DATETIME | server_default |
| post_modified_gmt | DATETIME | server_default |
| post_content_filtered | TEXT | default='' |
| post_parent | INTEGER | default=0 |
| guid | VARCHAR(255) | default='' |
| menu_order | INTEGER | default=0 |
| post_type | VARCHAR(20) | default='courses' |
| post_mime_type | VARCHAR(100) | default='' |
| comment_count | INTEGER | default=0 |
| course_price_type | VARCHAR(20) | default='free' |
| course_price | NUMERIC(10, 2) | default=0 |
| course_sale_price | NUMERIC(10, 2) | default=0 |
| course_duration | VARCHAR(255) | default='' |
| course_level | VARCHAR(50) | default='beginner' |
| course_category | VARCHAR(100) | default='' |
| course_language | VARCHAR(50) | default='English' |
| course_benefits | TEXT | default='' |
| course_requirements | TEXT | default='' |
| course_target_audience | TEXT | default='' |
| course_material_includes | TEXT | default='' |
| course_tags | TEXT | default='' |
| num_offline_workshops | INTEGER | default=0 |
| num_hours | INTEGER | default=60 |
| institution | VARCHAR(255) | default='' |
| course_thumbnail | VARCHAR(255) | default='' |
| course_cover_image | VARCHAR(255) | default='' |
| course_intro_video | VARCHAR(255) | default='' |
| course_retakes_allowed | BOOLEAN | default=True |
| course_auto_start_next_lesson | BOOLEAN | default=False |
| course_content_drip_type | VARCHAR(50) | default='none' |
| certificate_template | VARCHAR(255) | default='' |
| course_sections_meta | TEXT | default='' |
| course_type | VARCHAR(50) | default='' |
| certificate_design | JSON | default={} |
| total_enrollments | INTEGER | default=0 |
| average_rating | NUMERIC(3, 2) | default=0 |
| total_reviews | INTEGER | default=0 |
| video_view_count | INTEGER | default=0 |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(post_name)

### `daily_work_logs`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| student_user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| internship_id | INTEGER | FK â†’ internships.id, NOT NULL, indexed |
| log_date | DATE | NOT NULL |
| content | TEXT | NOT NULL, default='' |
| attachment_url | VARCHAR(500) | NOT NULL, default='' |
| review_status | VARCHAR(20) | NOT NULL, default='pending' |
| reviewed_by | INTEGER | FK â†’ users.id |
| reviewer_comment | TEXT | NOT NULL, default='' |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(internship_id); INDEX(internship_id, log_date); INDEX(student_user_id); UNIQUE(student_user_id, log_date)

### `earnings`

| column | type | constraints |
|---|---|---|
| earning_id | INTEGER | PK, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| course_id | INTEGER | FK â†’ courses.id, NOT NULL |
| order_id | INTEGER | FK â†’ orders.id, NOT NULL |
| order_status | VARCHAR(50) | default='completed' |
| course_price_total | NUMERIC(16, 2) | default=0 |
| course_price_grand_total | NUMERIC(16, 2) | default=0 |
| instructor_amount | NUMERIC(16, 2) | default=0 |
| instructor_rate | NUMERIC(16, 2) | default=0 |
| admin_amount | NUMERIC(16, 2) | default=0 |
| admin_rate | NUMERIC(16, 2) | default=0 |
| commission_type | VARCHAR(20) | default='percent' |
| deduct_fees_amount | NUMERIC(16, 2) | default=0 |
| deduct_fees_name | VARCHAR(250) | default='' |
| deduct_fees_type | VARCHAR(20) | default='percent' |
| process_by | VARCHAR(20) | default='admin' |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(earning_id)

### `ebook_grants`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| ebook_id | INTEGER | FK â†’ ebooks.id, NOT NULL, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| order_id | INTEGER | FK â†’ orders.id |
| source | VARCHAR(16) | NOT NULL, default='purchase' |
| granted_at | DATETIME | server_default |

Constraints/indexes: INDEX(ebook_id); INDEX(id); INDEX(user_id); UNIQUE(ebook_id, user_id)

### `ebooks`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| owner_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| title | VARCHAR(200) | NOT NULL |
| slug | VARCHAR(255) | NOT NULL, UNIQUE, indexed |
| description | TEXT | default='' |
| category | VARCHAR(16) | NOT NULL |
| price_inr | INTEGER | NOT NULL, default=0 |
| discount_price_inr | INTEGER |  |
| cover_image | VARCHAR(500) | default='' |
| file_path | VARCHAR(500) |  |
| file_size_bytes | INTEGER | NOT NULL, default=0 |
| page_count | INTEGER |  |
| sample_path | VARCHAR(500) |  |
| concept_tags | JSON | NOT NULL |
| course_id | INTEGER | FK â†’ courses.id, indexed |
| status | VARCHAR(16) | NOT NULL, default='draft' |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(course_id); INDEX(id); INDEX(owner_id); UNIQUE INDEX(slug)

### `enrollments`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| course_id | INTEGER | FK â†’ courses.id, NOT NULL |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| order_id | INTEGER | FK â†’ orders.id |
| cohort_id | INTEGER | FK â†’ cohorts.id |
| enrollment_source | VARCHAR(20) |  |
| membership_id | INTEGER | FK â†’ memberships.id, indexed |
| enrollment_date | DATETIME | server_default |
| enrollment_status | VARCHAR(50) | default='enrolled' |
| course_progress_percentage | INTEGER | default=0 |
| completed_lessons | INTEGER | default=0 |
| total_lessons | INTEGER | default=0 |
| completed_quizzes | INTEGER | default=0 |
| total_quizzes | INTEGER | default=0 |
| completion_date | DATETIME |  |
| completion_mode | VARCHAR(50) | default='' |
| completion_mode_text | TEXT | default='' |
| certificate_id | VARCHAR(100) |  |
| certificate_url | VARCHAR(500) |  |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(membership_id)

### `game_results`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| game_id | INTEGER | FK â†’ games.id, NOT NULL, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| score | INTEGER | NOT NULL |
| max_score | INTEGER | NOT NULL |
| duration_s | INTEGER | NOT NULL, default=0 |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(game_id); INDEX(id); INDEX(user_id)

### `games`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| owner_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| title | VARCHAR(200) | NOT NULL |
| template | VARCHAR(32) | NOT NULL |
| config | JSON | NOT NULL |
| status | VARCHAR(16) | NOT NULL, default='draft' |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(owner_id)

### `h5p_contents`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| public_id | VARCHAR(32) | NOT NULL, UNIQUE, indexed |
| owner_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| title | VARCHAR(255) | NOT NULL |
| library | VARCHAR(120) |  |
| size_bytes | INTEGER | NOT NULL, default=0 |
| status | VARCHAR(20) | NOT NULL, default='uploaded' |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(owner_id); UNIQUE INDEX(public_id)

### `h5p_results`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| content_id | INTEGER | FK â†’ h5p_contents.id, NOT NULL, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| score | INTEGER |  |
| max_score | INTEGER |  |
| completed | BOOLEAN | NOT NULL, default=False |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(content_id); INDEX(id); INDEX(user_id); UNIQUE(content_id, user_id)

### `hall_of_fame_members`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| name | VARCHAR(200) | NOT NULL |
| role | VARCHAR(200) | NOT NULL, default='' |
| company | VARCHAR(200) | NOT NULL, default='' |
| photo | VARCHAR(500) |  |
| tenure | VARCHAR(100) | NOT NULL, default='' |
| location | VARCHAR(200) |  |
| linkedin | VARCHAR(500) |  |
| blurb | TEXT |  |
| highlight | VARCHAR(100) |  |
| sort_order | INTEGER | NOT NULL, indexed, default=0 |
| is_published | BOOLEAN | NOT NULL, indexed, default=True |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(is_published); INDEX(sort_order)

### `instructor_profiles`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| instructor_rating | VARCHAR(10) | default='0' |
| instructor_bio | TEXT | default='' |
| instructor_designation | VARCHAR(255) | default='' |
| profile_completion | INTEGER | default=0 |
| is_approved | BOOLEAN | default=False |
| is_blocked | BOOLEAN | default=False |
| earning_commission_type | VARCHAR(20) | default='percentage' |
| earning_commission_amount | VARCHAR(20) | default='80' |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id)

### `instructor_reviews`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| course_id | INTEGER | FK â†’ courses.id, NOT NULL |
| instructor_id | INTEGER | FK â†’ users.id, NOT NULL |
| student_id | INTEGER | FK â†’ users.id, NOT NULL |
| rating | INTEGER | NOT NULL |
| review_title | VARCHAR(255) | default='' |
| review_content | TEXT | NOT NULL |
| is_private | BOOLEAN | default=True |
| is_read | BOOLEAN | default=False |
| instructor_response | TEXT | default='' |
| response_date | DATETIME |  |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id)

### `internship_announcements`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| company_id | INTEGER | FK â†’ companies.id, NOT NULL, indexed |
| internship_id | INTEGER | FK â†’ internships.id |
| title | VARCHAR(200) | NOT NULL |
| body | TEXT | NOT NULL |
| created_by | INTEGER | FK â†’ users.id |
| created_at | DATETIME | server_default |
| deleted_at | DATETIME |  |

Constraints/indexes: INDEX(company_id); INDEX(id)

### `internship_attendance`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| internship_id | INTEGER | FK â†’ internships.id, NOT NULL, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| attended_at | DATE | NOT NULL |
| status | VARCHAR(20) | NOT NULL, default='present' |
| notes | TEXT | default='' |
| hours_worked | NUMERIC(4, 2) | NOT NULL, default=0 |
| marked_by | INTEGER | FK â†’ users.id |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(internship_id); INDEX(internship_id, attended_at); INDEX(user_id); UNIQUE(internship_id, user_id, attended_at)

### `internship_performance_reviews`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| company_id | INTEGER | FK â†’ companies.id, NOT NULL, indexed |
| student_user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| internship_id | INTEGER | FK â†’ internships.id, NOT NULL, indexed |
| rating | INTEGER | NOT NULL |
| feedback | TEXT | NOT NULL, default='' |
| hire_recommendation | VARCHAR(10) | NOT NULL, default='maybe' |
| submitted_by | INTEGER | FK â†’ users.id |
| submitted_at | DATETIME | NOT NULL, server_default |

Constraints/indexes: INDEX(company_id); INDEX(id); INDEX(internship_id); INDEX(student_user_id); UNIQUE(company_id, student_user_id, internship_id)

### `internship_requests`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| company_id | INTEGER | FK â†’ companies.id, NOT NULL |
| requested_by | INTEGER | FK â†’ users.id, NOT NULL |
| title | VARCHAR(255) | NOT NULL |
| start_date | DATE | NOT NULL |
| end_date | DATE | NOT NULL |
| intern_count | INTEGER | NOT NULL, default=1 |
| description | TEXT | NOT NULL, default='' |
| status | VARCHAR(20) | NOT NULL, default='pending' |
| rejection_reason | TEXT | NOT NULL, default='' |
| approved_internship_id | INTEGER | FK â†’ internships.id |
| reviewed_by | INTEGER | FK â†’ users.id |
| reviewed_at | DATETIME |  |
| created_at | DATETIME | NOT NULL |
| updated_at | DATETIME | NOT NULL |

Constraints/indexes: INDEX(id)

### `internship_vouchers`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| code | VARCHAR(32) | NOT NULL, UNIQUE, indexed |
| internship_id | INTEGER | FK â†’ internships.id, NOT NULL, indexed |
| buyer_user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| amount_paid | NUMERIC(12, 2) | NOT NULL |
| razorpay_order_id | VARCHAR(255) | default='' |
| razorpay_payment_id | VARCHAR(255) | default='' |
| status | VARCHAR(20) | NOT NULL, default='issued' |
| redeemed_on_course_id | INTEGER | FK â†’ courses.id |
| redeemed_at | DATETIME |  |
| hired_by_company_id | INTEGER | FK â†’ companies.id |
| hired_by_override_at | DATETIME |  |
| hired_by_override_by | INTEGER | FK â†’ users.id |
| reporting_manager_user_id | INTEGER | FK â†’ users.id, indexed |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(buyer_user_id); INDEX(buyer_user_id, status); INDEX(id); INDEX(internship_id); INDEX(reporting_manager_user_id); UNIQUE INDEX(code)

### `internships`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| title | VARCHAR(255) | NOT NULL |
| slug | VARCHAR(255) | NOT NULL, UNIQUE, indexed |
| description | TEXT | default='' |
| cover_image | VARCHAR(500) | default='' |
| price | NUMERIC(12, 2) | NOT NULL |
| is_published | BOOLEAN | NOT NULL, default=False |
| spoc_user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| cohort_id | INTEGER | FK â†’ cohorts.id, NOT NULL, UNIQUE |
| created_by | INTEGER | FK â†’ users.id |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(spoc_user_id); UNIQUE INDEX(slug); UNIQUE(cohort_id)

### `invoice_counter`

| column | type | constraints |
|---|---|---|
| fiscal_year | VARCHAR(4) | PK |
| last_number | INTEGER | NOT NULL, default=0 |

### `issued_certificates`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| certificate_id | INTEGER | FK â†’ certificates.id, NOT NULL |
| course_id | INTEGER | FK â†’ courses.id, NOT NULL |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| certificate_hash | VARCHAR(255) | NOT NULL, UNIQUE |
| secure_certificate_id | VARCHAR(100) | NOT NULL, UNIQUE |
| certificate_title | VARCHAR(255) | NOT NULL |
| certificate_content | TEXT | default='' |
| completion_date | DATETIME | NOT NULL |
| course_completion_percentage | NUMERIC(5, 2) | default=100.0 |
| quiz_completion_percentage | NUMERIC(5, 2) | default=0.0 |
| assignment_completion_percentage | NUMERIC(5, 2) | default=0.0 |
| certificate_file_path | VARCHAR(500) | default='' |
| certificate_download_url | VARCHAR(500) | default='' |
| is_valid | BOOLEAN | default=True |
| expires_at | DATETIME |  |
| invalidated_date | DATETIME |  |
| invalidation_reason | TEXT | default='' |
| email_sent | BOOLEAN | default=False |
| email_sent_date | DATETIME |  |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(user_id, course_id); UNIQUE(certificate_hash); UNIQUE(secure_certificate_id); UNIQUE(user_id, course_id)

### `lesson_progress`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| course_id | INTEGER | FK â†’ courses.id, NOT NULL |
| lesson_id | INTEGER | FK â†’ lessons.id, NOT NULL |
| enrollment_id | INTEGER | FK â†’ enrollments.id, NOT NULL |
| progress_status | VARCHAR(50) | default='started' |
| completion_date | DATETIME |  |
| video_current_time | INTEGER | default=0 |
| video_total_duration | INTEGER | default=0 |
| video_completion_percentage | INTEGER | default=0 |
| reading_time | INTEGER | default=0 |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id)

### `lessons`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| post_author | INTEGER | FK â†’ users.id, NOT NULL |
| post_date | DATETIME | server_default |
| post_content | TEXT | default='' |
| post_title | TEXT | NOT NULL |
| post_excerpt | TEXT | default='' |
| post_status | VARCHAR(20) | default='publish' |
| post_name | VARCHAR(200) | indexed, default='' |
| post_modified | DATETIME | server_default |
| post_parent | INTEGER | FK â†’ courses.id, NOT NULL |
| menu_order | INTEGER | default=0 |
| post_type | VARCHAR(20) | default='lesson' |
| lesson_video_source | VARCHAR(50) | default='html5' |
| lesson_video_url | VARCHAR(255) | default='' |
| lesson_youtube_url | VARCHAR(255) | default='' |
| lesson_video_duration | VARCHAR(50) | default='' |
| lesson_video_poster | VARCHAR(255) | default='' |
| lesson_content_type | VARCHAR(20) | default='video' |
| h5p_content_id | INTEGER | FK â†’ h5p_contents.id |
| game_id | INTEGER | FK â†’ games.id |
| lesson_attachments | TEXT | default='' |
| lesson_preview | BOOLEAN | default=False |
| lesson_attachment_url | TEXT | default='' |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(post_name)

### `live_class_attendance`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| class_id | INTEGER | FK â†’ live_classes.id, NOT NULL, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| source | VARCHAR(6) | NOT NULL, default=<AttendanceSource.WEB: 'web'> |
| first_joined_at | DATETIME |  |
| last_heartbeat_at | DATETIME |  |
| accumulated_seconds | INTEGER | NOT NULL, default=0 |
| present | BOOLEAN |  |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(class_id); INDEX(id); INDEX(user_id); UNIQUE(class_id, user_id)

### `live_class_events`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| class_id | INTEGER | FK â†’ live_classes.id, NOT NULL, indexed |
| user_id | INTEGER | FK â†’ users.id |
| event | VARCHAR(64) | NOT NULL, indexed |
| payload | JSON |  |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(class_id); INDEX(event); INDEX(id)

### `live_class_join_tokens`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| class_id | INTEGER | FK â†’ live_classes.id, NOT NULL, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| jti | VARCHAR(64) | NOT NULL, UNIQUE, indexed |
| moderator | BOOLEAN | NOT NULL, default=False |
| issued_at | DATETIME | server_default |
| expires_at | DATETIME | NOT NULL |
| redeemed_at | DATETIME |  |

Constraints/indexes: INDEX(class_id); INDEX(id); INDEX(user_id); UNIQUE INDEX(jti)

### `live_class_poll_votes`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| poll_id | INTEGER | FK â†’ live_class_polls.id, NOT NULL, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| option_index | INTEGER | NOT NULL |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(poll_id); INDEX(user_id); UNIQUE(poll_id, user_id)

### `live_class_polls`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| class_id | INTEGER | FK â†’ live_classes.id, NOT NULL, indexed |
| created_by | INTEGER | FK â†’ users.id, NOT NULL |
| question | VARCHAR(500) | NOT NULL |
| options | JSON | NOT NULL |
| status | VARCHAR(6) | NOT NULL, default=<PollStatus.DRAFT: 'draft'> |
| show_results | BOOLEAN | NOT NULL, default=True |
| created_at | DATETIME | server_default |
| activated_at | DATETIME |  |
| closed_at | DATETIME |  |

Constraints/indexes: INDEX(class_id); INDEX(id)

### `live_class_schedules`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| course_id | INTEGER | FK â†’ courses.id, NOT NULL, indexed |
| lesson_id | INTEGER | FK â†’ lessons.id |
| instructor_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| title | VARCHAR(200) | NOT NULL |
| description | TEXT |  |
| timezone | VARCHAR(64) | NOT NULL, default='Asia/Kolkata' |
| recurrence_weekly | JSON |  |
| weeks | INTEGER |  |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(course_id); INDEX(id); INDEX(instructor_id)

### `live_classes`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| schedule_id | INTEGER | FK â†’ live_class_schedules.id, indexed |
| course_id | INTEGER | FK â†’ courses.id, NOT NULL |
| lesson_id | INTEGER | FK â†’ lessons.id |
| instructor_id | INTEGER | FK â†’ users.id, NOT NULL |
| title | VARCHAR(200) | NOT NULL |
| description | TEXT |  |
| scheduled_start | DATETIME | NOT NULL |
| scheduled_end | DATETIME | NOT NULL |
| timezone | VARCHAR(64) | NOT NULL, default='Asia/Kolkata' |
| room_name | VARCHAR(120) | NOT NULL, UNIQUE, indexed |
| status | VARCHAR(9) | NOT NULL, default=<LiveClassStatus.SCHEDULED: 'scheduled'> |
| started_at | DATETIME |  |
| ended_at | DATETIME |  |
| live_participants | INTEGER | NOT NULL, default=0 |
| recording_video_id | VARCHAR(64) |  |
| recording_status | VARCHAR(10) | NOT NULL, default=<RecordingStatus.NONE: 'none'> |
| settings | JSON | NOT NULL |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |
| deleted_at | DATETIME |  |

Constraints/indexes: INDEX(course_id, scheduled_start); INDEX(id); INDEX(instructor_id, scheduled_start); INDEX(schedule_id); INDEX(status); UNIQUE INDEX(room_name)

### `membership_plan_courses`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| plan_id | INTEGER | FK â†’ membership_plans.id, NOT NULL, indexed |
| course_id | INTEGER | FK â†’ courses.id, NOT NULL |

Constraints/indexes: INDEX(id); INDEX(plan_id)

### `membership_plans`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| name | VARCHAR(120) | NOT NULL |
| description | TEXT | default='' |
| all_access | BOOLEAN | NOT NULL, default=False |
| period | VARCHAR(20) | NOT NULL |
| interval | INTEGER | NOT NULL, default=1 |
| price | NUMERIC(10, 2) | NOT NULL |
| grace_days | INTEGER | NOT NULL, default=7 |
| razorpay_plan_id | VARCHAR(64) | NOT NULL, UNIQUE |
| is_active | BOOLEAN | NOT NULL, default=True |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); UNIQUE(razorpay_plan_id)

### `memberships`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| plan_id | INTEGER | FK â†’ membership_plans.id, NOT NULL |
| razorpay_subscription_id | VARCHAR(64) | NOT NULL, UNIQUE, indexed |
| status | VARCHAR(9) | NOT NULL, default=<MembershipStatus.PENDING: 'pending'> |
| current_period_end | DATETIME |  |
| grace_until | DATETIME |  |
| cancel_at_period_end | BOOLEAN | NOT NULL, default=False |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(user_id); UNIQUE INDEX(razorpay_subscription_id); UNIQUE INDEX(user_id)

### `notifications`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| type | VARCHAR(50) | NOT NULL |
| title | VARCHAR(255) | NOT NULL |
| message | TEXT | default='' |
| link | VARCHAR(255) |  |
| related_id | INTEGER |  |
| is_read | BOOLEAN | NOT NULL, default=False |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(user_id); INDEX(user_id, is_read)

### `order_items`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| order_id | INTEGER | FK â†’ orders.id, NOT NULL |
| course_id | INTEGER | FK â†’ courses.id |
| ebook_id | INTEGER | FK â†’ ebooks.id, indexed |
| order_item_name | TEXT | NOT NULL |
| order_item_type | VARCHAR(200) | default='line_item' |
| quantity | INTEGER | default=1 |
| subtotal | NUMERIC(13, 4) | default=0 |
| subtotal_tax | NUMERIC(13, 4) | default=0 |
| total | NUMERIC(13, 4) | default=0 |
| total_tax | NUMERIC(13, 4) | default=0 |
| product_data | JSON | default={} |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(ebook_id); INDEX(id)

### `orders`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| bundle_id | INTEGER | FK â†’ bundles.id, indexed |
| ebook_id | INTEGER | FK â†’ ebooks.id, indexed |
| order_key | VARCHAR(255) | NOT NULL, UNIQUE |
| order_status | VARCHAR(10) | default=<OrderStatus.PENDING: 'pending'> |
| currency | VARCHAR(3) | default='INR' |
| total_amount | NUMERIC(13, 4) | default=0 |
| subtotal_amount | NUMERIC(13, 4) | default=0 |
| tax_amount | NUMERIC(13, 4) | default=0 |
| shipping_amount | NUMERIC(13, 4) | default=0 |
| discount_amount | NUMERIC(13, 4) | default=0 |
| payment_method | VARCHAR(255) | default='' |
| payment_method_title | VARCHAR(255) | default='' |
| transaction_id | VARCHAR(255) | default='' |
| billing_first_name | VARCHAR(255) | default='' |
| billing_last_name | VARCHAR(255) | default='' |
| billing_company | VARCHAR(255) | default='' |
| billing_address_1 | VARCHAR(255) | default='' |
| billing_address_2 | VARCHAR(255) | default='' |
| billing_city | VARCHAR(255) | default='' |
| billing_state | VARCHAR(255) | default='' |
| billing_postcode | VARCHAR(20) | default='' |
| billing_country | VARCHAR(2) | default='' |
| billing_email | VARCHAR(255) | default='' |
| billing_phone | VARCHAR(20) | default='' |
| customer_note | TEXT | default='' |
| order_notes | TEXT | default='' |
| date_created | DATETIME | server_default |
| date_modified | DATETIME |  |
| date_paid | DATETIME |  |
| date_completed | DATETIME |  |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(bundle_id); INDEX(ebook_id); INDEX(id); UNIQUE(order_key)

### `page_views`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| path | VARCHAR(500) | NOT NULL, indexed |
| referrer | VARCHAR(500) | default='' |
| user_id | INTEGER | FK â†’ users.id, indexed |
| session_id | VARCHAR(64) | indexed |
| ip_hash | VARCHAR(64) | indexed |
| user_agent | VARCHAR(500) | default='' |
| country | VARCHAR(8) | default='' |
| duration_ms | INTEGER | default=0 |
| entity_type | VARCHAR(32) | indexed |
| entity_id | INTEGER | indexed |
| created_at | DATETIME | indexed, server_default |

Constraints/indexes: INDEX(created_at); INDEX(created_at, path); INDEX(entity_id); INDEX(entity_type); INDEX(entity_type, entity_id); INDEX(id); INDEX(ip_hash); INDEX(path); INDEX(session_id); INDEX(user_id)

### `payments`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| order_id | INTEGER | FK â†’ orders.id, NOT NULL |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| payment_method | VARCHAR(50) | NOT NULL |
| gateway_transaction_id | VARCHAR(255) | default='' |
| gateway_payment_id | VARCHAR(255) | default='' |
| gateway_order_id | VARCHAR(255) | default='' |
| amount | NUMERIC(13, 4) | NOT NULL |
| currency | VARCHAR(3) | default='INR' |
| payment_status | VARCHAR(10) | default=<PaymentStatus.PENDING: 'pending'> |
| gateway_response | JSON | default={} |
| failure_reason | TEXT | default='' |
| payment_date | DATETIME | server_default |
| processed_date | DATETIME |  |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); UNIQUE INDEX(gateway_payment_id)

### `quiz_attempt_answers`

| column | type | constraints |
|---|---|---|
| attempt_answer_id | INTEGER | PK, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| quiz_id | INTEGER | FK â†’ quizzes.id, NOT NULL |
| question_id | INTEGER | FK â†’ quiz_questions.question_id, NOT NULL |
| quiz_attempt_id | INTEGER | FK â†’ quiz_attempts.attempt_id, NOT NULL |
| given_answer | TEXT | default='' |
| question_mark | NUMERIC(8, 2) | default=0 |
| achieved_mark | NUMERIC(8, 2) | default=0 |
| minus_mark | NUMERIC(8, 2) | default=0 |
| is_correct | BOOLEAN | default=False |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(attempt_answer_id)

### `quiz_attempts`

| column | type | constraints |
|---|---|---|
| attempt_id | INTEGER | PK, indexed |
| course_id | INTEGER | FK â†’ courses.id, NOT NULL |
| quiz_id | INTEGER | FK â†’ quizzes.id, NOT NULL |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| total_questions | INTEGER | default=0 |
| total_answered_questions | INTEGER | default=0 |
| total_marks | NUMERIC(9, 2) | default=0 |
| earned_marks | NUMERIC(9, 2) | default=0 |
| attempt_info | JSON | default={} |
| attempt_status | VARCHAR(50) | default='attempt_started' |
| attempt_ip | VARCHAR(250) | default='' |
| attempt_started_at | DATETIME | server_default |
| attempt_ended_at | DATETIME |  |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(attempt_id)

### `quiz_question_answers`

| column | type | constraints |
|---|---|---|
| answer_id | INTEGER | PK, indexed |
| belongs_question_id | INTEGER | FK â†’ quiz_questions.question_id, NOT NULL |
| belongs_question_type | VARCHAR(250) | default='' |
| answer_title | TEXT | NOT NULL |
| is_correct | BOOLEAN | default=False |
| image_id | INTEGER | default=0 |
| answer_two_gap_match | TEXT | default='' |
| answer_view_format | VARCHAR(250) | default='' |
| answer_settings | JSON | default={} |
| answer_order | INTEGER | default=0 |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(answer_id)

### `quiz_questions`

| column | type | constraints |
|---|---|---|
| question_id | INTEGER | PK, indexed |
| quiz_id | INTEGER | FK â†’ quizzes.id, NOT NULL |
| question_title | TEXT | NOT NULL |
| question_description | TEXT | default='' |
| answer_explanation | TEXT | default='' |
| question_type | VARCHAR(50) | NOT NULL |
| question_mark | NUMERIC(9, 2) | default=1.0 |
| question_settings | JSON | default={} |
| question_order | INTEGER | default=0 |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(question_id)

### `quizzes`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| post_author | INTEGER | FK â†’ users.id, NOT NULL |
| post_date | DATETIME | server_default |
| post_content | TEXT | default='' |
| post_title | TEXT | NOT NULL |
| post_excerpt | TEXT | default='' |
| post_status | VARCHAR(20) | default='publish' |
| post_name | VARCHAR(200) | indexed, default='' |
| post_modified | DATETIME | server_default |
| post_parent | INTEGER | FK â†’ courses.id, NOT NULL |
| menu_order | INTEGER | default=0 |
| post_type | VARCHAR(20) | default='tutor_quiz' |
| quiz_time_limit | INTEGER | default=0 |
| quiz_feedback_mode | VARCHAR(50) | default='default' |
| quiz_max_questions_for_take | INTEGER | default=10 |
| quiz_max_attempts_allowed | INTEGER | default=0 |
| quiz_passing_grade | INTEGER | default=80 |
| quiz_question_layout_view | VARCHAR(50) | default='single_question' |
| quiz_questions_order | VARCHAR(50) | default='rand' |
| quiz_hide_quiz_details | BOOLEAN | default=False |
| quiz_hide_quiz_time_display | BOOLEAN | default=False |
| quiz_auto_start | BOOLEAN | default=False |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(post_name)

### `referral_codes`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| cohort_id | INTEGER | FK â†’ cohorts.id, NOT NULL, UNIQUE |
| code | VARCHAR(64) | NOT NULL, UNIQUE, indexed |
| max_uses | INTEGER | NOT NULL, default=0 |
| used_count | INTEGER | NOT NULL, default=0 |
| expires_at | DATETIME |  |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); UNIQUE INDEX(code); UNIQUE(cohort_id)

### `session_attendance`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| session_id | INTEGER | FK â†’ cohort_sessions.id, NOT NULL, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| status | VARCHAR(16) | NOT NULL, default='absent' |
| notes | TEXT | default='' |
| marked_by | INTEGER | FK â†’ users.id |
| marked_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(session_id); INDEX(user_id); UNIQUE(session_id, user_id)

### `student_course_activities`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| course_id | INTEGER | FK â†’ courses.id, NOT NULL |
| lesson_id | INTEGER | FK â†’ lessons.id |
| quiz_id | INTEGER | FK â†’ quizzes.id |
| activity_type | VARCHAR(50) | NOT NULL |
| activity_value | TEXT | default='' |
| activity_status | VARCHAR(50) | default='active' |
| activity_meta | JSON | default={} |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(id)

### `user_badges`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| badge_id | INTEGER | FK â†’ badges.id, NOT NULL, indexed |
| awarded_at | DATETIME | server_default |

Constraints/indexes: INDEX(badge_id); INDEX(id); INDEX(user_id); UNIQUE(user_id, badge_id)

### `user_game_stats`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL, UNIQUE, indexed |
| total_xp | INTEGER | NOT NULL, default=0 |
| current_streak | INTEGER | NOT NULL, default=0 |
| longest_streak | INTEGER | NOT NULL, default=0 |
| last_active_date | DATE |  |
| leaderboard_visible | BOOLEAN | NOT NULL, default=True |
| badges_count | INTEGER | NOT NULL, default=0 |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); UNIQUE INDEX(user_id)

### `user_profiles`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| first_name | VARCHAR(255) | default='' |
| last_name | VARCHAR(255) | default='' |
| description | TEXT | default='' |
| phone | VARCHAR(20) | default='' |
| designation | VARCHAR(255) | default='' |
| address | TEXT | default='' |
| city | VARCHAR(100) | default='' |
| state | VARCHAR(100) | default='' |
| country | VARCHAR(100) | default='' |
| postal_code | VARCHAR(20) | default='' |
| profile_photo | VARCHAR(255) | default='' |
| cover_photo | VARCHAR(255) | default='' |
| facebook | VARCHAR(255) | default='' |
| twitter | VARCHAR(255) | default='' |
| linkedin | VARCHAR(255) | default='' |
| website | VARCHAR(255) | default='' |
| show_email | BOOLEAN | default=False |
| receive_notifications | BOOLEAN | default=True |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id)

### `user_roles`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| role | VARCHAR(50) | NOT NULL |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(id)

### `users`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_login | VARCHAR(60) | NOT NULL, UNIQUE, indexed |
| user_pass | VARCHAR(255) | NOT NULL |
| user_nicename | VARCHAR(50) | NOT NULL, indexed |
| user_email | VARCHAR(100) | NOT NULL, UNIQUE, indexed |
| user_url | VARCHAR(100) | default='' |
| user_registered | DATETIME | server_default |
| user_activation_key | VARCHAR(255) | default='' |
| user_status | INTEGER | default=0 |
| display_name | VARCHAR(250) | NOT NULL |
| role | VARCHAR(50) | default='student' |
| is_active | BOOLEAN | default=True |
| is_verified | BOOLEAN | default=True |
| profile_completed | BOOLEAN | default=False |
| last_login | DATETIME |  |
| totp_secret | VARCHAR(64) |  |
| totp_enabled | BOOLEAN | NOT NULL, default=False |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(id); INDEX(user_nicename); UNIQUE INDEX(user_email); UNIQUE INDEX(user_login)

### `watch_sessions`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| course_id | INTEGER | FK â†’ courses.id, NOT NULL, indexed |
| lesson_id | INTEGER | FK â†’ lessons.id, NOT NULL, indexed |
| event | VARCHAR(20) | NOT NULL |
| duration_seconds | INTEGER | default=0 |
| position_seconds | INTEGER | default=0 |
| started_at | DATETIME | indexed, server_default |
| ended_at | DATETIME |  |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(course_id); INDEX(id); INDEX(lesson_id); INDEX(started_at); INDEX(user_id)

### `webhook_events`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| event_id | VARCHAR(255) | NOT NULL, UNIQUE, indexed |
| event_type | VARCHAR(100) | NOT NULL, default='' |
| payload | JSON | NOT NULL, default={} |
| signature_valid | BOOLEAN | NOT NULL, default=False |
| status | VARCHAR(9) | NOT NULL, default=<WebhookEventStatus.RECEIVED: 'received'> |
| attempts | INTEGER | NOT NULL, default=0 |
| last_attempt_at | DATETIME |  |
| last_error | TEXT |  |
| received_at | DATETIME | NOT NULL, server_default |
| processed_at | DATETIME |  |

Constraints/indexes: INDEX(id); UNIQUE INDEX(event_id)

### `wishlist_items`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| course_id | INTEGER | FK â†’ courses.id, NOT NULL |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(id)

### `withdrawals`

| column | type | constraints |
|---|---|---|
| withdraw_id | INTEGER | PK, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL |
| amount | NUMERIC(16, 2) | NOT NULL |
| method_data | JSON | default={} |
| status | VARCHAR(50) | default='pending' |
| reject_detail | TEXT | default='' |
| created_at | DATETIME | server_default |
| updated_at | DATETIME | server_default |

Constraints/indexes: INDEX(withdraw_id)

### `xp_events`

| column | type | constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_id | INTEGER | FK â†’ users.id, NOT NULL, indexed |
| event_key | VARCHAR(120) | NOT NULL, UNIQUE, indexed |
| event_type | VARCHAR(40) | NOT NULL, indexed |
| points | INTEGER | NOT NULL, default=0 |
| course_id | INTEGER | FK â†’ courses.id, indexed |
| meta | JSON |  |
| created_at | DATETIME | server_default |

Constraints/indexes: INDEX(course_id); INDEX(event_type); INDEX(id); INDEX(user_id); UNIQUE INDEX(event_key)

