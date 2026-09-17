# Codebase index

Generated from the outer workspace on 6 September 2026. Secrets, runtime data, duplicate checkouts and vendor bundles are excluded. File presence does not prove runtime use.

## Frontend route patterns

- `*`
- `/`
- `/about`
- `/admin`
- `/admin/analytics`
- `/admin/approvals`
- `/admin/blog-templates`
- `/admin/blogs`
- `/admin/blogs/create`
- `/admin/blogs/edit/:id`
- `/admin/bundles`
- `/admin/certificates`
- `/admin/cohorts`
- `/admin/colleges`
- `/admin/companies`
- `/admin/company-invoices`
- `/admin/content-libraries`
- `/admin/coupons`
- `/admin/course-packages`
- `/admin/course-reviews`
- `/admin/courses`
- `/admin/courses/:courseId/activity`
- `/admin/courses/:courseId/assignment-builder`
- `/admin/courses/:courseId/assignment-builder/:assignmentId`
- `/admin/courses/:courseId/quiz-builder`
- `/admin/courses/:courseId/quiz-builder/:quizId`
- `/admin/courses/:id/edit`
- `/admin/courses/categories`
- `/admin/courses/create`
- `/admin/courses/new`
- `/admin/courses/tags`
- `/admin/dashboard`
- `/admin/enrollments`
- `/admin/exam-pricing`
- `/admin/hall-of-fame`
- `/admin/instructors`
- `/admin/internship-requests`
- `/admin/internships`
- `/admin/lab-studio`
- `/admin/lessons`
- `/admin/manage`
- `/admin/memberships`
- `/admin/messages`
- `/admin/operations`
- `/admin/orders`
- `/admin/past-classes`
- `/admin/quizzes`
- `/admin/settings`
- `/admin/spocs`
- `/admin/students`
- `/assignment/:assignmentId`
- `/auth/linkedin/callback`
- `/blog`
- `/blog/:slug`
- `/bundles`
- `/bundles/:slug`
- `/cart`
- `/categories`
- `/certificates/:courseId`
- `/checkout`
- `/checkout/:courseId`
- `/company/dashboard`
- `/contact`
- `/courses`
- `/courses/:courseId/assignments/:assignmentId`
- `/courses/:courseId/certificate`
- `/courses/:courseId/lessons/:lessonId`
- `/courses/:courseId/quizzes/:quizId`
- `/courses/:id`
- `/courses/:id/learn`
- `/courses/meiporul`
- `/courses/seyappaduporul`
- `/courses/utporul`
- `/dashboard`
- `/dashboard/analytics`
- `/dashboard/internship-inbox`
- `/dashboard/internship-profile`
- `/dashboard/messages`
- `/dashboard/my-internships`
- `/dashboard/my-internships/:slug`
- `/dashboard/my-vouchers`
- `/exam-papers`
- `/for-companies`
- `/for-companies/signup`
- `/forgot-password`
- `/games/:id/play`
- `/hall-of-fame`
- `/instructor`
- `/instructor/:id`
- `/instructor/analytics`
- `/instructor/assessment-studio`
- `/instructor/assignments/:assignmentId/grade`
- `/instructor/blog`
- `/instructor/blog/create`
- `/instructor/blog/edit/:id`
- `/instructor/certificate-designer`
- `/instructor/course-packages`
- `/instructor/courses`
- `/instructor/courses/:courseId/assignment-builder`
- `/instructor/courses/:courseId/assignment-builder/:assignmentId`
- `/instructor/courses/:courseId/quiz-builder`
- `/instructor/courses/:courseId/quiz-builder/:quizId`
- `/instructor/courses/:id/coverage`
- `/instructor/courses/:id/edit`
- `/instructor/courses/:id/gradebook`
- `/instructor/courses/:id/grading-queue`
- `/instructor/courses/create`
- `/instructor/dashboard`
- `/instructor/ebooks`
- `/instructor/games`
- `/instructor/games/:id/edit`
- `/instructor/games/new`
- `/instructor/grading`
- `/instructor/h5p`
- `/instructor/insights`
- `/instructor/interventions`
- `/instructor/lab-studio`
- `/instructor/live-classes`
- `/instructor/live-classes/:id/console`
- `/instructor/live-classes/:id/report`
- `/instructor/live-classes/new`
- `/instructor/past-classes`
- `/instructor/recording-lessons`
- `/instructor/review-queue`
- `/instructor/students`
- `/instructor/three-d-tasks`
- `/internships`
- `/internships/:slug`
- `/labs`
- `/labs/:slug`
- `/leaderboard`
- `/library`
- `/library/:slug`
- `/login`
- `/meiporul-ar`
- `/membership`
- `/my-courses`
- `/my-grades`
- `/my-library`
- `/my-mastery`
- `/my-plan`
- `/parent`
- `/privacy`
- `/profile`
- `/quiz/:quizId`
- `/recordings/:classId`
- `/refund-policy`
- `/register`
- `/reset-password`
- `/search`
- `/settings`
- `/shipping`
- `/spoc/:spocId/profile`
- `/spoc/blog`
- `/spoc/blog/create`
- `/spoc/blog/edit/:id`
- `/spoc/cohort/:id`
- `/spoc/dashboard`
- `/spoc/internship/:id`
- `/student/blog/create`
- `/student/blog/create/:id`
- `/student/live-classes`
- `/student/live-classes/:id/join`
- `/student/live-classes/:id/recording`
- `/superadmin`
- `/superadmin/admins`
- `/superadmin/audit`
- `/superadmin/dashboard`
- `/superadmin/instructors`
- `/superadmin/students`
- `/terms`
- `/u/:username`
- `/verify-certificate`
- `/verify-certificate/:certificateId`
- `/verify-email`
- `/wishlist`

## Backend router registrations

| Router | Prefix | main.py line |
|---|---|---|
| auth.router | `/api/v1/auth` | 1294 |
| notifications_router.router | `/api/v1/notifications` | 1295 |
| course_type_capabilities.router | `/api/v1` | 1296 |
| courses.router | `/api/v1/courses` | 1297 |
| categories.router | `/api/v1/categories` | 1298 |
| tags.router | `/api/v1/tags` | 1299 |
| instructors.router | `/api/v1/instructors` | 1300 |
| lessons.router | `/api/v1/lessons` | 1301 |
| checkout.router | `/api/v1/checkout` | 1302 |
| users.router | `/api/v1/users` | 1303 |
| payments.router | `/api/v1/payments` | 1304 |
| payments_proxy.router | `/api/v1/payments` | 1305 |
| memberships.router | `/api/v1/memberships` | 1306 |
| bundles.router | `/api/v1/bundles` | 1307 |
| library.router | `/api/v1/library` | 1308 |
| orders.router | `/api/v1/orders` | 1309 |
| certificates.router | `/api/v1/certificates` | 1310 |
| certificate_designer.router | `/api/v1/certificates/designer` | 1311 |
| admin.router | `/api/v1/admin` | 1312 |
| superadmin.router | `/api/v1/superadmin` | 1313 |
| dashboard.router | `/api/v1/dashboard` | 1314 |
| uploads.router | `/api/v1/upload` | 1315 |
| wishlist.router | `/api/v1/wishlist` | 1316 |
| instructor_reviews.router | `/api/v1/instructor-reviews` | 1317 |
| quizzes.router | `/api/v1` | 1318 |
| assignments.router | `/api/v1` | 1319 |
| gradebook.router | `/api/v1` | 1320 |
| h5p.router | `/api/v1/h5p` | 1321 |
| games.router | `/api/v1/games` | 1322 |
| gamification.router | `/api/v1/gamification` | 1323 |
| certificate_verification.router | `/api/v1` | 1324 |
| blog.router | `/api/v1/blog` | 1325 |
| hall_of_fame.router | `/api/v1/hall-of-fame` | 1326 |
| coupons.router | `/api/v1/coupons` | 1327 |
| video.router | `/api/v1/extract` | 1328 |
| video_streaming.router | `/api/v1/stream` | 1329 |
| embed.router | `/api/v1/embed` | 1330 |
| youtube_embed.router | `/api/v1/youtube` | 1331 |
| player.router | `/api/v1/video` | 1332 |
| progress_router.router | `/api/v1/progress` | 1333 |
| bunny.router | `/api/v1/bunny` | 1334 |
| analytics.router | `/api/v1/analytics` | 1335 |
| internships.router | `/api/v1` | 1336 |
| candidate.router | `/api/v1/candidates` | 1337 |
| companies.router | `/api/v1/companies` | 1338 |
| company_dashboard.router | `/api/v1/companies` | 1339 |
| company_billing.router | `/api/v1/companies/billing` | 1340 |
| cohorts.router | `/api/v1/cohorts` | 1341 |
| student_workspace.router | `/api/v1/student` | 1342 |
| admin_messages.router | `/api/v1/admin/messages` | 1343 |
| export_import.router | `/api/v1` | 1344 |
| question_banks.router | `/api/v1/question-banks` | 1346 |
| sileos.router | `/api/v1` | 1347 |
| ai.router | `/api/v1` | 1348 |
| ai_tutor.router | `/api/v1/ai` | 1349 |
| parents.router | `/api/v1/parents` | 1350 |
| geogebra.router | `/api/v1/geogebra` | 1351 |
| three_d.router | `/api/v1/three-d` | 1352 |
| virtual_labs.router | `/api/v1/virtual-labs` | 1353 |
| lab_studio.router | `/api/v1/lab-studio` | 1354 |
| scorable_items.router | `/api/v1/scorable-items` | 1357 |
| three_d_tasks.router | `/api/v1/three-d-tasks` | 1359 |
| mastery.router | `/api/v1/mastery` | 1361 |
| tag_taxonomy.router | `/api/v1/tag-taxonomy` | 1363 |
| ai_engines.router | `/api/v1/ai` | 1366 |
| flywheel.router | `/api/v1/flywheel` | 1368 |
| funnel.router | `/api/v1/funnel` | 1370 |
| course_ops.router | `/api/v1/course-ops` | 1372 |
| learning_signals.router | `/api/v1/signals` | 1374 |
| learning_planner.router | `/api/v1/planner` | 1376 |
| studio.router | `/api/v1/studio` | 1377 |
| content_library_admin.router | `/api/v1/admin/content-library` | 1378 |
| live_class_session.router | `/api/v1/live` | 1379 |
| live_classes.router | `/api/v1/live` | 1380 |
| live_class_attendance.router | `/api/v1/live` | 1381 |
| live_class_polls.router | `/api/v1/live` | 1382 |
| live_class_recordings.router | `/api/v1/live` | 1383 |
| live_class_internal.router | `/api/v1/internal/live` | 1384 |
| chunked_upload.router | `/api/v1/upload/chunked` | 1388 |
| assessment_studio.router | `/api/v1/assessment-studio` | 1403 |
| recording_lessons.router | `/api/v1/recording-lessons` | 1406 |
| operations.router | `/api/v1/admin/operations` | 1409 |
| course_packages.router | `/api/v1/course-packages` | 1412 |
| exam_papers.router | `/api/v1/exam-papers` | 1415 |

## Declared database tables

| Table | Model source |
|---|---|
| `admin_messages` | `backend/app/models/admin_message.py` |
| `tutor_escalations` | `backend/app/models/ai_layer.py` |
| `content_error_reports` | `backend/app/models/ai_layer.py` |
| `studio_questions` | `backend/app/models/assessment_studio.py` |
| `assignments` | `backend/app/models/assignment.py` |
| `assignment_submissions` | `backend/app/models/assignment.py` |
| `blog_posts` | `backend/app/models/blog.py` |
| `blog_comments` | `backend/app/models/blog.py` |
| `bundles` | `backend/app/models/bundle.py` |
| `bundle_courses` | `backend/app/models/bundle.py` |
| `candidate_profiles` | `backend/app/models/candidate.py` |
| `candidate_eligibility` | `backend/app/models/candidate.py` |
| `certificates` | `backend/app/models/certificate.py` |
| `course_certificates` | `backend/app/models/certificate.py` |
| `issued_certificates` | `backend/app/models/certificate.py` |
| `certificate_verifications` | `backend/app/models/certificate.py` |
| `certificate_element_templates` | `backend/app/models/certificate.py` |
| `colleges` | `backend/app/models/cohort.py` |
| `cohorts` | `backend/app/models/cohort.py` |
| `referral_codes` | `backend/app/models/cohort.py` |
| `cohort_memberships` | `backend/app/models/cohort.py` |
| `cohort_sessions` | `backend/app/models/cohort.py` |
| `session_attendance` | `backend/app/models/cohort.py` |
| `companies` | `backend/app/models/company.py` |
| `company_interests` | `backend/app/models/company.py` |
| `company_managers` | `backend/app/models/company_dashboard.py` |
| `daily_work_logs` | `backend/app/models/company_dashboard.py` |
| `internship_announcements` | `backend/app/models/company_dashboard.py` |
| `internship_performance_reviews` | `backend/app/models/company_dashboard.py` |
| `company_invoices` | `backend/app/models/company_invoice.py` |
| `company_invoice_items` | `backend/app/models/company_invoice.py` |
| `company_seat_pools` | `backend/app/models/company_invoice.py` |
| `company_seat_assignments` | `backend/app/models/company_invoice.py` |
| `invoice_counter` | `backend/app/models/company_invoice.py` |
| `virtual_lab_catalog` | `backend/app/models/content_library.py` |
| `virtual_lab_results` | `backend/app/models/content_library.py` |
| `coupons` | `backend/app/models/coupon.py` |
| `coupon_course_restrictions` | `backend/app/models/coupon.py` |
| `coupon_usage` | `backend/app/models/coupon.py` |
| `courses` | `backend/app/models/course.py` |
| `lessons` | `backend/app/models/course.py` |
| `course_categories` | `backend/app/models/course.py` |
| `course_tags` | `backend/app/models/course.py` |
| `course_reviews` | `backend/app/models/course.py` |
| `course_category_relations` | `backend/app/models/course.py` |
| `course_tag_relations` | `backend/app/models/course.py` |
| `course_collaborators` | `backend/app/models/course_ops.py` |
| `course_studio_settings` | `backend/app/models/course_settings.py` |
| `ebooks` | `backend/app/models/ebook.py` |
| `ebook_grants` | `backend/app/models/ebook.py` |
| `edgyy_payments` | `backend/app/models/edgyy_payment.py` |
| `edgyy_payment_sessions` | `backend/app/models/edgyy_payment.py` |
| `enrollments` | `backend/app/models/enrollment.py` |
| `lesson_progress` | `backend/app/models/enrollment.py` |
| `student_course_activities` | `backend/app/models/enrollment.py` |
| `watch_sessions` | `backend/app/models/enrollment.py` |
| `course_announcements` | `backend/app/models/enrollment.py` |
| `wishlist_items` | `backend/app/models/enrollment.py` |
| `exam_price_slabs` | `backend/app/models/exam_paper.py` |
| `exam_papers` | `backend/app/models/exam_paper.py` |
| `teach_backs` | `backend/app/models/flywheel.py` |
| `teach_back_ratings` | `backend/app/models/flywheel.py` |
| `funnel_events` | `backend/app/models/funnel.py` |
| `games` | `backend/app/models/game.py` |
| `game_results` | `backend/app/models/game.py` |
| `xp_events` | `backend/app/models/gamification.py` |
| `user_game_stats` | `backend/app/models/gamification.py` |
| `badges` | `backend/app/models/gamification.py` |
| `user_badges` | `backend/app/models/gamification.py` |
| `geogebra_applets` | `backend/app/models/geogebra.py` |
| `h5p_contents` | `backend/app/models/h5p.py` |
| `h5p_results` | `backend/app/models/h5p.py` |
| `hall_of_fame_members` | `backend/app/models/hall_of_fame.py` |
| `instructor_reviews` | `backend/app/models/instructor_review.py` |
| `internships` | `backend/app/models/internship.py` |
| `internship_vouchers` | `backend/app/models/internship.py` |
| `internship_attendance` | `backend/app/models/internship.py` |
| `internship_requests` | `backend/app/models/internship_request.py` |
| `lab_notebooks` | `backend/app/models/lab_notebook.py` |
| `learning_goals` | `backend/app/models/learning_planner.py` |
| `learning_interventions` | `backend/app/models/learning_planner.py` |
| `learning_plan_tasks` | `backend/app/models/learning_planner.py` |
| `lab_investigation_attempts` | `backend/app/models/learning_release.py` |
| `offline_sync_receipts` | `backend/app/models/learning_release.py` |
| `learning_signals` | `backend/app/models/learning_signals.py` |
| `lesson_concept_markers` | `backend/app/models/learning_signals.py` |
| `adaptive_sessions` | `backend/app/models/learning_signals.py` |
| `live_class_schedules` | `backend/app/models/live_class.py` |
| `live_classes` | `backend/app/models/live_class.py` |
| `live_class_join_tokens` | `backend/app/models/live_class.py` |
| `live_class_attendance` | `backend/app/models/live_class.py` |
| `live_class_polls` | `backend/app/models/live_class.py` |
| `live_class_poll_votes` | `backend/app/models/live_class.py` |
| `live_class_events` | `backend/app/models/live_class.py` |
| `class_reports` | `backend/app/models/live_class_report.py` |
| `recording_audit` | `backend/app/models/live_class_report.py` |
| `concept_links` | `backend/app/models/mastery.py` |
| `concept_prerequisites` | `backend/app/models/mastery.py` |
| `mastery_evidence` | `backend/app/models/mastery.py` |
| `learner_mastery` | `backend/app/models/mastery.py` |
| `course_outcomes` | `backend/app/models/mastery.py` |
| `membership_plans` | `backend/app/models/membership.py` |
| `membership_plan_courses` | `backend/app/models/membership.py` |
| `memberships` | `backend/app/models/membership.py` |
| `notifications` | `backend/app/models/notification.py` |
| `service_heartbeats` | `backend/app/models/operations.py` |
| `course_transfers` | `backend/app/models/operations.py` |
| `page_views` | `backend/app/models/page_view.py` |
| `orders` | `backend/app/models/payment.py` |
| `order_items` | `backend/app/models/payment.py` |
| `payments` | `backend/app/models/payment.py` |
| `earnings` | `backend/app/models/payment.py` |
| `withdrawals` | `backend/app/models/payment.py` |
| `quizzes` | `backend/app/models/quiz.py` |
| `quiz_questions` | `backend/app/models/quiz.py` |
| `quiz_question_answers` | `backend/app/models/quiz.py` |
| `quiz_attempts` | `backend/app/models/quiz.py` |
| `quiz_attempt_answers` | `backend/app/models/quiz.py` |
| `recording_lessons` | `backend/app/models/recording_lesson.py` |
| `question_banks` | `backend/app/models/sileos_pack.py` |
| `bank_questions` | `backend/app/models/sileos_pack.py` |
| `course_prerequisites` | `backend/app/models/sileos_pack.py` |
| `learning_paths` | `backend/app/models/sileos_pack.py` |
| `xapi_statements` | `backend/app/models/sileos_pack.py` |
| `ai_jobs` | `backend/app/models/sileos_pack.py` |
| `student_risk_flags` | `backend/app/models/sileos_pack.py` |
| `tag_clusters` | `backend/app/models/tag_cluster.py` |
| `three_d_models` | `backend/app/models/three_d.py` |
| `three_d_tasks` | `backend/app/models/three_d_task.py` |
| `three_d_task_attempts` | `backend/app/models/three_d_task.py` |
| `users` | `backend/app/models/user.py` |
| `user_profiles` | `backend/app/models/user.py` |
| `instructor_profiles` | `backend/app/models/user.py` |
| `admin_impersonation_logs` | `backend/app/models/user.py` |
| `user_roles` | `backend/app/models/user.py` |
| `webhook_events` | `backend/app/models/webhook_event.py` |

## Source file inventory

| File | Lines |
|---|---|
| `backend/app/api/v1/certificate_verification.py` | 194 |
| `backend/app/core/auth_security.py` | 421 |
| `backend/app/core/cache_headers.py` | 21 |
| `backend/app/core/config.py` | 200 |
| `backend/app/core/config_broken.py` | 78 |
| `backend/app/core/cors.py` | 44 |
| `backend/app/core/course_links.py` | 16 |
| `backend/app/core/course_types.py` | 78 |
| `backend/app/core/csv_safety.py` | 26 |
| `backend/app/core/database.py` | 120 |
| `backend/app/core/database_async.py` | 82 |
| `backend/app/core/database_postgres.py` | 46 |
| `backend/app/core/firebase_admin.py` | 167 |
| `backend/app/core/input_validation.py` | 450 |
| `backend/app/core/listing.py` | 35 |
| `backend/app/core/redis.py` | 201 |
| `backend/app/core/redis_full.py` | 221 |
| `backend/app/core/secure_upload.py` | 404 |
| `backend/app/core/security.py` | 127 |
| `backend/app/core/security_middleware.py` | 621 |
| `backend/app/core/totp.py` | 66 |
| `backend/app/main.py` | 1415 |
| `backend/app/main_email_test.py` | 201 |
| `backend/app/main_frontend_integration.py` | 170 |
| `backend/app/main_payment_test.py` | 211 |
| `backend/app/main_simple.py` | 106 |
| `backend/app/main_test.py` | 139 |
| `backend/app/migration/data_migrator.py` | 600 |
| `backend/app/migration/legacy_extractor.py` | 285 |
| `backend/app/models/__init__.py` | 181 |
| `backend/app/models/admin_message.py` | 28 |
| `backend/app/models/ai_layer.py` | 47 |
| `backend/app/models/assessment_studio.py` | 20 |
| `backend/app/models/assignment.py` | 135 |
| `backend/app/models/blog.py` | 74 |
| `backend/app/models/bundle.py` | 36 |
| `backend/app/models/candidate.py` | 99 |
| `backend/app/models/certificate.py` | 234 |
| `backend/app/models/cohort.py` | 151 |
| `backend/app/models/company.py` | 133 |
| `backend/app/models/company_dashboard.py` | 111 |
| `backend/app/models/company_invoice.py` | 171 |
| `backend/app/models/content_library.py` | 51 |
| `backend/app/models/coupon.py` | 120 |
| `backend/app/models/course.py` | 253 |
| `backend/app/models/course_ops.py` | 23 |
| `backend/app/models/course_settings.py` | 22 |
| `backend/app/models/ebook.py` | 130 |
| `backend/app/models/edgyy_payment.py` | 111 |
| `backend/app/models/enrollment.py` | 220 |
| `backend/app/models/exam_paper.py` | 40 |
| `backend/app/models/flywheel.py` | 37 |
| `backend/app/models/funnel.py` | 24 |
| `backend/app/models/game.py` | 62 |
| `backend/app/models/gamification.py` | 138 |
| `backend/app/models/geogebra.py` | 63 |
| `backend/app/models/h5p.py` | 73 |
| `backend/app/models/hall_of_fame.py` | 38 |
| `backend/app/models/instructor_review.py` | 43 |
| `backend/app/models/internship.py` | 159 |
| `backend/app/models/internship_request.py` | 39 |
| `backend/app/models/lab_notebook.py` | 16 |
| `backend/app/models/learning_planner.py` | 60 |
| `backend/app/models/learning_release.py` | 29 |
| `backend/app/models/learning_signals.py` | 61 |
| `backend/app/models/live_class.py` | 266 |
| `backend/app/models/live_class_report.py` | 54 |
| `backend/app/models/mastery.py` | 83 |
| `backend/app/models/membership.py` | 84 |
| `backend/app/models/notification.py` | 22 |
| `backend/app/models/operations.py` | 29 |
| `backend/app/models/page_view.py` | 32 |
| `backend/app/models/payment.py` | 273 |
| `backend/app/models/quiz.py` | 182 |
| `backend/app/models/recording_lesson.py` | 27 |
| `backend/app/models/sileos_pack.py` | 167 |
| `backend/app/models/tag_cluster.py` | 22 |
| `backend/app/models/three_d.py` | 28 |
| `backend/app/models/three_d_task.py` | 53 |
| `backend/app/models/user.py` | 187 |
| `backend/app/models/webhook_event.py` | 41 |
| `backend/app/routers/__init__.py` | 3 |
| `backend/app/routers/admin.py` | 5385 |
| `backend/app/routers/admin_messages.py` | 347 |
| `backend/app/routers/ai.py` | 203 |
| `backend/app/routers/ai_engines.py` | 416 |
| `backend/app/routers/ai_tutor.py` | 374 |
| `backend/app/routers/analytics.py` | 696 |
| `backend/app/routers/assessment_studio.py` | 194 |
| `backend/app/routers/assignments.py` | 1151 |
| `backend/app/routers/auth.py` | 1767 |
| `backend/app/routers/blog.py` | 824 |
| `backend/app/routers/bundles.py` | 106 |
| `backend/app/routers/bunny.py` | 246 |
| `backend/app/routers/candidate.py` | 290 |
| `backend/app/routers/categories.py` | 106 |
| `backend/app/routers/certificate_designer.py` | 587 |
| `backend/app/routers/certificates.py` | 1887 |
| `backend/app/routers/checkout.py` | 59 |
| `backend/app/routers/chunked_upload.py` | 592 |
| `backend/app/routers/cohorts.py` | 1035 |
| `backend/app/routers/companies.py` | 1128 |
| `backend/app/routers/company_billing.py` | 379 |
| `backend/app/routers/company_dashboard.py` | 1061 |
| `backend/app/routers/content_library_admin.py` | 360 |
| `backend/app/routers/coupons.py` | 520 |
| `backend/app/routers/course_ops.py` | 172 |
| `backend/app/routers/course_packages.py` | 138 |
| `backend/app/routers/course_type_capabilities.py` | 26 |
| `backend/app/routers/courses.py` | 2607 |
| `backend/app/routers/dashboard.py` | 1053 |
| `backend/app/routers/embed.py` | 146 |
| `backend/app/routers/exam_papers.py` | 192 |
| `backend/app/routers/export_import.py` | 3387 |
| `backend/app/routers/flywheel.py` | 158 |
| `backend/app/routers/funnel.py` | 82 |
| `backend/app/routers/games.py` | 526 |
| `backend/app/routers/gamification.py` | 195 |
| `backend/app/routers/geogebra.py` | 185 |
| `backend/app/routers/gradebook.py` | 207 |
| `backend/app/routers/h5p.py` | 567 |
| `backend/app/routers/hall_of_fame.py` | 233 |
| `backend/app/routers/instructor_reviews.py` | 317 |
| `backend/app/routers/instructors.py` | 43 |
| `backend/app/routers/internships.py` | 1608 |
| `backend/app/routers/lab_studio.py` | 188 |
| `backend/app/routers/learning_planner.py` | 198 |
| `backend/app/routers/learning_signals.py` | 190 |
| `backend/app/routers/lessons.py` | 88 |
| `backend/app/routers/library.py` | 707 |
| `backend/app/routers/live_class_attendance.py` | 238 |
| `backend/app/routers/live_class_internal.py` | 150 |
| `backend/app/routers/live_class_polls.py` | 423 |
| `backend/app/routers/live_class_recordings.py` | 402 |
| `backend/app/routers/live_class_session.py` | 385 |
| `backend/app/routers/live_classes.py` | 346 |
| `backend/app/routers/mastery.py` | 188 |
| `backend/app/routers/memberships.py` | 259 |
| `backend/app/routers/notifications.py` | 65 |
| `backend/app/routers/operations.py` | 80 |
| `backend/app/routers/orders.py` | 372 |
| `backend/app/routers/parents.py` | 186 |
| `backend/app/routers/payments.py` | 1056 |
| `backend/app/routers/payments_proxy.py` | 664 |
| `backend/app/routers/player.py` | 130 |
| `backend/app/routers/progress.py` | 320 |
| `backend/app/routers/question_banks.py` | 425 |
| `backend/app/routers/quizzes.py` | 2568 |
| `backend/app/routers/recording_lessons.py` | 200 |
| `backend/app/routers/scorable_items.py` | 75 |
| `backend/app/routers/sileos.py` | 730 |
| `backend/app/routers/student_workspace.py` | 145 |
| `backend/app/routers/studio.py` | 98 |
| `backend/app/routers/superadmin.py` | 900 |
| `backend/app/routers/tag_taxonomy.py` | 75 |
| `backend/app/routers/tags.py` | 28 |
| `backend/app/routers/three_d.py` | 231 |
| `backend/app/routers/three_d_tasks.py` | 362 |
| `backend/app/routers/uploads.py` | 692 |
| `backend/app/routers/users.py` | 605 |
| `backend/app/routers/video.py` | 116 |
| `backend/app/routers/video_streaming.py` | 363 |
| `backend/app/routers/virtual_labs.py` | 369 |
| `backend/app/routers/wishlist.py` | 146 |
| `backend/app/routers/youtube_embed.py` | 260 |
| `backend/app/schemas/__init__.py` | 3 |
| `backend/app/schemas/admin.py` | 135 |
| `backend/app/schemas/assessment.py` | 50 |
| `backend/app/schemas/auth.py` | 136 |
| `backend/app/schemas/bundle.py` | 47 |
| `backend/app/schemas/candidate.py` | 92 |
| `backend/app/schemas/certificate.py` | 229 |
| `backend/app/schemas/cohort.py` | 211 |
| `backend/app/schemas/company.py` | 133 |
| `backend/app/schemas/company_billing.py` | 86 |
| `backend/app/schemas/company_dashboard.py` | 248 |
| `backend/app/schemas/company_invoice.py` | 65 |
| `backend/app/schemas/concept_lab.py` | 145 |
| `backend/app/schemas/coupon.py` | 175 |
| `backend/app/schemas/course.py` | 321 |
| `backend/app/schemas/edgyy_payment.py` | 176 |
| `backend/app/schemas/exam_paper.py` | 30 |
| `backend/app/schemas/game_config.py` | 273 |
| `backend/app/schemas/instructor_review.py` | 41 |
| `backend/app/schemas/internship.py` | 331 |
| `backend/app/schemas/lab_config.py` | 291 |
| `backend/app/schemas/live_class.py` | 272 |
| `backend/app/schemas/membership.py` | 70 |
| `backend/app/schemas/payment.py` | 101 |
| `backend/app/schemas/scorable.py` | 210 |
| `backend/app/schemas/three_d_task_config.py` | 520 |
| `backend/app/schemas/user.py` | 110 |
| `backend/app/scripts/__init__.py` | 0 |
| `backend/app/scripts/cleanup_broken_uploads.py` | 96 |
| `backend/app/scripts/delete_all_courses.py` | 149 |
| `backend/app/seed_data/sashainfinity_courses.py` | 277 |
| `backend/app/seed_data.py` | 406 |
| `backend/app/services/__init__.py` | 3 |
| `backend/app/services/ai_layer_service.py` | 267 |
| `backend/app/services/assessment_studio_service.py` | 279 |
| `backend/app/services/attendance_report.py` | 149 |
| `backend/app/services/auth_service.py` | 240 |
| `backend/app/services/certificate_html_renderer.py` | 640 |
| `backend/app/services/certificate_service.py` | 1648 |
| `backend/app/services/class_report_service.py` | 377 |
| `backend/app/services/company_scope.py` | 58 |
| `backend/app/services/coupon_service.py` | 378 |
| `backend/app/services/course_access.py` | 31 |
| `backend/app/services/course_asset_service.py` | 63 |
| `backend/app/services/course_ops_service.py` | 237 |
| `backend/app/services/course_package_service.py` | 561 |
| `backend/app/services/course_service.py` | 659 |
| `backend/app/services/email_service.py` | 1194 |
| `backend/app/services/exam_paper_service.py` | 196 |
| `backend/app/services/flywheel_service.py` | 259 |
| `backend/app/services/fulfillment_service.py` | 519 |
| `backend/app/services/funnel_service.py` | 229 |
| `backend/app/services/gamification_service.py` | 770 |
| `backend/app/services/glb_budget.py` | 114 |
| `backend/app/services/gradebook_service.py` | 244 |
| `backend/app/services/h5p_service.py` | 340 |
| `backend/app/services/invoice_pdf.py` | 207 |
| `backend/app/services/invoice_service.py` | 148 |
| `backend/app/services/jitsi_token_service.py` | 110 |
| `backend/app/services/lab_catalog_service.py` | 56 |
| `backend/app/services/lab_investigation_service.py` | 107 |
| `backend/app/services/lab_model_service.py` | 123 |
| `backend/app/services/lab_studio_service.py` | 38 |
| `backend/app/services/launch_readiness.py` | 28 |
| `backend/app/services/learning_planner_service.py` | 363 |
| `backend/app/services/learning_signals_service.py` | 440 |
| `backend/app/services/library_storage.py` | 432 |
| `backend/app/services/live_class_service.py` | 603 |
| `backend/app/services/live_recording_service.py` | 320 |
| `backend/app/services/live_reminders.py` | 319 |
| `backend/app/services/llm_provider.py` | 67 |
| `backend/app/services/mastery_service.py` | 327 |
| `backend/app/services/media_pipeline.py` | 100 |
| `backend/app/services/membership_access.py` | 87 |
| `backend/app/services/notification_service.py` | 48 |
| `backend/app/services/offline_learning_service.py` | 49 |
| `backend/app/services/operations_service.py` | 139 |
| `backend/app/services/payment_service.py` | 197 |
| `backend/app/services/pricing.py` | 353 |
| `backend/app/services/public_preview.py` | 35 |
| `backend/app/services/reconciliation.py` | 521 |
| `backend/app/services/recording_lesson_service.py` | 162 |
| `backend/app/services/refund_service.py` | 506 |
| `backend/app/services/report_theme.py` | 260 |
| `backend/app/services/retention_service.py` | 191 |
| `backend/app/services/studio_service.py` | 302 |
| `backend/app/services/supplied_lab_pack.py` | 127 |
| `backend/app/services/tag_service.py` | 252 |
| `backend/app/services/transcription_provider.py` | 38 |
| `backend/app/services/user_service.py` | 217 |
| `backend/app/services/webhook_processor.py` | 567 |
| `backend/app/services/xapi_service.py` | 48 |
| `backend/app/utils/__init__.py` | 3 |
| `backend/app/utils/email.py` | 1190 |
| `backend/app/workers/__init__.py` | 0 |
| `backend/app/workers/recording_lessons.py` | 32 |
| `backend/alembic/env.py` | 113 |
| `backend/alembic/versions/0001_baseline.py` | 40 |
| `backend/alembic/versions/0002_add_live_class_tables.py` | 205 |
| `backend/alembic/versions/0003_learning_experience.py` | 426 |
| `backend/alembic/versions/0004_learning_games.py` | 119 |
| `backend/alembic/versions/0005_digital_library.py` | 156 |
| `backend/alembic/versions/0005_money_ops.py` | 124 |
| `backend/alembic/versions/0006_course_type_normalization.py` | 56 |
| `backend/alembic/versions/0006_merge_digital_library_and_money_ops.py` | 29 |
| `backend/alembic/versions/0007_content_libraries.py` | 94 |
| `backend/alembic/versions/0008_three_d_tasks.py` | 74 |
| `backend/alembic/versions/0009_mastery_graph.py` | 102 |
| `backend/alembic/versions/0010_tag_clusters.py` | 35 |
| `backend/alembic/versions/0011_live_retention.py` | 91 |
| `backend/alembic/versions/0012_studio_settings.py` | 56 |
| `backend/alembic/versions/0013_ai_layer.py` | 63 |
| `backend/alembic/versions/0014_flywheel.py` | 57 |
| `backend/alembic/versions/0015_funnel_events.py` | 37 |
| `backend/alembic/versions/0016_course_ops.py` | 49 |
| `backend/alembic/versions/0017_coupon_membership_offer.py` | 33 |
| `backend/alembic/versions/0018_assessment_integrity.py` | 43 |
| `backend/alembic/versions/0019_media_tiers.py` | 33 |
| `backend/alembic/versions/0020_learning_signals.py` | 74 |
| `backend/alembic/versions/0021_learning_planner.py` | 79 |
| `backend/alembic/versions/0022_assessment_studio.py` | 38 |
| `backend/alembic/versions/0023_recording_lessons.py` | 44 |
| `backend/alembic/versions/0024_operations_packages.py` | 45 |
| `backend/alembic/versions/0025_course_tools.py` | 24 |
| `backend/alembic/versions/0026_transfer_lifecycle.py` | 38 |
| `backend/alembic/versions/0027_lab_notebooks.py` | 28 |
| `backend/alembic/versions/0028_exam_papers_course_links.py` | 52 |
| `backend/alembic/versions/0029_integrated_learning.py` | 19 |
| `backend/scripts/build_concept_extensions.py` | 48 |
| `backend/scripts/install_transcription_model.py` | 13 |
| `backend/scripts/migrate_wp_orders.py` | 233 |
| `backend/scripts/rehearse_course_restore.py` | 79 |
| `backend/scripts/transcribe_local.py` | 22 |
| `frontend/src/api/admin-messages.ts` | 79 |
| `frontend/src/api/admin.ts` | 449 |
| `frontend/src/api/aiLayer.ts` | 70 |
| `frontend/src/api/assessment-studio.ts` | 15 |
| `frontend/src/api/assignment.ts` | 79 |
| `frontend/src/api/auth.ts` | 244 |
| `frontend/src/api/axios.ts` | 467 |
| `frontend/src/api/blog.ts` | 96 |
| `frontend/src/api/bundle.ts` | 48 |
| `frontend/src/api/candidate.ts` | 102 |
| `frontend/src/api/cart.ts` | 100 |
| `frontend/src/api/certificateDesigner.ts` | 112 |
| `frontend/src/api/certificates.ts` | 172 |
| `frontend/src/api/chunked-upload.ts` | 308 |
| `frontend/src/api/cohort.ts` | 163 |
| `frontend/src/api/company-dashboard.ts` | 641 |
| `frontend/src/api/company.ts` | 262 |
| `frontend/src/api/companyBilling.ts` | 150 |
| `frontend/src/api/course-packages.ts` | 61 |
| `frontend/src/api/course.ts` | 391 |
| `frontend/src/api/courseOps.ts` | 27 |
| `frontend/src/api/dashboard.ts` | 293 |
| `frontend/src/api/exam-papers.ts` | 52 |
| `frontend/src/api/flywheel.ts` | 34 |
| `frontend/src/api/funnel.ts` | 48 |
| `frontend/src/api/games.ts` | 220 |
| `frontend/src/api/gamification.ts` | 104 |
| `frontend/src/api/geogebra.ts` | 52 |
| `frontend/src/api/gradebook.ts` | 109 |
| `frontend/src/api/h5p.ts` | 246 |
| `frontend/src/api/hallOfFame.ts` | 72 |
| `frontend/src/api/internship.ts` | 369 |
| `frontend/src/api/lab-studio.ts` | 158 |
| `frontend/src/api/labs.ts` | 131 |
| `frontend/src/api/library.ts` | 152 |
| `frontend/src/api/liveClasses.ts` | 268 |
| `frontend/src/api/mastery.ts` | 99 |
| `frontend/src/api/membership.ts` | 51 |
| `frontend/src/api/notifications.ts` | 19 |
| `frontend/src/api/operations.ts` | 95 |
| `frontend/src/api/planner.ts` | 26 |
| `frontend/src/api/recording-lessons.ts` | 21 |
| `frontend/src/api/scorable.ts` | 96 |
| `frontend/src/api/signals.ts` | 59 |
| `frontend/src/api/studio.ts` | 77 |
| `frontend/src/api/superadmin.ts` | 154 |
| `frontend/src/api/threeD.ts` | 43 |
| `frontend/src/api/threeDTasks.ts` | 81 |
| `frontend/src/api/upload.ts` | 188 |
| `frontend/src/api/video.ts` | 115 |
| `frontend/src/App.tsx` | 2396 |
| `frontend/src/components/about/AboutSections.module.css` | 928 |
| `frontend/src/components/about/CoreOfferingsSection.tsx` | 68 |
| `frontend/src/components/about/CTASection.tsx` | 25 |
| `frontend/src/components/about/MentorsSection.tsx` | 99 |
| `frontend/src/components/about/MissionSection.tsx` | 37 |
| `frontend/src/components/about/PageTitleSection.tsx` | 12 |
| `frontend/src/components/about/StatsSection.tsx` | 33 |
| `frontend/src/components/about/WhoWeAreSection.tsx` | 39 |
| `frontend/src/components/admin/CoursesProgressChart.tsx` | 319 |
| `frontend/src/components/admin/ExportImportPanel.tsx` | 884 |
| `frontend/src/components/admin/heatmaps.tsx` | 449 |
| `frontend/src/components/admin/ImpersonationBanner.tsx` | 165 |
| `frontend/src/components/admin/InternshipAnalyticsCharts.tsx` | 288 |
| `frontend/src/components/admin/LaunchReadiness.tsx` | 79 |
| `frontend/src/components/admin/LearningProgressChart.tsx` | 172 |
| `frontend/src/components/admin/PasswordResetLinkAction.tsx` | 147 |
| `frontend/src/components/admin/TableScrollArea.tsx` | 85 |
| `frontend/src/components/admin/TagClustersPanel.tsx` | 72 |
| `frontend/src/components/ai/AdaptiveLessonPanel.tsx` | 60 |
| `frontend/src/components/ai/TutorDrawer.tsx` | 174 |
| `frontend/src/components/assess/RubricEditor.tsx` | 111 |
| `frontend/src/components/assess/RubricScorer.tsx` | 94 |
| `frontend/src/components/assessment/BankDrawDialog.tsx` | 70 |
| `frontend/src/components/assessment/QuizCsvImport.tsx` | 64 |
| `frontend/src/components/assessment/ScorableItemsEditor.tsx` | 198 |
| `frontend/src/components/assessment/ScorableItemsPanel.tsx` | 72 |
| `frontend/src/components/auth/instructor-register-form.tsx` | 487 |
| `frontend/src/components/auth/login-form.tsx` | 604 |
| `frontend/src/components/auth/MobileNumberGate.tsx` | 144 |
| `frontend/src/components/auth/ProfileCompletionGuard.tsx` | 34 |
| `frontend/src/components/auth/register-form.tsx` | 368 |
| `frontend/src/components/auth/RoleSelectionModal.tsx` | 268 |
| `frontend/src/components/auth/unified-register-form.tsx` | 419 |
| `frontend/src/components/candidate/InternshipEligibilityWidget.tsx` | 137 |
| `frontend/src/components/candidate/TagInput.tsx` | 94 |
| `frontend/src/components/certificate/LinkedInShareDialog.tsx` | 284 |
| `frontend/src/components/certificates/designer/CertificateDesignerEditor.tsx` | 425 |
| `frontend/src/components/certificates/designer/DesignerCanvas.tsx` | 420 |
| `frontend/src/components/certificates/designer/DesignerToolbar.tsx` | 166 |
| `frontend/src/components/certificates/designer/ElementProperties.tsx` | 412 |
| `frontend/src/components/certificates/designer/LayersPanel.tsx` | 128 |
| `frontend/src/components/certificates/designer/TemplateGallery.tsx` | 202 |
| `frontend/src/components/common/ErrorBoundary.tsx` | 175 |
| `frontend/src/components/common/scroll-to-top.tsx` | 18 |
| `frontend/src/components/company/CompanyInternshipCharts.tsx` | 187 |
| `frontend/src/components/company/InterestModal.tsx` | 75 |
| `frontend/src/components/contact/ContactFormSection.module.css` | 448 |
| `frontend/src/components/contact/ContactFormSection.tsx` | 221 |
| `frontend/src/components/contact/MapSection.module.css` | 145 |
| `frontend/src/components/contact/MapSection.tsx` | 55 |
| `frontend/src/components/course/CollaboratorsBlock.tsx` | 69 |
| `frontend/src/components/course/course-card.tsx` | 328 |
| `frontend/src/components/course/CourseLinkField.tsx` | 78 |
| `frontend/src/components/course/LessonPreviewModal.tsx` | 101 |
| `frontend/src/components/course/TagsEditor.tsx` | 80 |
| `frontend/src/components/course/TemplatePicker.tsx` | 45 |
| `frontend/src/components/dashboard/charts.tsx` | 315 |
| `frontend/src/components/dashboard/ContinueLearning.tsx` | 38 |
| `frontend/src/components/dashboard/DashboardNavbar.tsx` | 220 |
| `frontend/src/components/dashboard/DashboardSidebar.tsx` | 501 |
| `frontend/src/components/dashboard/DashboardWorkspace.tsx` | 172 |
| `frontend/src/components/dashboard/MembershipCard.tsx` | 141 |
| `frontend/src/components/dashboard/MyInternshipCharts.tsx` | 216 |
| `frontend/src/components/dashboard/nav-configs.ts` | 150 |
| `frontend/src/components/dashboard/primitives.tsx` | 619 |
| `frontend/src/components/dashboard/RoleLayouts.tsx` | 61 |
| `frontend/src/components/dashboard/StudentInternshipSummary.tsx` | 92 |
| `frontend/src/components/dashboard/theme.css` | 274 |
| `frontend/src/components/dashboard/two-factor-section.tsx` | 275 |
| `frontend/src/components/dashboard/WorkspaceHeader.tsx` | 75 |
| `frontend/src/components/dashboard/WorkspaceNavigation.tsx` | 48 |
| `frontend/src/components/design-system/AstraRouteTheme.tsx` | 46 |
| `frontend/src/components/design-system/AstraSymbol.tsx` | 15 |
| `frontend/src/components/design-system/GlassSurface.tsx` | 19 |
| `frontend/src/components/design-system/PageLayout.tsx` | 102 |
| `frontend/src/components/flywheel/DigiLockerButton.tsx` | 31 |
| `frontend/src/components/flywheel/EarningsPanel.tsx` | 70 |
| `frontend/src/components/flywheel/FlywheelPanel.tsx` | 83 |
| `frontend/src/components/flywheel/FunnelPanel.tsx` | 49 |
| `frontend/src/components/flywheel/ReviewQueueCard.tsx` | 37 |
| `frontend/src/components/flywheel/TeachBackPanel.tsx` | 67 |
| `frontend/src/components/games/builderValidation.ts` | 156 |
| `frontend/src/components/games/engines/DragSort.tsx` | 258 |
| `frontend/src/components/games/engines/MatchPairs.tsx` | 174 |
| `frontend/src/components/games/engines/QuizRush.tsx` | 168 |
| `frontend/src/components/games/engines/scoring.ts` | 70 |
| `frontend/src/components/games/engines/SequenceGame.tsx` | 235 |
| `frontend/src/components/games/engines/WordBuilder.tsx` | 175 |
| `frontend/src/components/games/GamePicker.tsx` | 161 |
| `frontend/src/components/games/GamePlayer.tsx` | 138 |
| `frontend/src/components/games/GameShell.tsx` | 125 |
| `frontend/src/components/gamification/AwardToaster.tsx` | 129 |
| `frontend/src/components/gamification/BadgeGrid.tsx` | 132 |
| `frontend/src/components/gamification/LeaderboardTable.tsx` | 94 |
| `frontend/src/components/gamification/StreakCard.tsx` | 91 |
| `frontend/src/components/gamification/XPLevelCard.tsx` | 86 |
| `frontend/src/components/geogebra/GeoGebraAuthorCard.tsx` | 118 |
| `frontend/src/components/geogebra/GeoGebraEmbed.tsx` | 103 |
| `frontend/src/components/h5p/H5PLesson.tsx` | 255 |
| `frontend/src/components/h5p/H5PPicker.tsx` | 214 |
| `frontend/src/components/home/Hero3DBackground.tsx` | 45 |
| `frontend/src/components/home/HeroSection.module.css` | 302 |
| `frontend/src/components/home/ScrollStack.css` | 28 |
| `frontend/src/components/home/ScrollStack.tsx` | 312 |
| `frontend/src/components/instructor/PurchasesByCourseChart.tsx` | 164 |
| `frontend/src/components/instructor/QuizSetupModal.tsx` | 565 |
| `frontend/src/components/labs/concept-templates.ts` | 126 |
| `frontend/src/components/labs/ConceptLabPlayer.tsx` | 122 |
| `frontend/src/components/labs/diagrams/CellDiagram.tsx` | 61 |
| `frontend/src/components/labs/diagrams/SkeletonDiagram.tsx` | 82 |
| `frontend/src/components/labs/GuidedLabAuthor.tsx` | 394 |
| `frontend/src/components/labs/GuidedLabPlayer.tsx` | 295 |
| `frontend/src/components/labs/LearningPreferences.tsx` | 101 |
| `frontend/src/components/labs/native/chemistry.ts` | 81 |
| `frontend/src/components/labs/native/IdentifyLab.tsx` | 145 |
| `frontend/src/components/labs/native/ReactionLab.tsx` | 195 |
| `frontend/src/components/labs/NativeLabPlayer.tsx` | 83 |
| `frontend/src/components/labs/SuppliedLabPack.tsx` | 179 |
| `frontend/src/components/labs/VirtualLabEmbed.tsx` | 24 |
| `frontend/src/components/labs/VirtualLabPicker.tsx` | 125 |
| `frontend/src/components/labs/VirtualLabPlayer.tsx` | 108 |
| `frontend/src/components/layout/admin/admin-layout.tsx` | 26 |
| `frontend/src/components/layout/admin/superadmin-layout.tsx` | 25 |
| `frontend/src/components/layout/auth-layout.tsx` | 40 |
| `frontend/src/components/layout/footer.tsx` | 231 |
| `frontend/src/components/layout/header.tsx` | 348 |
| `frontend/src/components/layout/main-layout.tsx` | 27 |
| `frontend/src/components/live/AttendancePanel.tsx` | 82 |
| `frontend/src/components/live/ClassCountdown.tsx` | 112 |
| `frontend/src/components/live/ClassReportModal.tsx` | 190 |
| `frontend/src/components/live/DevicePrecheck.tsx` | 188 |
| `frontend/src/components/live/InstructorDock.tsx` | 234 |
| `frontend/src/components/live/JitsiStage.tsx` | 284 |
| `frontend/src/components/live/joinButtonState.ts` | 76 |
| `frontend/src/components/live/LiveStatusBadge.tsx` | 30 |
| `frontend/src/components/live/PollPanel.tsx` | 329 |
| `frontend/src/components/live/RaiseHandList.tsx` | 47 |
| `frontend/src/components/live/RecordingBadge.tsx` | 23 |
| `frontend/src/components/live/RecordingTranscript.tsx` | 45 |
| `frontend/src/components/live/StudentLiveClasses.tsx` | 68 |
| `frontend/src/components/notifications/NotificationBell.tsx` | 82 |
| `frontend/src/components/promotional/independence-day.css` | 403 |
| `frontend/src/components/promotional/IndependenceDayPopup.tsx` | 314 |
| `frontend/src/components/promotional/offer-timer.css` | 226 |
| `frontend/src/components/promotional/OfferTimerWidget.tsx` | 102 |
| `frontend/src/components/public/PageHeader.module.css` | 59 |
| `frontend/src/components/public/PageHeader.tsx` | 33 |
| `frontend/src/components/public/PublicFooter.module.css` | 142 |
| `frontend/src/components/public/PublicFooter.tsx` | 156 |
| `frontend/src/components/public/PublicHeader.module.css` | 529 |
| `frontend/src/components/public/PublicHeader.tsx` | 206 |
| `frontend/src/components/routing/lazy-page.tsx` | 23 |
| `frontend/src/components/routing/page-guides.ts` | 441 |
| `frontend/src/components/routing/PageBackButton.tsx` | 22 |
| `frontend/src/components/routing/PageGuide.tsx` | 34 |
| `frontend/src/components/routing/protected-route.tsx` | 162 |
| `frontend/src/components/signals/AdaptivePractice.tsx` | 131 |
| `frontend/src/components/signals/LessonStruggleMap.tsx` | 112 |
| `frontend/src/components/signals/StruggleProfile.tsx` | 87 |
| `frontend/src/components/SortableLecture.tsx` | 32 |
| `frontend/src/components/spoc/CohortMasteryPanel.tsx` | 67 |
| `frontend/src/components/spoc/ViewAsSpocBanner.tsx` | 86 |
| `frontend/src/components/studio/GuardianVisibility.tsx` | 43 |
| `frontend/src/components/studio/RewardDesigner.tsx` | 99 |
| `frontend/src/components/studio/ScheduleBuilder.tsx` | 80 |
| `frontend/src/components/studio/StudioFace.tsx` | 125 |
| `frontend/src/components/studio/TierPreview.tsx` | 85 |
| `frontend/src/components/three-d/DeferredThreeD.tsx` | 57 |
| `frontend/src/components/three-d/tasks/ThreeDTaskPlayer.tsx` | 380 |
| `frontend/src/components/three-d/ThreeDCheckYourself.tsx` | 33 |
| `frontend/src/components/three-d/ThreeDModelPicker.tsx` | 159 |
| `frontend/src/components/three-d/ThreeDTeachingKit.tsx` | 69 |
| `frontend/src/components/three-d/ThreeDViewer.tsx` | 637 |
| `frontend/src/components/three-d/xr-session.ts` | 183 |
| `frontend/src/components/ui/avatar.tsx` | 59 |
| `frontend/src/components/ui/badge.tsx` | 45 |
| `frontend/src/components/ui/button.tsx` | 115 |
| `frontend/src/components/ui/card.tsx` | 91 |
| `frontend/src/components/ui/confirm.tsx` | 128 |
| `frontend/src/components/ui/dialog.tsx` | 133 |
| `frontend/src/components/ui/input.tsx` | 66 |
| `frontend/src/components/ui/logo.tsx` | 116 |
| `frontend/src/components/ui/pagination.tsx` | 170 |
| `frontend/src/components/ui/progress.tsx` | 59 |
| `frontend/src/components/ui/share-button.tsx` | 145 |
| `frontend/src/components/ui/star-rating.tsx` | 121 |
| `frontend/src/components/upload/document-upload.tsx` | 196 |
| `frontend/src/components/upload/image-upload.tsx` | 225 |
| `frontend/src/components/upload/index.ts` | 3 |
| `frontend/src/components/upload/video-upload.tsx` | 145 |
| `frontend/src/components/video/AudioOnlyToggle.tsx` | 42 |
| `frontend/src/components/video/native-video-player.tsx` | 360 |
| `frontend/src/components/video/react-player.tsx` | 81 |
| `frontend/src/components/video/react-video-player.tsx` | 165 |
| `frontend/src/components/video/SashaPlayer.jsx` | 161 |
| `frontend/src/components/video/video-player.tsx` | 126 |
| `frontend/src/components/video/youtube-extracted-player.tsx` | 331 |
| `frontend/src/components/video/youtube-player.tsx` | 100 |
| `frontend/src/config/courseTypes.ts` | 102 |
| `frontend/src/config/urls.ts` | 77 |
| `frontend/src/contexts/CartContext.tsx` | 217 |
| `frontend/src/contexts/theme-context.tsx` | 197 |
| `frontend/src/css-modules.d.ts` | 14 |
| `frontend/src/hooks/use-auth.tsx` | 241 |
| `frontend/src/hooks/use-debounced-value.ts` | 16 |
| `frontend/src/hooks/use-google-oauth.tsx` | 273 |
| `frontend/src/hooks/use-page-view-tracker.tsx` | 101 |
| `frontend/src/hooks/use-seo.tsx` | 207 |
| `frontend/src/hooks/useNavBadges.ts` | 33 |
| `frontend/src/hooks/useVideoPlayer.js` | 126 |
| `frontend/src/lib/certificateAssetSrc.ts` | 79 |
| `frontend/src/lib/certificateDesignerTypes.ts` | 142 |
| `frontend/src/lib/certificateTemplatePicker.ts` | 104 |
| `frontend/src/lib/curatedFonts.ts` | 81 |
| `frontend/src/lib/designerDraftStorage.ts` | 59 |
| `frontend/src/lib/designerHistory.ts` | 75 |
| `frontend/src/lib/designerSerialize.ts` | 53 |
| `frontend/src/lib/designerSnap.ts` | 60 |
| `frontend/src/lib/firebase.ts` | 73 |
| `frontend/src/lib/gradebook.ts` | 115 |
| `frontend/src/lib/lessonContentSync.ts` | 91 |
| `frontend/src/main.tsx` | 53 |
| `frontend/src/offline/learning.ts` | 110 |
| `frontend/src/offline/main.tsx` | 318 |
| `frontend/src/offline/OfflineSyncBridge.tsx` | 24 |
| `frontend/src/offline/storage.ts` | 117 |
| `frontend/src/pages/About.tsx` | 22 |
| `frontend/src/pages/admin/analytics.tsx` | 462 |
| `frontend/src/pages/admin/approvals.tsx` | 174 |
| `frontend/src/pages/admin/blog-templates.tsx` | 12 |
| `frontend/src/pages/admin/blogs.tsx` | 557 |
| `frontend/src/pages/admin/bundles.tsx` | 545 |
| `frontend/src/pages/admin/categories.tsx` | 364 |
| `frontend/src/pages/admin/certificates.tsx` | 523 |
| `frontend/src/pages/admin/cohorts.tsx` | 712 |
| `frontend/src/pages/admin/colleges.tsx` | 264 |
| `frontend/src/pages/admin/companies.tsx` | 884 |
| `frontend/src/pages/admin/company-invoices.tsx` | 794 |
| `frontend/src/pages/admin/content-libraries.tsx` | 934 |
| `frontend/src/pages/admin/coupons.tsx` | 802 |
| `frontend/src/pages/admin/courses.tsx` | 821 |
| `frontend/src/pages/admin/dashboard.tsx` | 521 |
| `frontend/src/pages/admin/enrollments.tsx` | 524 |
| `frontend/src/pages/admin/exam-pricing.tsx` | 235 |
| `frontend/src/pages/admin/hall-of-fame.tsx` | 518 |
| `frontend/src/pages/admin/instructors.tsx` | 538 |
| `frontend/src/pages/admin/internship-requests.tsx` | 646 |
| `frontend/src/pages/admin/internships.tsx` | 1414 |
| `frontend/src/pages/admin/lessons.tsx` | 295 |
| `frontend/src/pages/admin/manage.tsx` | 436 |
| `frontend/src/pages/admin/memberships.tsx` | 723 |
| `frontend/src/pages/admin/messages.tsx` | 358 |
| `frontend/src/pages/admin/new-course.tsx` | 478 |
| `frontend/src/pages/admin/operations.tsx` | 679 |
| `frontend/src/pages/admin/orders.tsx` | 664 |
| `frontend/src/pages/admin/quizzes.tsx` | 309 |
| `frontend/src/pages/admin/reviews.tsx` | 184 |
| `frontend/src/pages/admin/settings.tsx` | 956 |
| `frontend/src/pages/admin/spocs.tsx` | 427 |
| `frontend/src/pages/admin/student-activity.tsx` | 619 |
| `frontend/src/pages/admin/students.tsx` | 601 |
| `frontend/src/pages/admin/tags.tsx` | 360 |
| `frontend/src/pages/assignment-submission.tsx` | 718 |
| `frontend/src/pages/auth/forgot-password.tsx` | 123 |
| `frontend/src/pages/auth/linkedin-callback.tsx` | 53 |
| `frontend/src/pages/auth/login.tsx` | 5 |
| `frontend/src/pages/auth/register.tsx` | 9 |
| `frontend/src/pages/auth/reset-password.tsx` | 143 |
| `frontend/src/pages/auth/verify-email.tsx` | 191 |
| `frontend/src/pages/blog-detail.tsx` | 541 |
| `frontend/src/pages/blog.tsx` | 421 |
| `frontend/src/pages/bundle-detail.tsx` | 285 |
| `frontend/src/pages/bundles.tsx` | 114 |
| `frontend/src/pages/cart.tsx` | 314 |
| `frontend/src/pages/categories.tsx` | 187 |
| `frontend/src/pages/category-meiporul.tsx` | 254 |
| `frontend/src/pages/category-seyappaduporul.tsx` | 251 |
| `frontend/src/pages/category-utporul.tsx` | 253 |
| `frontend/src/pages/certificate.tsx` | 303 |
| `frontend/src/pages/checkout.tsx` | 770 |
| `frontend/src/pages/company/dashboard.tsx` | 3026 |
| `frontend/src/pages/Contact.tsx` | 18 |
| `frontend/src/pages/course-detail.tsx` | 1574 |
| `frontend/src/pages/courses.tsx` | 791 |
| `frontend/src/pages/dashboard/analytics-print.css` | 55 |
| `frontend/src/pages/dashboard/analytics.tsx` | 653 |
| `frontend/src/pages/dashboard/internship-inbox.tsx` | 138 |
| `frontend/src/pages/dashboard/internship-profile.tsx` | 438 |
| `frontend/src/pages/dashboard/messages.tsx` | 96 |
| `frontend/src/pages/dashboard/my-internship-detail.tsx` | 198 |
| `frontend/src/pages/dashboard/my-internships.tsx` | 260 |
| `frontend/src/pages/dashboard/my-vouchers.tsx` | 185 |
| `frontend/src/pages/dashboard.tsx` | 437 |
| `frontend/src/pages/exam-papers.tsx` | 423 |
| `frontend/src/pages/for-companies/signup.tsx` | 239 |
| `frontend/src/pages/for-companies.tsx` | 74 |
| `frontend/src/pages/game-play.tsx` | 121 |
| `frontend/src/pages/hall-of-fame.tsx` | 412 |
| `frontend/src/pages/home.css` | 724 |
| `frontend/src/pages/Home.tsx` | 910 |
| `frontend/src/pages/instructor/analytics.tsx` | 243 |
| `frontend/src/pages/instructor/assessment-studio.tsx` | 924 |
| `frontend/src/pages/instructor/assignment-builder.tsx` | 960 |
| `frontend/src/pages/instructor/assignment-grading.tsx` | 750 |
| `frontend/src/pages/instructor/blog-editor.tsx` | 830 |
| `frontend/src/pages/instructor/blog.tsx` | 322 |
| `frontend/src/pages/instructor/certificate-designer.tsx` | 105 |
| `frontend/src/pages/instructor/course-coverage.tsx` | 384 |
| `frontend/src/pages/instructor/course-packages.tsx` | 404 |
| `frontend/src/pages/instructor/course-start.tsx` | 176 |
| `frontend/src/pages/instructor/courses.tsx` | 672 |
| `frontend/src/pages/instructor/create-course.tsx` | 2602 |
| `frontend/src/pages/instructor/dashboard.tsx` | 516 |
| `frontend/src/pages/instructor/ebooks.tsx` | 660 |
| `frontend/src/pages/instructor/edit-course.tsx` | 2922 |
| `frontend/src/pages/instructor/game-builder.tsx` | 1136 |
| `frontend/src/pages/instructor/games.tsx` | 649 |
| `frontend/src/pages/instructor/gradebook.tsx` | 227 |
| `frontend/src/pages/instructor/grading-queue.tsx` | 431 |
| `frontend/src/pages/instructor/grading.tsx` | 125 |
| `frontend/src/pages/instructor/h5p-library.tsx` | 402 |
| `frontend/src/pages/instructor/insights.tsx` | 399 |
| `frontend/src/pages/instructor/interventions.tsx` | 258 |
| `frontend/src/pages/instructor/lab-studio.tsx` | 527 |
| `frontend/src/pages/instructor/live-class-console.tsx` | 169 |
| `frontend/src/pages/instructor/live-class-new.tsx` | 526 |
| `frontend/src/pages/instructor/live-class-report.tsx` | 372 |
| `frontend/src/pages/instructor/live-classes.tsx` | 634 |
| `frontend/src/pages/instructor/past-classes.tsx` | 196 |
| `frontend/src/pages/instructor/quiz-builder.tsx` | 1397 |
| `frontend/src/pages/instructor/quizBuilderValidation.ts` | 220 |
| `frontend/src/pages/instructor/recording-lessons.tsx` | 590 |
| `frontend/src/pages/instructor/review-queue.tsx` | 458 |
| `frontend/src/pages/instructor/students.tsx` | 572 |
| `frontend/src/pages/instructor/three-d-tasks.tsx` | 1465 |
| `frontend/src/pages/instructor-profile.tsx` | 503 |
| `frontend/src/pages/internship-detail.tsx` | 261 |
| `frontend/src/pages/internships.tsx` | 119 |
| `frontend/src/pages/lab-workspace.tsx` | 213 |
| `frontend/src/pages/labs.tsx` | 322 |
| `frontend/src/pages/leaderboard.tsx` | 114 |
| `frontend/src/pages/lesson-redesigned.tsx` | 2765 |
| `frontend/src/pages/library-detail.tsx` | 144 |
| `frontend/src/pages/library.tsx` | 186 |
| `frontend/src/pages/meiporul-ar.tsx` | 529 |
| `frontend/src/pages/membership.tsx` | 267 |
| `frontend/src/pages/my-courses.tsx` | 257 |
| `frontend/src/pages/my-library.tsx` | 107 |
| `frontend/src/pages/not-found.tsx` | 126 |
| `frontend/src/pages/parent/dashboard.tsx` | 155 |
| `frontend/src/pages/privacy.tsx` | 637 |
| `frontend/src/pages/profile.tsx` | 1071 |
| `frontend/src/pages/public-profile.tsx` | 266 |
| `frontend/src/pages/quiz-taking.tsx` | 1173 |
| `frontend/src/pages/recording-lesson.tsx` | 69 |
| `frontend/src/pages/refund-policy.tsx` | 246 |
| `frontend/src/pages/search.tsx` | 363 |
| `frontend/src/pages/server-down.tsx` | 276 |
| `frontend/src/pages/settings.tsx` | 314 |
| `frontend/src/pages/shipping.tsx` | 330 |
| `frontend/src/pages/spoc/blog.tsx` | 367 |
| `frontend/src/pages/spoc/cohort.tsx` | 645 |
| `frontend/src/pages/spoc/dashboard.tsx` | 328 |
| `frontend/src/pages/spoc/internship.tsx` | 219 |
| `frontend/src/pages/spoc/profile.tsx` | 339 |
| `frontend/src/pages/student/blog-create.tsx` | 12 |
| `frontend/src/pages/student/learning-plan.tsx` | 689 |
| `frontend/src/pages/student/live-class-join.tsx` | 112 |
| `frontend/src/pages/student/live-class-recording.tsx` | 108 |
| `frontend/src/pages/student/live-classes.tsx` | 207 |
| `frontend/src/pages/student/my-grades.tsx` | 197 |
| `frontend/src/pages/student/my-mastery.tsx` | 333 |
| `frontend/src/pages/superadmin/admins.tsx` | 219 |
| `frontend/src/pages/superadmin/audit.tsx` | 247 |
| `frontend/src/pages/superadmin/dashboard.tsx` | 417 |
| `frontend/src/pages/superadmin/instructors.tsx` | 230 |
| `frontend/src/pages/superadmin/students.tsx` | 235 |
| `frontend/src/pages/superadmin/use-impersonate.ts` | 114 |
| `frontend/src/pages/terms.tsx` | 335 |
| `frontend/src/pages/verify-certificate.tsx` | 695 |
| `frontend/src/pages/wishlist.tsx` | 234 |
| `frontend/src/Sasha Certificate (Standalone).html` | 185 |
| `frontend/src/store/auth.ts` | 724 |
| `frontend/src/store/cartStore.ts` | 179 |
| `frontend/src/store/course.ts` | 311 |
| `frontend/src/store/liveClassStore.ts` | 110 |
| `frontend/src/styles/astra-glass.css` | 1249 |
| `frontend/src/styles/astra-tokens.css` | 41 |
| `frontend/src/styles/category-page.module.css` | 445 |
| `frontend/src/styles/globals.css` | 1249 |
| `frontend/src/styles/home.css` | 73 |
| `frontend/src/styles/page-redesign.css` | 1514 |
| `frontend/src/styles/sasha-design.css` | 801 |
| `frontend/src/test-setup.ts` | 1 |
| `frontend/src/types/index.ts` | 637 |
| `frontend/src/utils/animations.ts` | 123 |
| `frontend/src/utils/auth-helper.ts` | 27 |
| `frontend/src/utils/certificate-share.ts` | 112 |
| `frontend/src/utils/cn.ts` | 6 |
| `frontend/src/utils/media.ts` | 96 |
| `frontend/src/utils/phone.ts` | 24 |
| `frontend/src/utils/role-routing.ts` | 35 |
| `frontend/src/utils/sanitize.ts` | 11 |
| `frontend/src/utils/slug.ts` | 26 |
| `frontend/src/vite-env.d.ts` | 23 |
| `frontend/labs/runtime/concept-engine.js` | 62 |
| `frontend/labs/runtime/concept.html` | 4 |
| `frontend/labs/runtime/curriculum.js` | 319 |
| `frontend/labs/runtime/lab3d.js` | 191 |
| `frontend/labs/runtime/labkit.css` | 130 |
| `frontend/labs/runtime/labkit.js` | 197 |
| `frontend/labs/runtime/spatial-bridge.js` | 182 |
| `frontend/labs/runtime/spatial-only.css` | 20 |
| `frontend/labs/runtime/xrkit.js` | 162 |
| `frontend/labs/simulations/biology/biotech-pcr-lab/simulation.js` | 139 |
| `frontend/labs/simulations/biology/biotech-pcr-lab/view.html` | 48 |
| `frontend/labs/simulations/biology/dna-helix-3d/simulation.js` | 149 |
| `frontend/labs/simulations/biology/dna-helix-3d/view.html` | 52 |
| `frontend/labs/simulations/biology/genetics-punnett/simulation.js` | 68 |
| `frontend/labs/simulations/biology/genetics-punnett/styles.css` | 9 |
| `frontend/labs/simulations/biology/genetics-punnett/view.html` | 69 |
| `frontend/labs/simulations/biology/heart-circulation-lab/simulation.js` | 128 |
| `frontend/labs/simulations/biology/heart-circulation-lab/view.html` | 50 |
| `frontend/labs/simulations/biology/photosynthesis-lab/simulation.js` | 117 |
| `frontend/labs/simulations/biology/photosynthesis-lab/view.html` | 49 |
| `frontend/labs/simulations/chemistry/ideal-gas-lab/simulation.js` | 132 |
| `frontend/labs/simulations/chemistry/ideal-gas-lab/view.html` | 53 |
| `frontend/labs/simulations/chemistry/kinetics-lab/simulation.js` | 138 |
| `frontend/labs/simulations/chemistry/kinetics-lab/view.html` | 53 |
| `frontend/labs/simulations/chemistry/molecule-viewer-3d/simulation.js` | 117 |
| `frontend/labs/simulations/chemistry/molecule-viewer-3d/view.html` | 55 |
| `frontend/labs/simulations/chemistry/periodic-table-lab/simulation.js` | 110 |
| `frontend/labs/simulations/chemistry/periodic-table-lab/styles.css` | 12 |
| `frontend/labs/simulations/chemistry/periodic-table-lab/view.html` | 56 |
| `frontend/labs/simulations/chemistry/titration-lab/simulation.js` | 147 |
| `frontend/labs/simulations/chemistry/titration-lab/view.html` | 56 |
| `frontend/labs/simulations/math/circles-lab/simulation.js` | 95 |
| `frontend/labs/simulations/math/circles-lab/view.html` | 51 |
| `frontend/labs/simulations/math/conic-sections-3d/simulation.js` | 113 |
| `frontend/labs/simulations/math/conic-sections-3d/view.html` | 55 |
| `frontend/labs/simulations/math/fractions-explorer/simulation.js` | 61 |
| `frontend/labs/simulations/math/fractions-explorer/view.html` | 52 |
| `frontend/labs/simulations/math/limits-lab/simulation.js` | 101 |
| `frontend/labs/simulations/math/limits-lab/view.html` | 51 |
| `frontend/labs/simulations/math/line-explorer/simulation.js` | 424 |
| `frontend/labs/simulations/math/line-explorer/styles.css` | 126 |
| `frontend/labs/simulations/math/line-explorer/view.html` | 130 |
| `frontend/labs/simulations/math/matrix-lab/simulation.js` | 130 |
| `frontend/labs/simulations/math/matrix-lab/view.html` | 55 |
| `frontend/labs/simulations/math/number-lab/simulation.js` | 65 |
| `frontend/labs/simulations/math/number-lab/view.html` | 49 |
| `frontend/labs/simulations/math/probability-lab/simulation.js` | 104 |
| `frontend/labs/simulations/math/probability-lab/view.html` | 60 |
| `frontend/labs/simulations/math/progressions-lab/simulation.js` | 66 |
| `frontend/labs/simulations/math/progressions-lab/view.html` | 48 |
| `frontend/labs/simulations/math/pythagoras-explorer/simulation.js` | 117 |
| `frontend/labs/simulations/math/pythagoras-explorer/view.html` | 47 |
| `frontend/labs/simulations/math/quadratic-explorer/simulation.js` | 103 |
| `frontend/labs/simulations/math/quadratic-explorer/view.html` | 53 |
| `frontend/labs/simulations/math/solids-3d/simulation.js` | 91 |
| `frontend/labs/simulations/math/solids-3d/view.html` | 60 |
| `frontend/labs/simulations/math/statistics-lab/simulation.js` | 144 |
| `frontend/labs/simulations/math/statistics-lab/view.html` | 53 |
| `frontend/labs/simulations/math/symmetry-3d/simulation.js` | 124 |
| `frontend/labs/simulations/math/symmetry-3d/view.html` | 59 |
| `frontend/labs/simulations/math/triangles-lab/simulation.js` | 116 |
| `frontend/labs/simulations/math/triangles-lab/view.html` | 51 |
| `frontend/labs/simulations/math/trigonometry-explorer/simulation.js` | 103 |
| `frontend/labs/simulations/math/trigonometry-explorer/view.html` | 53 |
| `frontend/labs/simulations/math/unit-circle-lab/simulation.js` | 139 |
| `frontend/labs/simulations/math/unit-circle-lab/view.html` | 50 |
| `frontend/labs/simulations/math/venn-sets-lab/simulation.js` | 103 |
| `frontend/labs/simulations/math/venn-sets-lab/view.html` | 53 |
| `frontend/labs/simulations/physics/electrostatics-lab/simulation.js` | 126 |
| `frontend/labs/simulations/physics/electrostatics-lab/view.html` | 48 |
| `frontend/labs/simulations/physics/faraday-lab/simulation.js` | 172 |
| `frontend/labs/simulations/physics/faraday-lab/view.html` | 49 |
| `frontend/labs/simulations/physics/photoelectric-lab/simulation.js` | 131 |
| `frontend/labs/simulations/physics/photoelectric-lab/view.html` | 55 |
| `frontend/labs/simulations/physics/projectile-motion/simulation.js` | 129 |
| `frontend/labs/simulations/physics/projectile-motion/view.html` | 59 |
| `frontend/labs/simulations/physics/radioactivity-lab/simulation.js` | 95 |
| `frontend/labs/simulations/physics/radioactivity-lab/view.html` | 50 |
| `frontend/labs/simulations/physics/simple-pendulum/simulation.js` | 108 |
| `frontend/labs/simulations/physics/simple-pendulum/view.html` | 57 |
| `frontend/labs/simulations/physics/wave-motion/simulation.js` | 86 |
| `frontend/labs/simulations/physics/wave-motion/view.html` | 50 |
| `frontend/labs/simulations/science/acids-bases-ph/simulation.js` | 112 |
| `frontend/labs/simulations/science/acids-bases-ph/view.html` | 63 |
| `frontend/labs/simulations/science/atom-builder-3d/simulation.js` | 134 |
| `frontend/labs/simulations/science/atom-builder-3d/view.html` | 51 |
| `frontend/labs/simulations/science/balance-equations/simulation.js` | 159 |
| `frontend/labs/simulations/science/balance-equations/styles.css` | 13 |
| `frontend/labs/simulations/science/balance-equations/view.html` | 64 |
| `frontend/labs/simulations/science/earth-moon-sun-3d/simulation.js` | 131 |
| `frontend/labs/simulations/science/earth-moon-sun-3d/view.html` | 58 |
| `frontend/labs/simulations/science/electric-circuits/simulation.js` | 190 |
| `frontend/labs/simulations/science/electric-circuits/view.html` | 56 |
| `frontend/labs/simulations/science/force-pressure-friction/simulation.js` | 156 |
| `frontend/labs/simulations/science/force-pressure-friction/view.html` | 65 |
| `frontend/labs/simulations/science/heat-transfer-lab/simulation.js` | 201 |
| `frontend/labs/simulations/science/heat-transfer-lab/view.html` | 66 |
| `frontend/labs/simulations/science/human-eye-lab/simulation.js` | 134 |
| `frontend/labs/simulations/science/human-eye-lab/view.html` | 52 |
| `frontend/labs/simulations/science/light-optics/simulation.js` | 139 |
| `frontend/labs/simulations/science/light-optics/view.html` | 54 |
| `frontend/labs/simulations/science/magnet-lab/simulation.js` | 182 |
| `frontend/labs/simulations/science/magnet-lab/view.html` | 51 |
| `frontend/labs/simulations/science/magnetism-current/simulation.js` | 164 |
| `frontend/labs/simulations/science/magnetism-current/view.html` | 50 |
| `frontend/labs/simulations/science/motion-graphs/simulation.js` | 122 |
| `frontend/labs/simulations/science/motion-graphs/view.html` | 51 |
| `frontend/labs/simulations/science/neuron-reflex-lab/simulation.js` | 188 |
| `frontend/labs/simulations/science/neuron-reflex-lab/view.html` | 52 |
| `frontend/labs/simulations/science/plant-animal-cell/simulation.js` | 67 |
| `frontend/labs/simulations/science/plant-animal-cell/styles.css` | 9 |
| `frontend/labs/simulations/science/plant-animal-cell/view.html` | 150 |
| `frontend/labs/simulations/science/predator-prey/simulation.js` | 96 |
| `frontend/labs/simulations/science/predator-prey/view.html` | 56 |
| `frontend/labs/simulations/science/reactivity-series/simulation.js` | 143 |
| `frontend/labs/simulations/science/reactivity-series/styles.css` | 14 |
| `frontend/labs/simulations/science/reactivity-series/view.html` | 53 |
| `frontend/labs/simulations/science/reproduction-lab/simulation.js` | 139 |
| `frontend/labs/simulations/science/reproduction-lab/view.html` | 48 |
| `frontend/labs/simulations/science/separation-lab/simulation.js` | 176 |
| `frontend/labs/simulations/science/separation-lab/view.html` | 49 |
| `frontend/labs/simulations/science/solar-system-3d/simulation.js` | 140 |
| `frontend/labs/simulations/science/solar-system-3d/view.html` | 55 |
| `frontend/labs/simulations/science/sundial-3d/simulation.js` | 111 |
| `frontend/labs/simulations/science/sundial-3d/view.html` | 54 |
| `frontend/labs/simulations/science/water-states-3d/simulation.js` | 114 |
| `frontend/labs/simulations/science/water-states-3d/view.html` | 55 |
| `frontend/labs/simulations/science/wind-pressure-lab/simulation.js` | 164 |
| `frontend/labs/simulations/science/wind-pressure-lab/view.html` | 50 |
| `frontend/labs/simulations/xr/molecule-viewer-xr/simulation.js` | 130 |
| `frontend/labs/simulations/xr/molecule-viewer-xr/view.html` | 65 |
| `frontend/labs/simulations/xr/solar-system-xr/simulation.js` | 151 |
| `frontend/labs/simulations/xr/solar-system-xr/view.html` | 54 |
| `frontend/scripts/build-labs.mjs` | 100 |
| `flutter_app/lib/config/app_config.dart` | 78 |
| `flutter_app/lib/config/design_tokens.dart` | 157 |
| `flutter_app/lib/config/routes.dart` | 316 |
| `flutter_app/lib/config/theme.dart` | 365 |
| `flutter_app/lib/config/theme_mode_provider.dart` | 49 |
| `flutter_app/lib/core/auth/session_events.dart` | 14 |
| `flutter_app/lib/core/constants/api_endpoints.dart` | 174 |
| `flutter_app/lib/core/constants/assets.dart` | 52 |
| `flutter_app/lib/core/constants/storage_keys.dart` | 51 |
| `flutter_app/lib/core/errors/exceptions.dart` | 104 |
| `flutter_app/lib/core/errors/failures.dart` | 40 |
| `flutter_app/lib/core/errors/failures.freezed.dart` | 1645 |
| `flutter_app/lib/core/network/api_client.dart` | 154 |
| `flutter_app/lib/core/network/cache_interceptor.dart` | 72 |
| `flutter_app/lib/core/network/interceptors.dart` | 256 |
| `flutter_app/lib/core/network/network_provider.dart` | 53 |
| `flutter_app/lib/core/network/network_provider.g.dart` | 60 |
| `flutter_app/lib/core/network/retry_interceptor.dart` | 59 |
| `flutter_app/lib/core/services/content_sync.dart` | 65 |
| `flutter_app/lib/core/services/deep_link_service.dart` | 35 |
| `flutter_app/lib/core/services/firebase_messaging_service.dart` | 162 |
| `flutter_app/lib/core/services/initialization_service.dart` | 49 |
| `flutter_app/lib/core/storage/cache_storage.dart` | 66 |
| `flutter_app/lib/core/storage/prefs_storage.dart` | 72 |
| `flutter_app/lib/core/storage/secure_storage.dart` | 87 |
| `flutter_app/lib/core/utils/bunny_video.dart` | 55 |
| `flutter_app/lib/core/utils/failure_logger.dart` | 56 |
| `flutter_app/lib/features/about/presentation/pages/about_page.dart` | 271 |
| `flutter_app/lib/features/admin/data/datasources/admin_remote_datasource.dart` | 166 |
| `flutter_app/lib/features/admin/data/repositories/admin_repository_impl.dart` | 191 |
| `flutter_app/lib/features/admin/domain/repositories/admin_repository.dart` | 49 |
| `flutter_app/lib/features/admin/presentation/pages/admin_courses_page.dart` | 328 |
| `flutter_app/lib/features/admin/presentation/pages/admin_dashboard_page.dart` | 313 |
| `flutter_app/lib/features/admin/presentation/pages/admin_orders_page.dart` | 203 |
| `flutter_app/lib/features/admin/presentation/pages/admin_scaffold.dart` | 89 |
| `flutter_app/lib/features/admin/presentation/pages/admin_staff_page.dart` | 410 |
| `flutter_app/lib/features/admin/presentation/pages/admin_students_page.dart` | 395 |
| `flutter_app/lib/features/admin/presentation/providers/admin_provider.dart` | 135 |
| `flutter_app/lib/features/admin/presentation/providers/admin_provider.g.dart` | 967 |
| `flutter_app/lib/features/admin/presentation/widgets/admin_filter_chips.dart` | 63 |
| `flutter_app/lib/features/admin/presentation/widgets/admin_search_bar.dart` | 74 |
| `flutter_app/lib/features/admin/presentation/widgets/admin_stat_card.dart` | 84 |
| `flutter_app/lib/features/admin/presentation/widgets/admin_status_chip.dart` | 64 |
| `flutter_app/lib/features/admin/presentation/widgets/admin_user_list_tile.dart` | 164 |
| `flutter_app/lib/features/ar_gallery/presentation/pages/ar_gallery_page.dart` | 537 |
| `flutter_app/lib/features/ar_gallery/presentation/pages/model_viewer_page.dart` | 305 |
| `flutter_app/lib/features/assignments/data/datasources/assignment_remote_datasource.dart` | 65 |
| `flutter_app/lib/features/assignments/data/models/assignment_model.dart` | 69 |
| `flutter_app/lib/features/assignments/data/models/assignment_model.freezed.dart` | 668 |
| `flutter_app/lib/features/assignments/data/models/assignment_model.g.dart` | 62 |
| `flutter_app/lib/features/assignments/data/repositories/assignment_repository_impl.dart` | 45 |
| `flutter_app/lib/features/assignments/domain/entities/assignment.dart` | 31 |
| `flutter_app/lib/features/assignments/domain/entities/assignment.freezed.dart` | 592 |
| `flutter_app/lib/features/assignments/domain/repositories/assignment_repository.dart` | 13 |
| `flutter_app/lib/features/assignments/presentation/pages/assignment_page.dart` | 137 |
| `flutter_app/lib/features/assignments/presentation/providers/assignment_provider.dart` | 59 |
| `flutter_app/lib/features/assignments/presentation/providers/assignment_provider.g.dart` | 199 |
| `flutter_app/lib/features/auth/data/datasources/auth_remote_datasource.dart` | 220 |
| `flutter_app/lib/features/auth/data/models/user_model.dart` | 71 |
| `flutter_app/lib/features/auth/data/models/user_model.freezed.dart` | 362 |
| `flutter_app/lib/features/auth/data/models/user_model.g.dart` | 33 |
| `flutter_app/lib/features/auth/data/repositories/auth_repository_impl.dart` | 421 |
| `flutter_app/lib/features/auth/data/services/google_signin_service.dart` | 31 |
| `flutter_app/lib/features/auth/domain/entities/google_auth_result.dart` | 18 |
| `flutter_app/lib/features/auth/domain/entities/google_auth_result.freezed.dart` | 425 |
| `flutter_app/lib/features/auth/domain/entities/user.dart` | 28 |
| `flutter_app/lib/features/auth/domain/entities/user.freezed.dart` | 311 |
| `flutter_app/lib/features/auth/domain/repositories/auth_repository.dart` | 42 |
| `flutter_app/lib/features/auth/domain/usecases/login_usecase.dart` | 17 |
| `flutter_app/lib/features/auth/domain/usecases/logout_usecase.dart` | 13 |
| `flutter_app/lib/features/auth/domain/usecases/register_usecase.dart` | 28 |
| `flutter_app/lib/features/auth/presentation/pages/forgot_password_page.dart` | 188 |
| `flutter_app/lib/features/auth/presentation/pages/get_started_page.dart` | 242 |
| `flutter_app/lib/features/auth/presentation/pages/login_page.dart` | 207 |
| `flutter_app/lib/features/auth/presentation/pages/register_page.dart` | 171 |
| `flutter_app/lib/features/auth/presentation/pages/reset_password_page.dart` | 219 |
| `flutter_app/lib/features/auth/presentation/pages/role_selection_page.dart` | 161 |
| `flutter_app/lib/features/auth/presentation/pages/splash_page.dart` | 119 |
| `flutter_app/lib/features/auth/presentation/pages/verify_email_page.dart` | 197 |
| `flutter_app/lib/features/auth/presentation/providers/auth_provider.dart` | 379 |
| `flutter_app/lib/features/auth/presentation/providers/auth_provider.g.dart` | 129 |
| `flutter_app/lib/features/auth/presentation/providers/auth_state.dart` | 35 |
| `flutter_app/lib/features/auth/presentation/providers/auth_state.freezed.dart` | 1339 |
| `flutter_app/lib/features/auth/presentation/providers/email_verification_provider.dart` | 64 |
| `flutter_app/lib/features/auth/presentation/providers/email_verification_provider.g.dart` | 31 |
| `flutter_app/lib/features/auth/presentation/providers/onboarding_provider.dart` | 34 |
| `flutter_app/lib/features/auth/presentation/providers/password_reset_provider.dart` | 71 |
| `flutter_app/lib/features/auth/presentation/providers/password_reset_provider.g.dart` | 30 |
| `flutter_app/lib/features/auth/presentation/providers/pending_role_selection.dart` | 28 |
| `flutter_app/lib/features/auth/presentation/providers/pending_role_selection.g.dart` | 27 |
| `flutter_app/lib/features/auth/presentation/utils/auth_error_text.dart` | 42 |
| `flutter_app/lib/features/auth/presentation/widgets/login_form.dart` | 169 |
| `flutter_app/lib/features/auth/presentation/widgets/login_hero.dart` | 132 |
| `flutter_app/lib/features/auth/presentation/widgets/register_form.dart` | 688 |
| `flutter_app/lib/features/auth/presentation/widgets/role_selection_sheet.dart` | 179 |
| `flutter_app/lib/features/auth/presentation/widgets/social_login_buttons.dart` | 143 |
| `flutter_app/lib/features/blog/presentation/pages/blog_detail_page.dart` | 293 |
| `flutter_app/lib/features/blog/presentation/pages/blog_list_page.dart` | 148 |
| `flutter_app/lib/features/cart/presentation/pages/cart_page.dart` | 166 |
| `flutter_app/lib/features/cart/presentation/providers/cart_provider.dart` | 26 |
| `flutter_app/lib/features/certificates/presentation/pages/verify_certificate_page.dart` | 219 |
| `flutter_app/lib/features/companies/presentation/pages/company_signup_page.dart` | 324 |
| `flutter_app/lib/features/companies/presentation/pages/for_companies_page.dart` | 172 |
| `flutter_app/lib/features/courses/data/datasources/course_remote_datasource.dart` | 302 |
| `flutter_app/lib/features/courses/data/models/course_model.dart` | 141 |
| `flutter_app/lib/features/courses/data/models/course_model.freezed.dart` | 1588 |
| `flutter_app/lib/features/courses/data/models/course_model.g.dart` | 156 |
| `flutter_app/lib/features/courses/data/models/lesson_model.dart` | 87 |
| `flutter_app/lib/features/courses/data/models/lesson_model.freezed.dart` | 798 |
| `flutter_app/lib/features/courses/data/models/lesson_model.g.dart` | 67 |
| `flutter_app/lib/features/courses/data/repositories/course_repository_impl.dart` | 206 |
| `flutter_app/lib/features/courses/domain/entities/certificate.dart` | 15 |
| `flutter_app/lib/features/courses/domain/entities/certificate.freezed.dart` | 252 |
| `flutter_app/lib/features/courses/domain/entities/course.dart` | 74 |
| `flutter_app/lib/features/courses/domain/entities/course.freezed.dart` | 1199 |
| `flutter_app/lib/features/courses/domain/entities/lesson.dart` | 38 |
| `flutter_app/lib/features/courses/domain/entities/lesson.freezed.dart` | 681 |
| `flutter_app/lib/features/courses/domain/repositories/course_repository.dart` | 43 |
| `flutter_app/lib/features/courses/domain/usecases/course_usecases.dart` | 79 |
| `flutter_app/lib/features/courses/presentation/pages/all_courses_page.dart` | 467 |
| `flutter_app/lib/features/courses/presentation/pages/course_detail_page.dart` | 1874 |
| `flutter_app/lib/features/courses/presentation/pages/lesson_page.dart` | 208 |
| `flutter_app/lib/features/courses/presentation/providers/course_catalog_provider.dart` | 198 |
| `flutter_app/lib/features/courses/presentation/providers/course_filter_providers.dart` | 22 |
| `flutter_app/lib/features/courses/presentation/providers/course_provider.dart` | 153 |
| `flutter_app/lib/features/courses/presentation/providers/course_provider.g.dart` | 882 |
| `flutter_app/lib/features/courses/presentation/providers/video_playback_provider.dart` | 50 |
| `flutter_app/lib/features/courses/presentation/widgets/course_card.dart` | 326 |
| `flutter_app/lib/features/courses/presentation/widgets/next_lesson_card.dart` | 109 |
| `flutter_app/lib/features/dashboard/data/datasources/dashboard_remote_datasource.dart` | 70 |
| `flutter_app/lib/features/dashboard/data/models/dashboard_model.dart` | 177 |
| `flutter_app/lib/features/dashboard/data/models/dashboard_model.freezed.dart` | 1772 |
| `flutter_app/lib/features/dashboard/data/models/dashboard_model.g.dart` | 154 |
| `flutter_app/lib/features/dashboard/data/repositories/dashboard_repository_impl.dart` | 56 |
| `flutter_app/lib/features/dashboard/domain/entities/dashboard_data.dart` | 77 |
| `flutter_app/lib/features/dashboard/domain/entities/dashboard_data.freezed.dart` | 1553 |
| `flutter_app/lib/features/dashboard/domain/entities/monthly_revenue.dart` | 96 |
| `flutter_app/lib/features/dashboard/domain/repositories/dashboard_repository.dart` | 9 |
| `flutter_app/lib/features/dashboard/presentation/pages/continue_learning_page.dart` | 287 |
| `flutter_app/lib/features/dashboard/presentation/pages/dashboard_page.dart` | 1694 |
| `flutter_app/lib/features/dashboard/presentation/pages/student_report_page.dart` | 612 |
| `flutter_app/lib/features/dashboard/presentation/providers/dashboard_provider.dart` | 64 |
| `flutter_app/lib/features/dashboard/presentation/providers/dashboard_provider.g.dart` | 105 |
| `flutter_app/lib/features/dashboard/presentation/providers/monthly_revenue_provider.dart` | 52 |
| `flutter_app/lib/features/dashboard/presentation/widgets/admin_dashboard_view.dart` | 108 |
| `flutter_app/lib/features/dashboard/presentation/widgets/admin_monthly_revenue_section.dart` | 476 |
| `flutter_app/lib/features/dashboard/presentation/widgets/instructor_dashboard_view.dart` | 114 |
| `flutter_app/lib/features/dashboard/presentation/widgets/role_dashboard_common.dart` | 218 |
| `flutter_app/lib/features/home/presentation/pages/home_page.dart` | 1134 |
| `flutter_app/lib/features/home/presentation/pages/main_scaffold.dart` | 65 |
| `flutter_app/lib/features/home/presentation/providers/home_instructors_provider.dart` | 25 |
| `flutter_app/lib/features/home/presentation/widgets/instructor_card.dart` | 87 |
| `flutter_app/lib/features/home/presentation/widgets/stagger_testimonials_hero.dart` | 461 |
| `flutter_app/lib/features/internships/presentation/pages/internship_detail_page.dart` | 290 |
| `flutter_app/lib/features/internships/presentation/pages/internships_page.dart` | 161 |
| `flutter_app/lib/features/learning/learning_api.dart` | 49 |
| `flutter_app/lib/features/learning/learning_workspace.dart` | 635 |
| `flutter_app/lib/features/learning/recording_reader.dart` | 102 |
| `flutter_app/lib/features/live_classes/data/live_class_api.dart` | 139 |
| `flutter_app/lib/features/live_classes/data/live_class_repository.dart` | 116 |
| `flutter_app/lib/features/live_classes/data/models/live_class_model.dart` | 184 |
| `flutter_app/lib/features/live_classes/data/models/live_class_model.freezed.dart` | 1480 |
| `flutter_app/lib/features/live_classes/data/models/live_class_model.g.dart` | 125 |
| `flutter_app/lib/features/live_classes/domain/entities/live_class.dart` | 76 |
| `flutter_app/lib/features/live_classes/domain/entities/live_class.freezed.dart` | 1061 |
| `flutter_app/lib/features/live_classes/domain/repositories/live_class_repository.dart` | 38 |
| `flutter_app/lib/features/live_classes/presentation/join_live_class_screen.dart` | 295 |
| `flutter_app/lib/features/live_classes/presentation/live_class_detail_screen.dart` | 138 |
| `flutter_app/lib/features/live_classes/presentation/live_class_list_screen.dart` | 196 |
| `flutter_app/lib/features/live_classes/presentation/providers.dart` | 71 |
| `flutter_app/lib/features/live_classes/presentation/providers.g.dart` | 654 |
| `flutter_app/lib/features/profile/data/datasources/profile_remote_datasource.dart` | 119 |
| `flutter_app/lib/features/profile/data/repositories/profile_repository_impl.dart` | 54 |
| `flutter_app/lib/features/profile/domain/repositories/profile_repository.dart` | 9 |
| `flutter_app/lib/features/profile/presentation/pages/profile_page.dart` | 1810 |
| `flutter_app/lib/features/profile/presentation/pages/public_profile_page.dart` | 495 |
| `flutter_app/lib/features/profile/presentation/pages/settings_page.dart` | 446 |
| `flutter_app/lib/features/profile/presentation/providers/profile_provider.dart` | 26 |
| `flutter_app/lib/features/quizzes/data/datasources/quiz_remote_datasource.dart` | 110 |
| `flutter_app/lib/features/quizzes/data/models/quiz_model.dart` | 87 |
| `flutter_app/lib/features/quizzes/data/models/quiz_model.freezed.dart` | 931 |
| `flutter_app/lib/features/quizzes/data/models/quiz_model.g.dart` | 86 |
| `flutter_app/lib/features/quizzes/data/repositories/quiz_repository_impl.dart` | 84 |
| `flutter_app/lib/features/quizzes/domain/entities/quiz.dart` | 53 |
| `flutter_app/lib/features/quizzes/domain/entities/quiz.freezed.dart` | 1017 |
| `flutter_app/lib/features/quizzes/domain/repositories/quiz_repository.dart` | 23 |
| `flutter_app/lib/features/quizzes/domain/usecases/quiz_usecases.dart` | 43 |
| `flutter_app/lib/features/quizzes/presentation/pages/quiz_taking_page.dart` | 289 |
| `flutter_app/lib/features/quizzes/presentation/providers/quiz_provider.dart` | 51 |
| `flutter_app/lib/features/quizzes/presentation/providers/quiz_provider.g.dart` | 267 |
| `flutter_app/lib/features/wishlist/presentation/pages/wishlist_page.dart` | 80 |
| `flutter_app/lib/main.dart` | 123 |
| `flutter_app/lib/shared/widgets/common/app_button.dart` | 234 |
| `flutter_app/lib/shared/widgets/common/app_card.dart` | 78 |
| `flutter_app/lib/shared/widgets/common/app_input.dart` | 153 |
| `flutter_app/lib/shared/widgets/common/app_loader.dart` | 162 |
| `flutter_app/lib/shared/widgets/common/app_snackbar.dart` | 75 |
| `flutter_app/lib/shared/widgets/common/error_display.dart` | 102 |
| `flutter_app/lib/shared/widgets/common/gradient_header.dart` | 80 |
| `flutter_app/lib/shared/widgets/common/launching_soon.dart` | 48 |
| `flutter_app/lib/shared/widgets/common/safe_model_viewer.dart` | 93 |
| `flutter_app/lib/shared/widgets/common/section_header.dart` | 79 |
| `flutter_app/lib/shared/widgets/common/skeleton_loader.dart` | 147 |
| `flutter_app/lib/shared/widgets/common/user_menu.dart` | 506 |
| `flutter_app/lib/shared/widgets/common/warm_glow_background.dart` | 54 |
| `flutter_app/lib/shared/widgets/video/bunny_video_player_widget.dart` | 194 |
| `flutter_app/lib/shared/widgets/video/video_player_widget.dart` | 508 |
| `streaming-service/video_streaming.py` | 279 |
| `nginx/cache.conf` | 5 |
| `nginx/conf.d/aapanel.conf` | 23 |
| `nginx/conf.d/default.conf` | 502 |
| `nginx/conf.d/default.production.conf` | 202 |
| `nginx/conf.d/map_crawler.conf` | 18 |
| `nginx/conf.d.local/default.conf` | 135 |
| `nginx/nginx-entrypoint.sh` | 9 |
| `nginx/nginx.conf` | 53 |
| `scripts/apply_integrated_migration.py` | 20 |
| `scripts/backup-db.sh` | 56 |
| `scripts/build_architecture_inventory.py` | 51 |
| `scripts/check_local_release.py` | 31 |
| `scripts/ids_watch.py` | 412 |
| `scripts/purge-cloudflare-cache.sh` | 34 |
| `scripts/render_architecture_pdf.py` | 123 |
| `scripts/setup.sh` | 82 |
| `scripts/smoke.sh` | 56 |
| `scripts/start-recording-worker.ps1` | 12 |
