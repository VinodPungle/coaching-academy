# PRD — JAM Academy LMS (Edmingle-style, IIT-JAM coaching)

## Original Problem Statement
Create a website with Edmingle LMS features for an educational academy providing IIT-JAM coaching, with potential to scale into a SaaS platform. Teacher and Student portals with Edmingle-like features. User approved defaults (MongoDB, JWT auth, agent-chosen design).

## Tech Stack
- React 19 + Tailwind + shadcn (frontend), FastAPI + Motor/MongoDB (backend)
- JWT Bearer auth (localStorage `jam_token` + httpOnly cookie fallback), bcrypt hashing
- Design: Swiss high-contrast light theme, Klein Blue #1D4ED8 / Signal Red accent, Cabinet Grotesk + IBM Plex Sans, sharp corners (/app/design_guidelines.json)

## Implemented (June 2026) — MVP COMPLETE, tested 100% (iteration_1.json: 26/26 backend, 18/18 e2e)
- Auth: register (student/teacher role toggle), login, logout, /me; seeded demo accounts
- Landing page (marketing, hero, features bento, CTA) at /
- Student portal (/app/*): dashboard (stats, upcoming classes, announcements), course catalog + enroll, My Courses with progress, course detail with sections/lessons + mark-complete, live class schedule with join links, timed mock tests with auto-grading + scorecard (one attempt), assignment submission + view grade/feedback, announcements
- Teacher portal (same routes, role-aware): dashboard stats, create/manage courses (sections, lessons, enrolled students table), schedule/delete live classes, test builder (MCQ, correct-answer radio, marks) + results leaderboard, create assignments + grade submissions with feedback, post/delete announcements
- Seed data: 4 IIT-JAM courses, 2 mock tests (5 Q each), 3 live classes, 2 assignments, 3 announcements
- Role enforcement on all APIs; correct answers hidden from students; unique indexes on enrollments and test_attempts

## Architecture
- /app/backend: server.py (app + startup indexes/seed), database.py, auth_utils.py, seed.py, routers/{auth,courses,tests,live_classes,assignments,announcements,dashboard}.py, tests/backend_test.py
- /app/frontend/src: App.js (routes), lib/api.js, context/AuthContext.jsx, components/PortalLayout.jsx, pages/{Landing,AuthPage,Dashboard,Courses,CourseDetail,LiveClasses,Tests,TakeTest,TestBuilder,TestResults,Assignments,Announcements}.jsx

## Key API Endpoints (all /api)
- /auth/{register,login,logout,me}
- /courses (CRUD), /courses/{id}/{enroll,sections,students}, /courses/{id}/sections/{sid}/lessons, /courses/{id}/lessons/{lid}/complete, /teacher/courses, /student/enrollments
- /tests (CRUD), /tests/{id}/attempt, /tests/{id}/attempts, /student/attempts
- /live-classes (GET/POST/DELETE)
- /assignments (GET/POST/DELETE), /assignments/{id}/{submit,submissions}, /submissions/{id}/grade
- /announcements (GET/POST/DELETE)
- /dashboard/{student,teacher}

## Backlog / Roadmap
- P1: Payments for course enrollment (Stripe/Razorpay), batches/cohorts model, real file uploads for notes & assignment submissions (object storage), certificates on course completion
- P2: Course-linked tests & assignments (currently global), test question review after attempt, teacher analytics charts (recharts), student leaderboards, email notifications, forgot-password flow
- P3 (SaaS): multi-tenant academies (white-label), admin panel, live class recordings, Zoom integration, mobile PWA

## Notes
- Credentials in /app/memory/test_credentials.md; auth test guide in /app/auth_testing.md
