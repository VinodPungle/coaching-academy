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

## Architecture
- /app/backend: server.py (app + startup indexes/seed), database.py, auth_utils.py, seed.py, routers/{auth,courses,tests,live_classes,assignments,announcements,dashboard,payments,batches,files}.py, tests/{backend_test.py,test_new_features.py}, uploads/ (file storage)
- /app/frontend/src: App.js (routes), lib/api.js (uploadFile/fileUrl helpers), context/AuthContext.jsx, components/{PortalLayout,EnrollModal}.jsx, pages/{Landing,AuthPage,Dashboard,Courses,CourseDetail,LiveClasses,Tests,TakeTest,TestBuilder,TestResults,Assignments,Announcements}.jsx

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

## Backlog / Roadmap
- P0: Real Stripe/Razorpay gateway integration once user provides keys (wire into payments.py confirm + webhooks; UI already built)
- P1: Certificates on course completion, test question review after attempt, teacher analytics charts (recharts)
- P2: Student leaderboards, email notifications, forgot-password flow, batch-scoped live classes/announcements
- P3 (SaaS): multi-tenant academies (white-label), admin panel, live class recordings, Zoom integration, mobile PWA

## Notes
- Credentials in /app/memory/test_credentials.md; auth test guide in /app/auth_testing.md
