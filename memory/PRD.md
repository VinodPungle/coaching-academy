# PRD — JAM Academy LMS (Edmingle-style, IIT-JAM coaching)

## Original Problem Statement
Create a website with Edmingle LMS features for an educational academy providing IIT-JAM coaching, with potential to scale into a SaaS platform. Teacher and Student portals with Edmingle-like features. User approved defaults (MongoDB, JWT auth, agent-chosen design).

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

## Architecture
- /app/backend: server.py (app + startup indexes/seed), database.py, auth_utils.py, seed.py, notify.py (Resend email + in-app notify), routers/{auth,courses,tests,live_classes,assignments,announcements,dashboard,payments,batches,files,certificates,notifications}.py, tests/{backend_test.py,test_new_features.py,test_iteration3.py}, uploads/ (file storage)
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
- P2: Batch-scoped announcements, notification pagination, background email queue (notify() uses fire-and-forget create_task)
- P3 (SaaS): multi-tenant academies (white-label), admin panel, live class recordings, Zoom integration, mobile PWA

## Notes
- Credentials in /app/memory/test_credentials.md; auth test guide in /app/auth_testing.md
