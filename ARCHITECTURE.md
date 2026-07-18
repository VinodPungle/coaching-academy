# Architecture Document — Coaching Academy Learning Platform

> **Who this is for:** Students with **zero prior experience** in web development, cloud computing, or software architecture. Every term is explained the first time it appears. If you already know what a "REST API" or "Docker container" is, feel free to skim — but nothing is assumed.

---

## Table of Contents

1. [What Is This Solution?](#1-what-is-this-solution)
2. [The Big Picture — System Architecture Diagram](#2-the-big-picture--system-architecture-diagram)
3. [The Three Worlds: Local, Cloud, and CI/CD](#3-the-three-worlds-local-cloud-and-cicd)
4. [Component Catalog](#4-component-catalog)
   - [4.1 Frontend — The React Web App](#41-frontend--the-react-web-app)
   - [4.2 Backend — The FastAPI Server](#42-backend--the-fastapi-server)
   - [4.3 Database — MongoDB](#43-database--mongodb)
   - [4.4 File Storage — Azure Blob Storage](#44-file-storage--azure-blob-storage)
   - [4.5 Third-Party Services](#45-third-party-services)
   - [4.6 Infrastructure — Docker, Azure Container Apps, Azure Static Web Apps](#46-infrastructure--docker-azure-container-apps-azure-static-web-apps)
   - [4.7 CI/CD — GitHub Actions](#47-cicd--github-actions)
5. [Technology Glossary](#5-technology-glossary)
6. [Request & Data Flow Walkthroughs](#6-request--data-flow-walkthroughs)
   - [6.1 Login Flow](#61-login-flow)
   - [6.2 Browsing Courses (Public Data Flow)](#62-browsing-courses-public-data-flow)
   - [6.3 Enrolling & Paying for a Course](#63-enrolling--paying-for-a-course)
   - [6.4 Uploading a File (Video, PDF, Image)](#64-uploading-a-file-video-pdf-image)
   - [6.5 Scheduling a Live Class (Zoom Integration)](#65-scheduling-a-live-class-zoom-integration)
   - [6.6 Deploying a Code Change (CI/CD Flow)](#66-deploying-a-code-change-cicd-flow)
7. [Folder-by-Folder Reference Map](#7-folder-by-folder-reference-map)
8. [Security Model](#8-security-model)
9. [Database Collections Reference](#9-database-collections-reference)

---

## 1. What Is This Solution?

This repository is a **web-based coaching/exam-preparation platform** — think of it like a mini version of Udemy or BYJU'S, built for a specific coaching academy that prepares students for the IIT-JAM exam (a postgraduate entrance exam in India).

The platform lets:
- **Students** browse courses, watch video lessons, take timed tests, submit assignments, attend live classes, and pay for course enrollment.
- **Teachers** create courses, upload lessons, build tests, schedule live classes, and grade assignments.
- **Admins** manage users, review payments, configure site settings, and oversee everything.

Like almost every modern web application, it is split into two independently-running programs that talk to each other over the internet using a well-defined language (an **API**, explained in [Section 5](#5-technology-glossary)):

| Part | What it does | Built with |
|---|---|---|
| **Frontend** | Everything you *see* and *click* in your browser | React (JavaScript) |
| **Backend** | The "brain" that stores data, checks passwords, processes payments | FastAPI (Python) |
| **Database** | Where all the data (courses, users, test scores) permanently lives | MongoDB |

These three pieces are hosted separately in the cloud (on Microsoft Azure), and a fourth piece — **GitHub Actions** — automatically ships new code to the cloud every time a developer pushes a change. We'll explain every one of these words below.

---

## 2. The Big Picture — System Architecture Diagram

```mermaid
graph TB
    subgraph "User's Device"
        Browser["🌐 Web Browser<br/>(Chrome, Edge, etc.)"]
    end

    subgraph "Azure Cloud — Frontend Hosting"
        SWA["Azure Static Web App<br/>(serves the React app's<br/>HTML/CSS/JS files)"]
    end

    subgraph "Azure Cloud — Backend Hosting"
        CA["Azure Container App<br/>(runs the FastAPI server<br/>inside a Docker container)"]
    end

    subgraph "Azure Cloud — File Storage"
        Blob["Azure Blob Storage<br/>(stores uploaded PDFs,<br/>videos, images)"]
    end

    subgraph "MongoDB Atlas (Managed Database, hosted on Azure infrastructure)"
        Mongo[("MongoDB Database<br/>courses, users, tests,<br/>payments, etc.")]
    end

    subgraph "Third-Party Services"
        Razorpay["💳 Razorpay<br/>(payment processing)"]
        Resend["📧 Resend<br/>(sends emails)"]
        Twilio["💬 Twilio<br/>(sends WhatsApp messages)"]
        Zoom["📹 Zoom API<br/>(creates video meetings)"]
    end

    subgraph "Developer's Machine + GitHub"
        Dev["👩‍💻 Developer writes code"]
        GH["GitHub Repository<br/>(source code storage)"]
        GHA["GitHub Actions<br/>(automated deployment robot)"]
    end

    Browser <-->|"HTTPS<br/>(loads the web page)"| SWA
    Browser <-->|"HTTPS + JSON<br/>(REST API calls)"| CA
    CA <-->|"Encrypted DB connection"| Mongo
    CA <-->|"Upload/download files"| Blob
    CA -->|"Create payment order"| Razorpay
    Browser -->|"Complete checkout"| Razorpay
    CA -->|"Send email"| Resend
    CA -->|"Send WhatsApp msg"| Twilio
    CA -->|"Create meeting link"| Zoom

    Dev -->|"git push"| GH
    GH -->|"triggers on push"| GHA
    GHA -->|"builds Docker image,<br/>deploys backend"| CA
    GHA -->|"builds React app,<br/>deploys frontend"| SWA

    style Browser fill:#e1f5ff
    style SWA fill:#cce5ff
    style CA fill:#cce5ff
    style Blob fill:#cce5ff
    style Mongo fill:#d4f7dc
    style GHA fill:#fff3cd
```

**Reading this diagram:** Everything in blue boxes runs on **Azure** (Microsoft's cloud platform). The green box (MongoDB) is a separate managed database service. The yellow box (GitHub Actions) is the automation that pushes code from a developer's laptop into the cloud. The browser is the only thing running on the *user's* computer — nothing else needs to be installed to use the app.

---

## 3. The Three Worlds: Local, Cloud, and CI/CD

Understanding this project means understanding it runs in **three different contexts**, each with a different purpose:

```mermaid
graph LR
    subgraph "1. LOCAL (your laptop)"
        L1["Docker: MongoDB<br/>on localhost:27017"]
        L2["Python: FastAPI backend<br/>on localhost:8001"]
        L3["Node: React frontend<br/>on localhost:3001"]
        L3-->L2-->L1
    end
    subgraph "2. CLOUD (production, always on)"
        C1["Azure Static Web App<br/>(real domain)"]
        C2["Azure Container App<br/>(real domain)"]
        C3["MongoDB Atlas<br/>(managed cloud DB)"]
        C1-->C2-->C3
    end
    subgraph "3. CI/CD (the bridge)"
        P1["GitHub Actions workflow"]
    end
    L3 -.->|"git push"| P1
    P1 -->|"auto-deploys"| C1
    P1 -->|"auto-deploys"| C2
```

| World | Purpose | Where it lives | Who "runs" it |
|---|---|---|---|
| **Local** | Writing and testing code before anyone else sees it | Your own laptop | You, manually, via terminal commands |
| **Cloud (Production)** | The real, live app that real users visit | Microsoft Azure data centers | Runs 24/7 automatically, no human touches it |
| **CI/CD** | The automated "delivery truck" that moves code from your laptop (via GitHub) into the cloud | GitHub's servers | Triggers automatically on `git push` |

This project is deliberately built so that **the exact same source code** runs in all three worlds — the only things that differ are *configuration* (see [Environment Variables](#environment-variables) in the glossary), never the application logic itself.

---

## 4. Component Catalog

### 4.1 Frontend — The React Web App

**What it is:** A **Single-Page Application (SPA)** — a website that loads once and then updates itself dynamically without full page reloads, similar to how Gmail or Twitter feels "app-like" in a browser.

**Location in repo:** [`frontend/`](frontend/)

**Technology:** [React](https://react.dev) (a JavaScript library for building user interfaces), bootstrapped with **Create React App** and customized using **CRACO** (Create React App Configuration Override — lets you tweak CRA's build settings without "ejecting" it).

**Key files:**

| File | Role |
|---|---|
| [`frontend/src/App.js`](frontend/src/App.js) | The **router** — defines every URL path in the app (`/`, `/app/dashboard`, `/app/courses`, etc.) and which page component renders for each |
| [`frontend/src/context/AuthContext.jsx`](frontend/src/context/AuthContext.jsx) | Manages "who is logged in" globally across the whole app, using React's **Context API** |
| [`frontend/src/context/SiteConfigContext.jsx`](frontend/src/context/SiteConfigContext.jsx) | Manages site-wide branding settings (academy name, logo, etc.) fetched from the backend |
| [`frontend/src/lib/api.js`](frontend/src/lib/api.js) | A single configured **Axios** instance used by the whole app to talk to the backend — automatically attaches the login token to every request |
| [`frontend/src/pages/`](frontend/src/pages/) | 28 "page" components — one per screen (Dashboard, Courses, TakeTest, AdminUsers, etc.) |
| [`frontend/src/components/`](frontend/src/components/) | Reusable UI pieces shared across pages (e.g. `PortalLayout.jsx` — the sidebar navigation shell) |
| [`frontend/src/components/ui/`](frontend/src/components/ui/) | 46 small, generic UI building blocks (buttons, dialogs, dropdowns) built on **Radix UI** primitives and styled with **Tailwind CSS** |
| [`frontend/craco.config.js`](frontend/craco.config.js) | Build configuration — sets up path aliases (`@/` → `src/`) and other webpack tweaks |
| [`frontend/package.json`](frontend/package.json) | Lists every JavaScript library the frontend depends on, and defines the `start`/`build` commands |

**How it interacts with other components:** The frontend never talks to the database directly. It only ever makes HTTP requests (see glossary) to the backend's REST API, receives JSON data back, and renders it as HTML.

---

### 4.2 Backend — The FastAPI Server

**What it is:** A **REST API server** — a program that listens for HTTP requests over the network and responds with data (as JSON), rather than rendering web pages itself.

**Location in repo:** [`backend/`](backend/)

**Technology:** [FastAPI](https://fastapi.tiangolo.com) (a modern Python web framework), running on **Uvicorn** (an ASGI server — the actual program that listens on a network port and hands incoming requests to FastAPI).

**Key files:**

| File | Role |
|---|---|
| [`backend/server.py`](backend/server.py) | The **entry point**. Creates the FastAPI app, registers all routers, configures CORS, and runs one-time startup tasks (database indexes, data migrations, seeding demo data) |
| [`backend/database.py`](backend/database.py) | Opens the connection to MongoDB using **Motor** (an async MongoDB driver) |
| [`backend/auth_utils.py`](backend/auth_utils.py) | Password hashing (bcrypt), JWT token creation/validation, and role-checking "dependencies" used to protect routes |
| [`backend/notify.py`](backend/notify.py) | Sends emails (via Resend) and WhatsApp messages (via Twilio) |
| [`backend/zoom_service.py`](backend/zoom_service.py) | Talks to the Zoom API to create video meeting links for live classes |
| [`backend/storage_service.py`](backend/storage_service.py) | Uploads/downloads files to/from Azure Blob Storage (falls back to the local disk when running on a laptop) |
| [`backend/seed.py`](backend/seed.py) | Creates demo accounts and sample courses/tests the very first time the app starts against an empty database |
| [`backend/routers/`](backend/routers/) | 17 files, each grouping related API endpoints (see table below) |
| [`backend/requirements.txt`](backend/requirements.txt) | Lists every Python library the backend depends on |
| [`backend/Dockerfile`](backend/Dockerfile) | Instructions for packaging the backend into a Docker container image |

**The 17 routers** (each is a self-contained group of related endpoints, "mounted" onto the app in `server.py`):

| Router file | Endpoints it handles |
|---|---|
| [`auth.py`](backend/routers/auth.py) | Register, login, logout, "who am I", password reset |
| [`courses.py`](backend/routers/courses.py) | Create/list/edit courses, sections, lessons, enrollment |
| [`tests.py`](backend/routers/tests.py) | Create tests, take tests, view results, leaderboard |
| [`live_classes.py`](backend/routers/live_classes.py) | Schedule/join live Zoom classes, attendance |
| [`assignments.py`](backend/routers/assignments.py) | Post assignments, submit work, grade submissions |
| [`announcements.py`](backend/routers/announcements.py) | Post/read academy-wide announcements |
| [`dashboard.py`](backend/routers/dashboard.py) | Summary statistics for student/teacher dashboards |
| [`payments.py`](backend/routers/payments.py) | Razorpay order creation, payment verification, admin payment records |
| [`batches.py`](backend/routers/batches.py) | Manage course "batches" (morning/evening sections) |
| [`files.py`](backend/routers/files.py) | Upload/download files (delegates to `storage_service.py`) |
| [`certificates.py`](backend/routers/certificates.py) | Generate course-completion certificates |
| [`notifications.py`](backend/routers/notifications.py) | In-app notification bell |
| [`admin.py`](backend/routers/admin.py) | User management (admin-only) |
| [`comments.py`](backend/routers/comments.py) | Discussion threads under lessons |
| [`enquiries.py`](backend/routers/enquiries.py) | Public "contact us" form submissions |
| [`site_config.py`](backend/routers/site_config.py) | Site branding configuration |
| [`teacher_profiles.py`](backend/routers/teacher_profiles.py) | Public teacher profile pages |

**How it interacts with other components:** The backend is the *only* piece of the system allowed to talk to MongoDB, Azure Blob Storage, Razorpay, Resend, Twilio, and Zoom. This is a deliberate security boundary — see [Section 8](#8-security-model).

---

### 4.3 Database — MongoDB

**What it is:** A **NoSQL document database**. Unlike a traditional spreadsheet-like ("relational") database with rigid tables and columns, MongoDB stores data as flexible JSON-like documents grouped into "collections" (roughly equivalent to a table).

**Where it runs:**
- **Locally:** Inside a Docker container (see `docker run ... mongo:7` in [TUTORIAL.md](TUTORIAL.md)), reachable at `mongodb://localhost:27017`
- **In production:** A managed cluster on **MongoDB Atlas** (MongoDB's own cloud database hosting service) — the backend connects to it using a `mongodb+srv://` connection string stored in the `MONGO_URL` environment variable

**How the backend talks to it:** Through [`backend/database.py`](backend/database.py), using the **Motor** library — an *asynchronous* MongoDB driver that lets FastAPI handle many requests concurrently without blocking on slow database operations.

```python
# backend/database.py (simplified)
client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]
```

Every router imports this single `db` object and calls methods like `db.courses.find(...)`, `db.users.insert_one(...)`, etc.

See [Section 9](#9-database-collections-reference) for the full list of collections and what each one stores.

---

### 4.4 File Storage — Azure Blob Storage

**What it is:** "Blob" stands for **Binary Large Object** — cloud storage designed for holding files (images, PDFs, videos) rather than structured data. Think of it as a limitless, internet-accessible hard drive.

**Why not just store files in MongoDB or on the server's own disk?** Two reasons:
1. Files like lecture videos can be hundreds of megabytes — databases are not designed for this.
2. Azure Container Apps (where the backend runs) have **ephemeral** (temporary) disks — anything written to local disk is *lost* whenever the container restarts or redeploys. A separate, permanent storage service is required.

**Where it's implemented:** [`backend/storage_service.py`](backend/storage_service.py). This file has *two modes*, chosen automatically:

```python
def _azure_connection_string() -> str:
    return os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "").strip()
```

- **If `AZURE_STORAGE_CONNECTION_STRING` is set** (in production) → files go to a real Azure Blob container named `uploads`.
- **If it's not set** (in local development) → files are silently written to the `backend/uploads/` folder on your laptop instead.

This "environment-aware fallback" pattern means the exact same code — [`backend/routers/files.py`](backend/routers/files.py) calling `storage_service.put_object()` / `get_object()` — works identically whether you're on your laptop or in the cloud.

---

### 4.5 Third-Party Services

The backend integrates with four external companies' APIs (Application Programming Interfaces — see glossary) to provide features it couldn't build itself:

| Service | Used for | Implemented in | Key(s) needed |
|---|---|---|---|
| **Razorpay** | Processing real credit card / UPI payments for course fees | [`backend/routers/payments.py`](backend/routers/payments.py) | `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` |
| **Resend** | Sending transactional emails (password reset, enrollment confirmation) | [`backend/notify.py`](backend/notify.py) | `RESEND_API_KEY` |
| **Twilio** | Sending WhatsApp notifications | [`backend/notify.py`](backend/notify.py) | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` |
| **Zoom** | Auto-creating video meeting links for scheduled live classes | [`backend/zoom_service.py`](backend/zoom_service.py) | `ZOOM_ACCOUNT_ID`, `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET` |

All four are **optional** at the code level — each module checks whether its required keys are present (`is_configured()`-style functions) and gracefully disables the feature rather than crashing if they're missing. This is why the app can run locally without ever touching a real payment gateway.

---

### 4.6 Infrastructure — Docker, Azure Container Apps, Azure Static Web Apps

This is the "plumbing" that takes the frontend and backend code and makes them run reliably, at scale, on the internet.

#### Docker & Containers

**What it is:** Docker packages an application *together with everything it needs to run* (the exact Python version, all libraries, OS-level dependencies) into a single portable unit called an **image**. Running that image produces a **container** — an isolated, lightweight process that behaves identically no matter what machine it runs on.

**Where it's used:** [`backend/Dockerfile`](backend/Dockerfile) defines how to build the backend's image:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m appuser && chown -R appuser /app
USER appuser
EXPOSE 8001
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
```

Each line is an **instruction** — explained fully, step by step, in [TUTORIAL.md](TUTORIAL.md#module-4-containerize-the-backend-with-docker).

> **Only the backend is containerized.** The frontend is *not* — because it's a static site (plain HTML/CSS/JS files after being "built"), it doesn't need its own running process; it's just served as files (see Static Web Apps below).

#### Azure Container Apps

**What it is:** A **serverless container hosting service**. You give it a Docker image; it runs containers of that image for you, automatically handling networking, HTTPS certificates, scaling (running more copies under heavy load, fewer — even zero — when idle), and restarts if the app crashes.

**Where it's configured:** Not a single file in the repo — it's an Azure *resource*, created via the `az containerapp create` command (see [DEPLOYMENT.md](DEPLOYMENT.md)) and updated by [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml). Configuration (environment variables, secrets) is stored in Azure itself, not in the codebase — see [Environment Variables](#environment-variables).

This project's Container App is configured with `--min-replicas 0`, meaning it can scale down to **zero running containers** when nobody is using the app (to save cost), and automatically starts one up again (taking a few seconds — a "cold start") when the next request arrives.

#### Azure Container Registry (ACR)

**What it is:** A private storage location for Docker images — like a company-internal version of Docker Hub. Before Azure Container Apps can *run* the backend's image, that image has to be built and stored somewhere Azure can pull it from.

**How it's used here:** The command `az acr build --registry coachingacademyacr --image coaching-backend:v1 ./backend` builds the Docker image **in the cloud** (not on the developer's laptop) directly from the `backend/` folder, and stores the resulting image in the registry named `coachingacademyacr`.

#### Azure Static Web Apps

**What it is:** A hosting service purpose-built for frontend-only apps (no server-side code) — it uploads your built HTML/CSS/JS files to a global **CDN** (Content Delivery Network — copies of your files cached in data centers worldwide, so users everywhere get fast load times) and serves them over HTTPS automatically.

**Where it's configured:** [`frontend/public/staticwebapp.config.json`](frontend/public/staticwebapp.config.json):

```json
{
  "navigationFallback": {
    "rewrite": "/index.html",
    "exclude": ["/static/*", "/docs/*", "*.{css,js,svg,png,...}"]
  }
}
```

This tells Azure: "If someone directly visits a URL like `/app/courses/123` (which doesn't correspond to a real file), serve `index.html` instead and let React Router figure out what to display." Without this, refreshing the browser on any inner page of the SPA would show a "404 Not Found" error, because there's no *actual file* called `courses/123` on the server — React Router only understands that URL *after* the JavaScript has loaded and run.

---

### 4.7 CI/CD — GitHub Actions

**What it is:** **CI/CD** stands for **Continuous Integration / Continuous Deployment** — the practice of automatically testing and shipping code the moment it's pushed to a shared repository, instead of a human manually copying files to a server.

**Where it's configured:** [`.github/workflows/`](.github/workflows/), which contains two **workflow files** (YAML configuration files that GitHub reads to know what automated steps to run):

| File | Triggers on | What it does |
|---|---|---|
| [`deploy-backend.yml`](.github/workflows/deploy-backend.yml) | Any push to `main` that changes files under `backend/` | Builds a new Docker image in ACR, then updates the Container App to use it |
| [`deploy-frontend.yml`](.github/workflows/deploy-frontend.yml) | Any push to `main` that changes files under `frontend/` | Builds the React app (`yarn build`) and uploads the result to the Static Web App |

**How GitHub Actions authenticates to Azure:** It cannot use a developer's personal login. Instead, an Azure **Service Principal** (a machine identity — like a robot's own username/password, scoped to only the permissions it needs) was created and its credentials stored as an encrypted **GitHub Secret** named `AZURE_CREDENTIALS`. Workflows reference secrets like `${{ secrets.AZURE_CREDENTIALS }}` — GitHub injects the real value only at run time and never shows it in logs.

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant GH as GitHub Repo
    participant GHA as GitHub Actions Runner
    participant ACR as Azure Container Registry
    participant CA as Azure Container App

    Dev->>GH: git push origin main
    GH->>GHA: triggers deploy-backend.yml
    GHA->>GHA: az login (using AZURE_CREDENTIALS secret)
    GHA->>ACR: az acr build (builds Docker image from backend/Dockerfile)
    ACR-->>GHA: image built & stored
    GHA->>CA: az containerapp update (point to new image)
    CA-->>Dev: New version live within ~1-2 minutes
```

---

## 5. Technology Glossary

Every technical term used anywhere in this project, explained plainly, with **why it's here** and **where to find it**.

### Frontend concepts

<a name="react"></a>**React** — A JavaScript library for building user interfaces out of reusable "components" (small, self-contained pieces of UI, each responsible for a piece of the screen). *Why here:* it's the most widely-used frontend framework, making this skill highly transferable. *Where:* every `.jsx` file under [`frontend/src/`](frontend/src/).

**Single-Page Application (SPA)** — A web app that loads one HTML page and then uses JavaScript to swap content in and out as the user navigates, rather than requesting a brand-new page from the server for every click. *Why here:* it makes the app feel instant, like a native app. *Where:* the whole `frontend/` folder is one SPA; routing is handled client-side by [`App.js`](frontend/src/App.js).

**JSX** — A syntax extension that lets you write HTML-like markup directly inside JavaScript code. *Where:* every `.jsx` file (e.g. [`frontend/src/pages/Courses.jsx`](frontend/src/pages/Courses.jsx)).

**React Router** — A library that maps URL paths (like `/app/courses`) to specific React components to display, entirely inside the browser (no server round-trip). *Where:* [`frontend/src/App.js`](frontend/src/App.js) uses `<Routes>` and `<Route>` from `react-router-dom`.

**Context API** — React's built-in way to share data (like "the logged-in user") across many components without manually passing it down through every layer ("prop drilling"). *Where:* [`AuthContext.jsx`](frontend/src/context/AuthContext.jsx) and [`SiteConfigContext.jsx`](frontend/src/context/SiteConfigContext.jsx).

**Axios** — A JavaScript library for making HTTP requests (talking to a backend API) from the browser, more convenient than the browser's built-in `fetch`. *Where:* [`frontend/src/lib/api.js`](frontend/src/lib/api.js) — a single shared instance configured once and reused everywhere.

**localStorage** — A browser feature that lets a website store small pieces of text data on the user's own computer, persisting even after the tab is closed. *Why here:* used to remember the login token between visits, so users aren't logged out every time they close the browser. *Where:* `localStorage.getItem("jam_token")` in [`AuthContext.jsx`](frontend/src/context/AuthContext.jsx).

**Tailwind CSS** — A "utility-first" CSS framework: instead of writing custom CSS files, you style elements by combining small pre-made class names directly in your markup (e.g. `className="flex items-center gap-3 px-5 py-2.5"`). *Where:* [`frontend/tailwind.config.js`](frontend/tailwind.config.js) and used throughout every `.jsx` file.

**Radix UI** — A library of unstyled, accessible UI building blocks (dropdown menus, dialogs, tooltips) that handle tricky behavior (keyboard navigation, focus management) correctly out of the box. *Where:* [`frontend/src/components/ui/`](frontend/src/components/ui/) — this project wraps Radix primitives with Tailwind styling (a common pattern known as "shadcn/ui style" components).

**npm / Yarn** — **Package managers**: tools that download and manage the hundreds of third-party code libraries ("packages" or "dependencies") a JavaScript project relies on. *Where:* [`frontend/package.json`](frontend/package.json) lists every dependency; `frontend/yarn.lock` pins their exact versions.

**Webpack / CRACO** — Webpack is a **bundler**: it takes dozens of separate source files and combines ("bundles") them into a small number of optimized files a browser can efficiently download. Create React App (CRA) configures Webpack automatically; **CRACO** lets this project override small pieces of that configuration (like adding a `@/` shortcut for imports) without fully taking over Webpack's config. *Where:* [`frontend/craco.config.js`](frontend/craco.config.js).

---

### Backend concepts

**API (Application Programming Interface)** — A defined set of rules for how one piece of software can request data or actions from another. *Why here:* it's the contract between frontend and backend — the frontend doesn't know or care that the backend is written in Python; it only knows the API's rules.

**REST (Representational State Transfer) API** — A common style of API design where each piece of data (a course, a user) has its own URL, and standard HTTP verbs express what to do with it: `GET` (read), `POST` (create), `PUT`/`PATCH` (update), `DELETE` (remove). *Where:* every endpoint in [`backend/routers/`](backend/routers/), e.g. `GET /api/courses` (list courses), `POST /api/courses` (create one).

**HTTP (HyperText Transfer Protocol)** — The underlying communication protocol the entire web is built on; defines how a "request" (from browser to server) and a "response" (server back to browser) are formatted.

**JSON (JavaScript Object Notation)** — A lightweight text format for representing structured data (`{"name": "Physics", "price": 4999}`), used as the "language" both the frontend and backend speak when exchanging data over the API.

**FastAPI** — A Python web framework for building APIs, chosen for this project because it's fast, has excellent automatic data validation (via Pydantic, below), and generates interactive API documentation automatically. *Where:* [`backend/server.py`](backend/server.py) creates the `FastAPI()` app instance; every file in [`backend/routers/`](backend/routers/) defines `@router.get(...)` / `@router.post(...)` endpoint functions.

**Uvicorn** — An **ASGI server**: the actual low-level program that opens a network port, accepts incoming HTTP connections, and hands each request to FastAPI to process. FastAPI is a *framework* (a set of tools for writing the logic); Uvicorn is the *server* that actually runs it. *Where:* the last line of [`backend/Dockerfile`](backend/Dockerfile) — `CMD ["uvicorn", "server:app", ...]`.

**Pydantic** — A Python library FastAPI uses to define the *shape* of expected data (e.g. "a course must have a `title` string and a `price` number") and automatically validate/reject malformed requests before your own code even runs. *Where:* every `class ... (BaseModel)` in the router files, e.g. `class CourseBody(BaseModel)` in [`courses.py`](backend/routers/courses.py).

**Motor** — An asynchronous Python driver for MongoDB, used so the backend can handle many simultaneous requests efficiently instead of freezing while waiting for a slow database query. *Where:* [`backend/database.py`](backend/database.py).

**async / await** — Python keywords that let a function pause while waiting for a slow operation (like a database query or network call) *without blocking the entire program* — other requests can be processed in the meantime. *Where:* nearly every route function in `backend/routers/` is declared `async def`.

**JWT (JSON Web Token)** — A compact, digitally-signed token that proves "this user successfully logged in" without the server needing to remember every logged-in session in memory. It contains the user's ID and role, signed with a secret key so it can't be forged. *Why here:* it's how the backend knows who's making each request. *Where:* created in [`auth_utils.py`](backend/auth_utils.py)'s `create_access_token()`, sent to the frontend on login, then attached to every subsequent request by [`frontend/src/lib/api.js`](frontend/src/lib/api.js)'s Axios interceptor as an `Authorization: Bearer <token>` header, and verified again by `get_current_user()` in `auth_utils.py` on every protected route.

**bcrypt** — A password-hashing algorithm. *Why here:* passwords are never stored as plain readable text in the database — only their **hash** (a one-way scrambled version) is stored, so even if the database were leaked, the original passwords couldn't be recovered. *Where:* `hash_password()` and `verify_password()` in [`auth_utils.py`](backend/auth_utils.py).

**CORS (Cross-Origin Resource Sharing)** — A browser security rule that blocks a web page from one domain (e.g. `yellow-dune-....azurestaticapps.net`) from making API requests to a different domain (e.g. `coaching-api-....azurecontainerapps.io`) *unless* the target server explicitly allows it. *Why here:* frontend and backend are hosted on two different Azure services with two different domain names, so without CORS configuration, the browser would silently block every API call. *Where:* [`backend/server.py`](backend/server.py)'s `CORSMiddleware`, allowed origins controlled by the `CORS_ORIGINS` environment variable.

**Environment Variables** <a name="environment-variables"></a> — Configuration values (like a database connection string or an API key) supplied to a running program *from outside its source code*, rather than hard-coded. *Why here:* this is what makes the exact same code run correctly on a laptop, in a test environment, and in production — only the environment variables differ. *Where:* read via Python's `os.environ.get(...)` throughout the backend, and defined in a local `.env` file ([`backend/.env`](backend/.env), never committed to Git — see `.gitignore`) or as Azure Container App "secrets" in production.

**`.env` file** — A plain text file listing `KEY=value` pairs, loaded into environment variables at startup by the `python-dotenv` library (`load_dotenv()` in [`server.py`](backend/server.py) and [`database.py`](backend/database.py)). *Why here:* it lets developers configure secrets locally without ever typing them into the terminal or committing them to Git.

**pytest** — A Python testing framework used to write and run automated tests that verify the backend behaves correctly. *Where:* [`backend/tests/`](backend/tests/) — these are **integration tests**: instead of testing functions in isolation, they make real HTTP requests against a running backend (`http://localhost:8001` by default) and check the responses, using the `requests` library. Configured via [`backend/pytest.ini`](backend/pytest.ini) to run in parallel across 2 worker processes using the `pytest-xdist` plugin.

---

### Database concepts

**Database** — A system for storing data so it can be reliably saved, searched, and retrieved later — the permanent "memory" of the application (unlike variables in a running program, which vanish when it stops).

**NoSQL** — A category of databases that don't use the traditional rows-and-columns "table" model. MongoDB (used here) is a **document database**: each record is a flexible, JSON-like object that can have nested fields and arrays.

**Collection** — MongoDB's equivalent of a "table" — a named group of related documents (e.g. the `courses` collection holds every course document). See [Section 9](#9-database-collections-reference) for the full list used in this project.

**Document** — A single record in MongoDB, stored as JSON-like data (technically **BSON** — Binary JSON, a binary-encoded superset of JSON that also supports extra types like dates).

**`_id` field** — Every MongoDB document has a unique identifier field called `_id`. This project uses randomly generated **UUIDs** (Universally Unique Identifiers — long random strings virtually guaranteed not to collide) as `_id` values instead of MongoDB's default auto-generated IDs, e.g. `"_id": str(uuid.uuid4())` in [`seed.py`](backend/seed.py).

**Index** — A special data structure that dramatically speeds up searching a collection by a specific field, at the cost of extra storage. *Where:* `backend/server.py`'s startup function creates several, e.g. `await db.users.create_index("email", unique=True)` — this also *enforces* that no two users can ever share an email address.

**MongoDB Atlas** — MongoDB's own managed cloud database hosting service. *Why here:* rather than the developer running and maintaining their own database server, Atlas handles backups, security patches, and scaling. This project uses Atlas's free **M0** tier. *Where:* not a repo file — it's an external cloud resource, connected to via the `MONGO_URL` environment variable.

**Connection string** — A specially-formatted URL that tells a database driver how to reach and authenticate with a database, e.g. `mongodb+srv://username:password@cluster.mongodb.net/`. This is one of the most sensitive secrets in the whole system — anyone with it has full access to the database.

---

### Cloud & DevOps concepts

**Cloud Computing** — Renting computing resources (servers, storage, databases) from a provider (Microsoft Azure, AWS, Google Cloud) over the internet, instead of buying and maintaining physical hardware yourself.

**Microsoft Azure** — The specific cloud provider used to host this project's backend, frontend, and file storage.

**Docker** — See [Section 4.6](#docker--containers) above. In one sentence: it packages an app plus everything it needs to run into a portable, consistent unit.

**Container** — A running instance of a Docker image — an isolated process with its own filesystem and dependencies, but sharing the host machine's operating system kernel (making it much lighter-weight than a full virtual machine).

**Container Registry** — A storage service for Docker images, so they can be built once and then pulled/run anywhere. This project uses **Azure Container Registry (ACR)**.

**Serverless** — A cloud model where you don't manage the underlying servers at all — you just supply code (or a container image) and the platform handles running it, scaling it, and even shutting it down completely when idle. Azure Container Apps (used here) is a serverless container platform.

**Azure Container Apps** — See [Section 4.6](#azure-container-apps). Runs the backend's Docker container in the cloud with automatic scaling (including scaling to *zero* when idle).

**Azure Static Web Apps** — See [Section 4.6](#azure-static-web-apps). Hosts the built frontend files on a global CDN.

**Azure Blob Storage** — See [Section 4.4](#44-file-storage--azure-blob-storage). Stores uploaded files (videos, PDFs, images).

**CDN (Content Delivery Network)** — A network of servers distributed around the world that cache copies of static files close to users, so a student in Mumbai and one in New York both get fast load times.

**CI/CD** — See [Section 4.7](#47-cicd--github-actions). Continuous Integration / Continuous Deployment — automatically testing and shipping code changes.

**GitHub** — A cloud platform for hosting **Git** repositories (see below) and collaborating on code. This project's source code lives at `github.com/VinodPungle/coaching-academy`.

**Git** — A **version control system**: software that tracks every change ever made to a codebase, letting multiple people collaborate, see history, and revert mistakes. *Where:* the hidden `.git/` folder in the repo root; every `git commit` in this project's history.

**GitHub Actions** — GitHub's built-in CI/CD automation feature. *Where:* [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) and [`.github/workflows/deploy-frontend.yml`](.github/workflows/deploy-frontend.yml).

**YAML** — A human-readable data format (using indentation instead of brackets) commonly used for configuration files. *Where:* both GitHub Actions workflow files are written in YAML.

**Workflow / Job / Step** — GitHub Actions terminology: a **workflow** (one `.yml` file) contains one or more **jobs** (which can run in parallel), and each job contains a sequence of **steps** (individual commands or pre-built "actions") that run in order.

**GitHub Secrets** — Encrypted values stored in a GitHub repository's settings, accessible to workflows (as `${{ secrets.NAME }}`) but never shown in logs or to unauthorized users. *Where:* `AZURE_CREDENTIALS` and `AZURE_STATIC_WEB_APPS_API_TOKEN` in this repo's Settings → Secrets and variables → Actions.

**GitHub Variables** — Like Secrets, but for *non-sensitive* configuration values that are safe to be visible in logs (e.g. a resource group name). *Where:* `ACR_NAME`, `AZURE_RESOURCE_GROUP`, `CONTAINER_APP_NAME`, `REACT_APP_BACKEND_URL`, `REACT_APP_ACADEMY_NAME`.

**Service Principal** — An identity in Azure Active Directory (Azure's identity/access system) created specifically for an application or automated process to use, rather than a human logging in — like a robot's own restricted user account. *Why here:* GitHub Actions needs *some* identity to authenticate to Azure and deploy on the developer's behalf, without ever using the developer's personal login credentials.

**Azure CLI (`az`)** — A command-line tool for creating and managing Azure resources by typing commands, instead of clicking through a web dashboard. Used extensively when this project was first deployed (see [DEPLOYMENT.md](DEPLOYMENT.md)) and inside `deploy-backend.yml`.

**GitHub CLI (`gh`)** — A command-line tool for interacting with GitHub (creating repos, setting secrets, checking workflow runs) without opening a browser.

---

## 6. Request & Data Flow Walkthroughs

### 6.1 Login Flow

```mermaid
sequenceDiagram
    participant U as User (Browser)
    participant F as Frontend (React)
    participant B as Backend (FastAPI)
    participant DB as MongoDB

    U->>F: Enters email + password, clicks "Log In"
    F->>B: POST /api/auth/login {email, password}
    B->>DB: db.users.find_one({email})
    DB-->>B: user document (with password_hash)
    B->>B: bcrypt.checkpw(password, password_hash)
    alt password correct
        B->>B: create_access_token() → JWT
        B-->>F: 200 OK {user, access_token}
        F->>F: localStorage.setItem("jam_token", access_token)
        F-->>U: Redirect to /app/dashboard
    else password wrong
        B-->>F: 401 Unauthorized
        F-->>U: Show error message
    end
```

Every subsequent request the frontend makes automatically includes the token — see [`frontend/src/lib/api.js`](frontend/src/lib/api.js)'s request interceptor:

```js
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("jam_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
```

On the backend, [`auth_utils.py`](backend/auth_utils.py)'s `get_current_user()` function reads that header, verifies the JWT's signature, and looks up the user — this is used as a FastAPI **dependency** (`Depends(get_current_user)`) on every route that requires login.

---

### 6.2 Browsing Courses (Public Data Flow)

1. Student navigates to `/app/courses` in the browser.
2. React Router renders `frontend/src/pages/Courses.jsx`.
3. That component calls `api.get("/courses")` on mount.
4. Request hits `GET /api/courses` in [`backend/routers/courses.py`](backend/routers/courses.py).
5. The handler queries MongoDB: `db.courses.find({"published": True})`.
6. MongoDB returns matching documents; FastAPI serializes them to JSON automatically.
7. Axios receives the JSON array; React re-renders the page with course cards.

This route doesn't strictly require login (`Depends(optional_user)`), so even a logged-out visitor can browse the public course catalog.

---

### 6.3 Enrolling & Paying for a Course

```mermaid
sequenceDiagram
    participant U as Student (Browser)
    participant F as Frontend
    participant B as Backend
    participant RP as Razorpay
    participant DB as MongoDB

    U->>F: Clicks "Enroll Now"
    F->>B: POST /api/payments/razorpay/create-order {course_id}
    B->>RP: Create order (amount, currency)
    RP-->>B: order_id
    B-->>F: {order_id, razorpay_key_id}
    F->>RP: Opens Razorpay Checkout widget (client-side)
    U->>RP: Enters card/UPI details, pays
    RP-->>F: {payment_id, order_id, signature}
    F->>B: POST /api/payments/razorpay/verify {payment_id, order_id, signature}
    B->>B: Verify HMAC signature using RAZORPAY_KEY_SECRET
    B->>DB: Insert enrollment + payment record
    B-->>F: 200 OK
    F-->>U: "Enrollment successful!"
```

**Why signature verification matters:** anyone could fake a "payment successful" request straight to the backend without ever actually paying. The signature (an HMAC — Hash-based Message Authentication Code, computed using the secret `RAZORPAY_KEY_SECRET` that only the backend and Razorpay know) proves the payment confirmation genuinely came from Razorpay and wasn't forged. See [`payments.py`](backend/routers/payments.py).

---

### 6.4 Uploading a File (Video, PDF, Image)

1. Teacher selects a file in the browser (e.g. attaching a lecture PDF).
2. Frontend calls `uploadFile()` from [`lib/api.js`](frontend/src/lib/api.js), which `POST`s the file as `multipart/form-data` to `/api/files/upload`.
3. [`backend/routers/files.py`](backend/routers/files.py) checks the file extension and size against allow-lists, then calls `storage_service.put_object(...)`.
4. `storage_service.py` checks whether `AZURE_STORAGE_CONNECTION_STRING` is set:
   - **In production:** uploads the bytes to the Azure Blob container `uploads`.
   - **Locally:** writes the bytes to `backend/uploads/` on disk.
5. A metadata record is saved in MongoDB's `files` collection (filename, size, uploader, storage path).
6. The backend returns a URL like `/api/files/{file_id}` that the frontend can use to display or download the file later — `GET /api/files/{file_id}` fetches the bytes back from wherever they were actually stored, so the rest of the app never needs to know *which* storage backend is in use.

---

### 6.5 Scheduling a Live Class (Zoom Integration)

1. Teacher fills out the "Schedule Live Class" form (title, date/time, duration).
2. Frontend `POST`s to `/api/live-classes`.
3. [`backend/routers/live_classes.py`](backend/routers/live_classes.py) calls `zoom_service.create_zoom_meeting(...)`.
4. [`zoom_service.py`](backend/zoom_service.py) authenticates to Zoom using **Server-to-Server OAuth** (exchanges `ZOOM_ACCOUNT_ID` + `ZOOM_CLIENT_ID` + `ZOOM_CLIENT_SECRET` for a temporary access token), then calls Zoom's API to create a meeting.
5. Zoom returns a join URL, which is saved on the live class document in MongoDB.
6. When class time arrives, students click "Join" in the app, which simply opens that Zoom URL — Zoom itself hosts the actual video call, not this application.

---

### 6.6 Deploying a Code Change (CI/CD Flow)

Already diagrammed in [Section 4.7](#47-cicd--github-actions) — summarized as text here:

1. Developer edits a file, e.g. `backend/routers/courses.py`.
2. `git add`, `git commit`, `git push origin main`.
3. GitHub detects the push touches `backend/**` and automatically starts the `deploy-backend.yml` workflow.
4. The workflow runner authenticates to Azure using the `AZURE_CREDENTIALS` secret.
5. It runs `az acr build` — this rebuilds the Docker image *in Azure's cloud* (not on the runner itself) from the current `backend/Dockerfile` and code.
6. It runs `az containerapp update` to point the live Container App at the freshly built image tag.
7. Azure gradually shifts traffic to the new container, and the change is live — typically within 1-3 minutes of the original `git push`, with zero manual server access required.

---

## 7. Folder-by-Folder Reference Map

```
coaching-academy/
├── backend/                          Python/FastAPI REST API
│   ├── server.py                     App entry point, startup tasks, CORS
│   ├── database.py                   MongoDB connection (Motor)
│   ├── auth_utils.py                 JWT, bcrypt, role-checking
│   ├── notify.py                     Resend (email) + Twilio (WhatsApp)
│   ├── zoom_service.py               Zoom meeting creation
│   ├── storage_service.py            Azure Blob Storage / local disk files
│   ├── seed.py                       Demo data seeding
│   ├── requirements.txt              Python dependencies
│   ├── Dockerfile                    Container build instructions
│   ├── .dockerignore                 Files excluded from the Docker build
│   ├── .env                          Local secrets (NEVER committed — gitignored)
│   ├── routers/                      17 files, one per feature area (see 4.2)
│   ├── tests/                        pytest integration tests
│   └── uploads/                      Local-disk file storage fallback (dev only)
│
├── frontend/                         React SPA
│   ├── src/
│   │   ├── App.js                    Route definitions
│   │   ├── context/                  AuthContext, SiteConfigContext
│   │   ├── lib/                      api.js (Axios), config.js, utils.js, video.js
│   │   ├── pages/                    28 page components (one per screen)
│   │   └── components/               Shared UI, including ui/ (46 primitives)
│   ├── public/
│   │   └── staticwebapp.config.json  Azure SWA routing config
│   ├── package.json                  JS dependencies + npm scripts
│   ├── craco.config.js               Build configuration overrides
│   ├── tailwind.config.js            Tailwind CSS theme configuration
│   └── .env                          Local frontend config (gitignored)
│
├── .github/
│   └── workflows/
│       ├── deploy-backend.yml        CI/CD: backend → Azure Container Apps
│       └── deploy-frontend.yml       CI/CD: frontend → Azure Static Web Apps
│
├── DEPLOYMENT.md                     Step-by-step Azure setup/redeploy runbook
├── ARCHITECTURE.md                   This document
└── TUTORIAL.md                       Hands-on rebuild-from-scratch tutorial
```

---

## 8. Security Model

| Concern | How it's addressed | Where |
|---|---|---|
| Passwords in the database | Hashed with bcrypt, never stored in plain text | [`auth_utils.py`](backend/auth_utils.py) |
| Proving who's logged in | Signed JWTs, verified on every protected request | [`auth_utils.py`](backend/auth_utils.py) |
| Role-based access (admin vs teacher vs student) | `require_role(*roles)` FastAPI dependency rejects unauthorized roles with `403 Forbidden` | [`auth_utils.py`](backend/auth_utils.py), used throughout `routers/` |
| Cross-domain API access | CORS explicitly allow-lists only the real frontend domain(s), not `*` in production | `CORS_ORIGINS` env var, [`server.py`](backend/server.py) |
| Secrets (DB passwords, API keys) | Never committed to Git (`.gitignore`); stored as Azure Container App **secrets** in production, injected as environment variables at container startup | `.gitignore`, Azure Container App configuration |
| Payment authenticity | Razorpay's HMAC signature verified server-side before recording any payment as successful | [`payments.py`](backend/routers/payments.py) |
| Automated deployment credentials | A narrowly-scoped Service Principal (only Contributor on one resource group) rather than a personal Azure login | GitHub Secret `AZURE_CREDENTIALS` |

---

## 9. Database Collections Reference

MongoDB has no fixed schema enforced by the database itself — the "shape" of each collection is really defined by the Pydantic models and the code that writes to it. Here's what each collection conceptually holds:

| Collection | Holds | Key fields | Written by |
|---|---|---|---|
| `users` | Every account (student/teacher/admin) | `_id`, `email` (unique), `password_hash`, `role`, `is_demo` | `auth.py`, `seed.py` |
| `courses` | Course catalog, including nested sections → sub-topics → lessons | `_id`, `title`, `subject`, `price`, `teacher_id`, `sections[]` | `courses.py` |
| `enrollments` | Which student is enrolled in which course | `course_id`, `student_id` (unique pair) | `courses.py`, `payments.py` |
| `tests` | Mock tests with embedded questions | `_id`, `questions[]`, `teacher_id` | `tests.py` |
| `test_attempts` | A student's answers + score for one test | `test_id`, `student_id` (unique pair) | `tests.py` |
| `live_classes` | Scheduled Zoom sessions | `_id`, `start_time`, `meeting_link`, `teacher_id` | `live_classes.py` |
| `assignments` | Homework posted by teachers | `_id`, `due_date`, `teacher_id` | `assignments.py` |
| `submissions` | A student's assignment submission | `assignment_id`, `student_id` | `assignments.py` |
| `announcements` | Academy-wide notices | `_id`, `title`, `body` | `announcements.py` |
| `batches` | Course sections (e.g. Morning/Evening) | `course_id`, `schedule`, `capacity` | `batches.py` |
| `payments` | Payment records | `student_id`, `course_id`, `amount`, Razorpay IDs | `payments.py` |
| `files` | Metadata for every uploaded file | `_id`, `filename`, `storage_path`, `uploader_id` | `files.py` |
| `notifications` | In-app notification bell items | `user_id`, `created_at` | various routers via `notify.py` |
| `certificates` | Issued completion certificates | `student_id`, `course_id` | `certificates.py` |
| `password_reset_tokens` | Temporary tokens for "forgot password" | `expires_at` (auto-deleted by a MongoDB TTL index) | `auth.py` |
| `system_flags` | Internal "has this one-time migration already run?" markers | `_id` (a flag name), `at` (timestamp) | `server.py` startup logic |

> **Note on `system_flags`:** this project's `server.py` contains several *one-time* data-migration and cleanup routines that run automatically at startup, guarded by a flag document in this collection so they never re-run once completed. This is a common real-world pattern for evolving a live database schema without downtime — worth understanding, but also worth being cautious with, since a poorly-guarded migration can unintentionally re-run against fresh or restored databases.
