# PRD — Rohini's Academy LMS (Edmingle-style, entrance-exam coaching)

## Original Problem Statement
Create a website with Edmingle LMS features for an educational academy providing entrance-exam coaching (originally focused on IIT-JAM, now generalised to all entrance exams), with potential to scale into a SaaS platform. Teacher and Student portals with Edmingle-like features. User approved defaults (MongoDB, JWT auth, agent-chosen design).

## Tech Stack
- React 19 + Tailwind + shadcn (frontend), FastAPI + Motor/MongoDB (backend)
- JWT Bearer auth (localStorage `jam_token` + httpOnly cookie fallback), bcrypt hashing
- Design: Swiss high-contrast light theme, Klein Blue #1D4ED8 / Signal Red accent, Cabinet Grotesk + IBM Plex Sans, sharp corners (/app/design_guidelines.json)

## Implemented (June 2026)
### Phase 1 — MVP (tested 100%, iteration_1.json: 26/26 backend, 18/18 e2e)
- Auth: register (student/teacher role toggle), login, logout, /me; seeded demo accounts
- Landing page (marketing, hero, features bento, CTA) at /
- Student portal (/app/*): dashboard (stats, upcoming classes, announcements), course catalog + enroll, My Courses with progress, course detail with sections/lessons + mark-complete, live class schedule with join links, timed mock tests with auto-grading + scorecard (one attempt), assignment submission + view grade/feedback, announcements
- Teacher portal (same routes, role-aware): dashboard stats, create/manage courses (sections, lessons, enrolled students table), schedule/delete live classes, test builder (MCQ, correct-answer radio, marks) + results leaderboard, create assignments + grade submissions with feedback, post/delete announcements
- Seed data: 4 IIT-JAM courses, 2 mock tests (5 Q each), 3 live classes, 2 assignments, 3 announcements
- Role enforcement on all APIs; correct answers hidden from students; unique indexes on enrollments and test_attempts

### Phase 2 — Payments UI, Batches, File Uploads, Course-linking (tested, iteration_2.json: 42/42 backend, all UI flows)
- Payment checkout for paid enrollment: EnrollModal with batch picker, Stripe/Razorpay method toggle, order total. DEMO MODE (keys empty in backend/.env: STRIPE_API_KEY, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET — placeholders awaiting user's keys; confirm endpoint returns 501 once real keys set, pending gateway verification implementation). Payments stored in db.payments; GET /api/student/payments history.
- Batches/cohorts: teacher creates batches per course (name, start date, schedule, capacity) on course detail page; students pick batch at enrollment (capacity enforced, "batch full" 400); my_batch shown on course detail; batch student roster API. 2 batches seeded per course.
- Real file uploads: POST /api/files/upload (25MB max, ext whitelist, chunked write to /app/backend/uploads, metadata in db.files), GET /api/files/{id} serves. Teacher uploads lesson notes (auto-fills lesson URL, type=pdf); students attach files to assignment submissions; teacher sees download link in submissions view.
- Course-linked tests & assignments: optional course selector in TestBuilder and assignment form; students only see items that are unlinked or belong to enrolled courses; course badge shown on cards.

### Phase 3 — Certificates, Test Review, Teacher Analytics (self-tested e2e via curl + UI screenshots)
- Certificates: GET /api/courses/{id}/certificate issues cert (unique cert_no) only at 100% lesson completion (400 with progress otherwise); GET /api/student/certificates. Printable certificate page at /certificate/:courseId (print CSS, window.print for PDF); "Certificate" buttons appear on My Courses card + course detail at 100%.
- Test answer review: GET /api/tests/{id}/review (student, requires attempt) returns questions with correct_index + student answers. /app/tests/:id/review page shows verdict per question (+marks/0/Skipped), correct answer green, wrong choice red. Linked from scorecard and attempted test cards.
- Teacher analytics: GET /api/dashboard/teacher/analytics (enrollments per course, test avg%/attempts, assignment graded vs pending). Recharts bar charts rendered on teacher dashboard (components/TeacherAnalytics.jsx).

### Phase 4 — Leaderboards, Email Notifications, Forgot-Password, Batch-Scoped Classes (tested 100%, iteration_3.json: 59/59 backend, all UI flows)
- Leaderboards: GET /api/tests/{id}/leaderboard (rank by score desc/time asc, my_rank + my_percentile). /app/tests/:id/leaderboard page with podium top-3, ranked table (own row highlighted). Links from attempted test cards + scorecard.
- Email + in-app notifications: Resend integrated (notify.py: send_email + email_template + notify()). RESEND API KEY set in backend/.env — ACCOUNT IN TESTING MODE: delivers only to account owner (vinod.pungle@gmail.com) until domain verified at resend.com/domains; failures caught + logged gracefully. In-app: db.notifications, GET /api/notifications + read-all, NotificationsBell (unread badge, panel, 30s poll) in portal. Triggers: enrollment (student email + teacher in-app), payment success, assignment graded (email), announcement posted, live class scheduled (scoped).
- Forgot-password: POST /api/auth/forgot-password (token in password_reset_tokens, TTL 1h, reset link emailed + logged), POST /api/auth/reset-password (single-use, expiry checked). Pages /forgot-password + /reset-password?token=; link on login form.
- Batch-scoped live classes: live_classes optional course_id/batch_id (names resolved); teacher form has course + batch selects; student visibility filter (global OR enrolled course + matching/global batch) applied to /api/live-classes AND student dashboard upcoming; scope badges in UI; scoped students notified on scheduling.

### Phase 5 — Configurable Branding + Deployment Readiness (June 2026)
- Academy name renamed to "Rohini's JAM Academy", fully configurable: frontend via REACT_APP_ACADEMY_NAME (frontend/.env) → src/lib/config.js ACADEMY_NAME constant (used in Landing, AuthPage, PortalLayout, Certificate, ForgotPassword, ResetPassword); backend via ACADEMY_NAME (backend/.env) → notify.py constant (email templates, reset email, welcome email, FastAPI title). index.html title updated.
- All N+1 query patterns eliminated (aggregation $group + batched $in): courses.py (teacher_courses, my_enrollments, course_students), dashboard.py (teacher_analytics), tests.py (list_tests), assignments.py (list_assignments both roles).
- Deployment agent: ✅ PASS — no blockers, ready to deploy to Emergent.

### Phase 6 — Admin Panel + Zoom Integration (June 2026)
- Admin panel: seeded admin (admin@jamacademy.com / Admin@123 from ADMIN_EMAIL/ADMIN_PASSWORD env). Endpoints (all require_role admin): GET /api/admin/stats (platform totals + revenue + recent signups), GET /api/admin/users?q=&role= (search/filter), PUT /api/admin/users/{id}/role, DELETE /api/admin/users/{id} (full cascade incl. teacher content; self-protected), GET /api/admin/payments (+total_revenue). UI: role-aware nav (admin sees Dashboard/Users/Payments/Announcements), AdminDashboard component (stat cards + recent signups), /app/users (search, role filter, inline role change, confirm delete), /app/payments (table + revenue widget).
- Zoom integration (Server-to-Server OAuth per playbook): backend/zoom_service.py (token caching 59min, create_zoom_meeting → join_url), GET /api/zoom/config {configured}, live class create accepts create_zoom flag → auto-fills meeting_link with Zoom join_url. UI checkbox "Auto-create Zoom meeting" in schedule form (disabled with notice until creds set). PLACEHOLDERS in backend/.env: ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET — AWAITING USER CREDENTIALS (from marketplace.zoom.us → Build App → Server-to-Server OAuth, scope meeting:write:admin). Manual meeting links still work.

### Phase 7 — Documentation (June 2026)
- Three downloadable, printable HTML docs served from frontend/public/docs/ (linked in landing footer): /docs/user-manual.html (student/teacher/admin operations + FAQ), /docs/design-architecture.html (stack, design system, data model, API surface, key flows, integrations), /docs/developer-guide.html (repo structure, env vars, conventions, integration activation steps, how-tos). Each has a Print/Save-as-PDF button.
- Confirmed to user: recorded video lectures = lessons of type "video" (teacher adds URL), students view + mark complete, progress % tracked per student, teacher sees per-student completion, certificate at 100%.

### Phase 8 — In-App Video Player (June 2026)
- components/VideoPlayerModal.jsx: react-player@2.16.0 lightbox (16:9, dark overlay, autoplay, controls) — supports YouTube/Vimeo/direct files. Video lessons in CourseDetail open the player in-app (PDFs still open in new tab).
- Auto-mark-complete: onProgress played>=0.9 or onEnded → POST lessons/{id}/complete (once, enrolled students only); manual "Mark complete" button in player header; teacher/non-enrolled see preview mode note. Verified via screenshot (player renders, completion state works).

### Phase 9 — WhatsApp Notifications (June 2026, PLACEHOLDER MODE)
- Twilio WhatsApp wired in notify.py: send_whatsapp() (E.164 check, to_thread, errors logged); notify() sends in-app + email + WhatsApp (to users with `phone`) for ALL events (enrollment, payment, grading, announcements, live classes). DEMO MODE until user provides TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN in backend/.env (TWILIO_WHATSAPP_FROM preset to sandbox whatsapp:+14155238886); demo sends are logged "[WHATSAPP demo mode]".
- Phone collection: registration form has optional "WhatsApp number" field (register-phone-input); PUT /api/auth/profile {phone} validates +countrycode; NotificationsBell panel footer has "Get these on WhatsApp" input + save (whatsapp-phone-input/save). Verified via curl + UI screenshot.
- Also: emails now send as "Rohini's JAM Academy <SENDER_EMAIL>" with REPLY_TO_EMAIL=patilrohini194@gmail.com (backend/.env). PRODUCTION deployed at https://educoach-platform.emergent.host (changes need redeploy to reach production).

## Architecture
- /app/backend: server.py (app + startup indexes/seed), database.py, auth_utils.py, seed.py, notify.py (Resend email + in-app notify), zoom_service.py, routers/{auth,courses,tests,live_classes,assignments,announcements,dashboard,payments,batches,files,certificates,notifications,admin}.py, tests/{backend_test.py,test_new_features.py,test_iteration3.py}, uploads/ (file storage)
- /app/frontend/src: App.js (routes incl /certificate/:courseId, /app/tests/:id/{review,leaderboard}, /forgot-password, /reset-password), lib/api.js (uploadFile/fileUrl helpers), context/AuthContext.jsx, components/{PortalLayout,EnrollModal,TeacherAnalytics,NotificationsBell}.jsx, pages/{Landing,AuthPage,ForgotPassword,ResetPassword,Dashboard,Courses,CourseDetail,LiveClasses,Tests,TakeTest,TestBuilder,TestResults,TestReview,Leaderboard,Certificate,Assignments,Announcements}.jsx

## Key API Endpoints (all /api)
- /auth/{register,login,logout,me}
- /courses (CRUD), /courses/{id}/{enroll,sections,students}, /courses/{id}/sections/{sid}/lessons, /courses/{id}/lessons/{lid}/complete, /teacher/courses, /student/enrollments
- /tests (CRUD), /tests/{id}/attempt, /tests/{id}/attempts, /student/attempts
- /live-classes (GET/POST/DELETE)
- /assignments (GET/POST/DELETE), /assignments/{id}/{submit,submissions}, /submissions/{id}/grade
- /announcements (GET/POST/DELETE)
- /dashboard/{student,teacher}
- /payments/{config,checkout}, /payments/{id}/confirm, /student/payments
- /courses/{id}/batches (GET/POST), /batches/{id} (DELETE), /batches/{id}/students
- /files/upload (POST multipart), /files/{id} (GET)
- /courses/{id}/certificate, /student/certificates, /tests/{id}/review, /dashboard/teacher/analytics
- /tests/{id}/leaderboard, /notifications (GET + read-all), /auth/{forgot-password,reset-password}

## Backlog / Roadmap
- P0: Real Stripe/Razorpay gateway integration once user provides keys (wire into payments.py confirm + webhooks; UI already built)
- P0: Resend domain verification (user must verify domain at resend.com/domains, then change SENDER_EMAIL) so emails deliver to all users
- P1: Automatic WhatsApp reminders 30 min before live classes (scheduler)
- P2: Batch-scoped announcements, notification pagination, background email queue
- P2: Move local uploads to S3/Blob for horizontal scaling
- P3 (SaaS): multi-tenant academies (white-label), mobile PWA

## Iteration 5 — Feb 12, 2026 (Phased overhaul: hierarchy, playback, comments, live-class attendance, retakes, UPI, portal mode, enrolment mgmt, free courses)

Delivered in 11 phases with test coverage between each phase (41 backend tests + 15 frontend unit tests, all passing).

### Phase 1 — Content hierarchy (Course → Section → Sub Topic → Lesson)
- Startup migration wraps existing lessons under a default "Overview" sub-topic (idempotent).
- New endpoints: POST/PUT/DELETE `/courses/{cid}/sections/{sid}/sub-topics`, reorder, comments-toggle.
- Duplicate sub-topic names rejected; delete blocked when lessons exist.

### Phase 2 — Lesson content & playback
- Lessons hold `url` (video) + `notes[]` (PDFs) — either/both allowed.
- Google Drive share links auto-converted to `/preview` embed URL; YouTube via react-player.
- Clear inline error for invalid/restricted Drive links.
- `src/lib/video.js` + `src/components/LessonVideoPlayer.jsx`.

### Phase 3 — Lesson detail page (`/app/courses/:cid/lessons/:lid`)
- Back link, Prev/Next navigation across sub-topics & sections.
- `GET /courses/{cid}/lessons/{lid}` returns section/sub-topic context + prev/next ids.
- Enrolled student check enforced.

### Phase 4 — Reusable threaded Comments (YouTube-style)
- `CommentsThread` component mounted on Lesson page (per lesson) and Recording page (per class).
- Teacher can enable/disable per sub-topic and per recording; disabled state hides input.
- Teacher/admin can moderate any comment; students only their own. Delete cascades to replies.

### Phase 5 — Live Classes upgrade
- Reschedule (past times rejected); attach/replace/remove recording URL.
- Student "Join Class" click marks attendance (idempotent). Teacher sees `/app/live/:id/attendance`.
- Past class with recording swaps button to "View Recording" → `/app/live/:id/recording` page (reuses LessonVideoPlayer + CommentsThread).

### Phase 6 — Retakes toggle on tests
- New `retakes_allowed` flag on tests. When true, students can reattempt; latest score replaces old (single-attempt-per-student invariant preserved).
- Teacher can flip mid-course via edit page.

### Phase 7 — Payments overhaul (Stripe removed, UPI + admin manual)
- Stripe integration ripped out. New settings collection stores portal_mode + upi_qr_url (image) + upi_vpa (text).
- Course-level `is_free` flag; teacher chooses Free/Paid at create/edit.
- Paid courses in live mode display UPI QR (image) or VPA (text) with "Notify admin" CTA.
- Admin can record payments (any amount ≤ outstanding), edit or delete them, and grant course access at their discretion — even for partial payments.
- Dues endpoint: student sees paid/outstanding; admin sees payment history per student per course.

### Phase 8 — Portal Mode
- Admin can toggle Demo/Live. Demo lets students enrol in any course for free (fee waived).

### Phase 9 — Enrolment management
- Teacher can move a student between batches or switch to self-paced (`PUT /courses/{cid}/students/{sid}/batch`).
- Full-batch guard on transfer.

### Phase 10 — Free courses on student dashboard
- New "Free courses" section on student dashboard with one-click enrol (skips modal).
- Enrolled courses filtered out; hides when list is empty.

### Phase 11 — Polish (cross-cutting)
- **"Developed by VinodPungle.com"** replaces the Emergent badge in `public/index.html`.
- Phone column in Admin Users table + Admin Teachers list (WhatsApp deep-link).
- Admin one-click cleanup for TEST_* users (26 stale accounts removed this session).
- Validation messages standardised across new endpoints (empty title, invalid URL/duration/amount, duplicate names, past scheduling).

### Warmup (from previous message)
- Phone visible to admin ✅
- Cleanup script + button ✅

**Test files added:**
- `/app/backend/tests/test_phase1_subtopics.py`
- `/app/backend/tests/test_phase3_lesson_page.py`
- `/app/backend/tests/test_phase4_comments.py`
- `/app/backend/tests/test_phase5_live_classes.py`
- `/app/backend/tests/test_phase6_retakes.py`
- `/app/backend/tests/test_phase7_payments.py`
- `/app/backend/tests/test_phase9_10_enrollment.py`
- `/app/frontend/src/lib/video.test.js`
- `/app/test_reports/all_phases_summary.json`
- Rebranded "Rohini's JAM Academy" → "Rohini's Academy" (frontend + backend .env, config.js, notify.py, seed.py, index.html title, footer). App is now presented as generic entrance-exam coaching (no IIT-JAM branding on hero, subjects list expanded).
- Landing page copy updated: hero H1, sub-heading, footer tag, subjects list, subhead moved to entrance-exam framing.
- Favicon: /public/favicon.svg (GraduationCap) added and referenced in index.html.
- User email migration: startup migration @jamacademy.com → @rgpacademy.com (passwords preserved). Handles empty-duplicate cleanup safely.
- Access-control tightening:
  - Teacher scope preserved on tests/live-classes/assignments/courses; announcements now filtered to own + admin-posted.
  - Student announcements filtered to enrolled courses + global.
  - Delete-test guard: 400 with clear message when attempts exist.
  - Delete announcement + delete live class: teacher can delete only own; admin can delete any.
- Test edit (Modify) flow: /app/tests/:id/edit reuses TestBuilder in edit mode. PUT /api/tests/{id} already existed on backend.
- Course cross-links: CourseDetail now shows 3 cards (Live Classes / Tests / Assignments) filtered to the course.
- 'For all students' badges on Tests, Assignments, Live Classes, Announcements when unlinked.
- Admin per-teacher breakdown: GET /api/admin/teachers, GET /api/admin/teachers/{id}/detail; new /app/teachers page.
- Admin top performers: GET /api/admin/top-performers (per_course + per_batch); new /app/top-performers page.
- Admin nav: added "Teachers" and "Top Performers" links.

## Notes
- Credentials in /app/memory/test_credentials.md; all seeded users now use @rgpacademy.com.
