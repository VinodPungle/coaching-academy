# Tutorial — Build & Deploy the Coaching Academy Platform From Scratch

> **Before you start:** Read [ARCHITECTURE.md](ARCHITECTURE.md) first, or at least skim [Section 2](ARCHITECTURE.md#2-the-big-picture--system-architecture-diagram) and [Section 5](ARCHITECTURE.md#5-technology-glossary). This tutorial assumes **zero prior experience** — every command is explained, every concept is defined before it's used, and nothing is left implied. Some steps will feel slow if you already know the basics — that's fine, skim ahead.

**What you'll actually do in this tutorial:** take this project's existing, already-written source code and (1) run it on your own laptop, (2) package it with Docker, (3) deploy it to Microsoft Azure's cloud, and (4) set up automatic deployment via GitHub Actions — exactly the real journey a professional engineering team follows to ship a web application. You will not be writing the React/FastAPI application code from a blank file; you'll be learning the *infrastructure and deployment* skills around an app that's already built, which is what most junior engineering jobs actually require on day one.

---

## Table of Contents

1. [What You'll Build & Learn](#1-what-youll-build--learn)
2. [Prerequisites — Accounts](#2-prerequisites--accounts)
3. [Prerequisites — Tools to Install](#3-prerequisites--tools-to-install)
4. [Module 1: Get the Code](#module-1-get-the-code)
5. [Module 2: Run the Backend Locally](#module-2-run-the-backend-locally)
6. [Module 3: Run the Frontend Locally](#module-3-run-the-frontend-locally)
7. [Module 4: Containerize the Backend with Docker](#module-4-containerize-the-backend-with-docker)
8. [Module 5: Set Up Cloud Accounts](#module-5-set-up-cloud-accounts)
9. [Module 6: Provision Azure Infrastructure](#module-6-provision-azure-infrastructure)
10. [Module 7: Deploy the Backend to Azure](#module-7-deploy-the-backend-to-azure)
11. [Module 8: Deploy the Frontend to Azure](#module-8-deploy-the-frontend-to-azure)
12. [Module 9: Set Up CI/CD With GitHub Actions](#module-9-set-up-cicd-with-github-actions)
13. [Module 10: End-to-End Verification Checklist](#module-10-end-to-end-verification-checklist)
14. [Troubleshooting Guide](#14-troubleshooting-guide)
15. [Interview Preparation](#15-interview-preparation)
16. [Presenting This Project in Interviews & On Your Resume](#16-presenting-this-project-in-interviews--on-your-resume)

---

## 1. What You'll Build & Learn

By the end of this tutorial, you will have:

- ✅ Run a full-stack web application (React + FastAPI + MongoDB) entirely on your own laptop
- ✅ Packaged a backend application into a **Docker container**
- ✅ Created cloud infrastructure on **Microsoft Azure** using the command line
- ✅ Deployed a real, publicly-accessible web application to the internet
- ✅ Set up **CI/CD** so that future code changes deploy automatically
- ✅ Learned enough about every technology involved to explain it confidently in a job interview

**Skills covered:** Git & GitHub, Python virtual environments, REST APIs, JWT authentication, MongoDB, React, environment variables, Docker, Azure cloud services, GitHub Actions, CI/CD pipelines.

---

## 2. Prerequisites — Accounts

You need free accounts on the following services before starting. Create them now so you're not interrupted mid-tutorial.

| Account | Why you need it | Sign up at | Cost |
|---|---|---|---|
| **GitHub** | Hosts the source code; required for CI/CD | github.com | Free |
| **Microsoft Azure** | Hosts the live application (backend, frontend, file storage) | azure.microsoft.com/free | Free tier + ~$200 trial credit for new accounts |
| **MongoDB Atlas** | Hosts the production database | cloud.mongodb.com | Free forever on the M0 tier |

**Optional** (only needed if you want to test the real integrations — the app works fine without them, those features just stay disabled):

| Account | Enables |
|---|---|
| Razorpay | Real payment processing |
| Resend | Sending real emails |
| Twilio | Sending real WhatsApp messages |
| Zoom (with a Server-to-Server OAuth app) | Auto-creating real video meeting links |

> **Concept Explainer — "Account" vs "API Key"**
> Signing up for an account gets you into a company's dashboard. From that dashboard, you generate **API keys** (essentially, a username/password pair specifically for *programs*, not humans, to use) which your application then uses to authenticate its requests to that company's servers. You'll generate several of these throughout this tutorial.

---

## 3. Prerequisites — Tools to Install

Install these on your laptop. Versions shown are what this project was built and tested with — newer patch versions are generally fine.

| Tool | What it is | Version used | Install command (Windows, via winget) |
|---|---|---|---|
| **Git** | Version control (tracks code changes) | 2.50+ | `winget install --id Git.Git -e` |
| **Python** | Runs the backend | 3.12+ | `winget install --id Python.Python.3.12 -e` |
| **Node.js** | Runs frontend build tools | 20+ | `winget install --id OpenJS.NodeJS.LTS -e` |
| **Yarn** | JavaScript package manager | 1.22+ | `npm install -g yarn` (after Node is installed) |
| **Docker Desktop** | Builds/runs containers | 28+ | `winget install --id Docker.DockerDesktop -e` |
| **Azure CLI** | Command-line control of Azure | latest | `winget install --id Microsoft.AzureCLI -e` |
| **GitHub CLI** | Command-line control of GitHub | latest | `winget install --id GitHub.cli -e` |

> On macOS, replace `winget install --id X -e` with `brew install <package>` (using [Homebrew](https://brew.sh)). On Linux, use your distribution's package manager (`apt`, `dnf`, etc.) or each tool's official install script.

**Verify every install** by running these and confirming each prints a version number (not an error):

```powershell
git --version
python --version
node --version
yarn --version
docker --version
az --version
gh --version
```

> **Concept Explainer — Command Line / Terminal**
> The terminal (also called a shell, console, or command line) is a text-based way to control your computer by typing commands instead of clicking icons. Almost all professional software development happens here because it's precise, scriptable, and repeatable. This tutorial uses **PowerShell** (Windows) syntax; if you're on macOS/Linux, use **bash** — the commands are nearly identical, with minor syntax differences noted where they matter.

---

## Module 1: Get the Code

### What we're doing and why

We're downloading ("cloning") the project's source code from GitHub onto your laptop, so you have a local copy to run and modify.

### How to do it

```powershell
git clone https://github.com/VinodPungle/coaching-academy.git
cd coaching-academy
```

> **Concept Explainer — Git & GitHub**
> **Git** is version control software: it tracks every change ever made to a set of files, letting you see history, undo mistakes, and work on features without disturbing the main codebase. **GitHub** is a website that hosts Git repositories in the cloud, adding collaboration features (pull requests, issues, and — crucial for this tutorial — **GitHub Actions**, covered in Module 9). Every `git clone`, `git commit`, and `git push` you'll do interacts with these two things: Git is the *tool* running on your machine; GitHub is the *remote server* your local copy talks to.
>
> **Real-world use case:** every professional software team uses Git/GitHub (or an equivalent like GitLab/Bitbucket) — it's how multiple developers work on the same codebase without overwriting each other's work.

### ✅ Verification checkpoint

```powershell
ls
```
You should see folders named `backend/`, `frontend/`, `.github/`, and files like `ARCHITECTURE.md`.

---

## Module 2: Run the Backend Locally

### What we're doing and why

The backend is a Python program. Before it can run, we need: (1) Python's own isolated environment for this project, (2) all the third-party libraries it depends on, (3) a running MongoDB database for it to connect to, and (4) a configuration file telling it *how* to connect to that database and other services.

### Step 2.1 — Create a Python virtual environment

```powershell
cd backend
python -m venv .venv
```

> **Concept Explainer — Virtual Environment**
> A virtual environment (`venv`) is an isolated copy of Python with its own separate set of installed libraries, completely separate from your computer's main Python installation and from any other project's environment. **Why it matters:** Project A might need version 2.0 of a library while Project B needs version 3.0 — without isolated environments, installing one would break the other. Every serious Python project uses one.

Activate it:
```powershell
.venv\Scripts\Activate.ps1
```
Your terminal prompt should now show `(.venv)` at the start of the line — that's your confirmation it's active.

### Step 2.2 — Install the backend's dependencies

```powershell
pip install -r requirements.txt
```

> **Concept Explainer — Dependencies & `requirements.txt`**
> This project's Python code calls functions from libraries it didn't write itself — FastAPI, Motor (MongoDB driver), bcrypt, etc. Each of those is a **dependency**. [`requirements.txt`](backend/requirements.txt) is a plain text list of every dependency and (optionally) which version to use, so anyone can recreate the exact same environment with one command instead of manually installing each library and hoping they picked compatible versions.

### Step 2.3 — Start MongoDB using Docker

```powershell
docker run -d --name coaching-mongo -p 27017:27017 -v coaching_mongo_data:/data/db --restart unless-stopped mongo:7
```

Let's break this command down piece by piece, since it packs in several concepts at once:

| Piece | Meaning |
|---|---|
| `docker run` | Start a new container |
| `-d` | "Detached" — run in the background, don't tie up this terminal |
| `--name coaching-mongo` | Give the container a friendly name so we can refer to it later |
| `-p 27017:27017` | **Port mapping**: connect port 27017 on your laptop to port 27017 *inside* the container (MongoDB's default port) |
| `-v coaching_mongo_data:/data/db` | **Volume**: store the database's actual files in a persistent Docker volume named `coaching_mongo_data`, so data survives even if the container is deleted and recreated |
| `--restart unless-stopped` | Automatically restart this container whenever Docker itself restarts (e.g. after you reboot your laptop) |
| `mongo:7` | The Docker **image** to run — the official MongoDB image, version 7 |

> **Concept Explainer — Port**
> A port is a numbered "door" on a computer that a specific program listens on for incoming network connections. MongoDB's standard door is 27017. By mapping `-p 27017:27017`, requests to `localhost:27017` on your laptop get forwarded into the container.

### Step 2.4 — Create your local environment configuration

Create a file named `.env` inside the `backend/` folder (this file is deliberately excluded from Git via `.gitignore` — it holds secrets that should never be shared or committed):

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=coaching_academy
JWT_SECRET=replace-this-with-a-long-random-string
CORS_ORIGINS=http://localhost:3001
FRONTEND_URL=http://localhost:3001
ACADEMY_NAME=My Test Academy
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=Admin@123
```

Generate a proper random value for `JWT_SECRET` rather than typing something guessable:
```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
Paste the output as the value of `JWT_SECRET`.

> **Concept Explainer — Environment Variables & `.env` files**
> An environment variable is a named value available to a running program from its surrounding "environment" rather than hard-coded into its source. [`backend/database.py`](backend/database.py) reads `MONGO_URL` with `os.environ['MONGO_URL']` — nowhere in the Python code is the actual database address written down; it's supplied externally. A `.env` file is a convenient way to define a bunch of these for local development; the `python-dotenv` library's `load_dotenv()` (called at the top of [`server.py`](backend/server.py)) reads this file and loads its contents into the environment automatically when the app starts.
>
> **Why this matters:** it means the *exact same source code* can run against a test database locally, and a completely different production database in the cloud — the code never changes, only the environment variables do. It also keeps secrets out of Git history, where they'd be permanently visible to anyone with repo access, forever, even if later "deleted."

### Step 2.5 — Start the backend server

```powershell
python -m uvicorn server:app --host 0.0.0.0 --port 8001
```

- `server:app` means "look in `server.py` for a variable named `app`" (that's the `FastAPI()` instance created in [`server.py`](backend/server.py)).
- `--host 0.0.0.0` means "accept connections from any network interface" (not just `localhost`).
- `--port 8001` is the port this project's backend always uses.

### ✅ Verification checkpoint

Open a **new** terminal (leave the server running in the first one) and run:
```powershell
curl http://localhost:8001/api/
```
You should see JSON like `{"message":"My Test Academy LMS API"}`. If you see this, your backend is running and successfully connected to MongoDB (the startup process creates database indexes and seeds demo data — if MongoDB weren't reachable, this command would have crashed on startup instead).

Try logging in as the seeded admin:
```powershell
curl -X POST http://localhost:8001/api/auth/login -H "Content-Type: application/json" -d '{\"email\":\"admin@example.com\",\"password\":\"Admin@123\"}'
```
You should get back a JSON object containing an `access_token`.

---

## Module 3: Run the Frontend Locally

### What we're doing and why

Now we start the React development server, which compiles the frontend's source code into something a browser can run, and serves it with **hot-reload** (automatically refreshing the browser whenever you save a code change).

### Step 3.1 — Install frontend dependencies

```powershell
cd ../frontend
yarn install
```

> **Concept Explainer — npm vs Yarn**
> Both are **package managers** for JavaScript — tools that read a project's dependency list ([`package.json`](frontend/package.json)) and download every required library (into a folder called `node_modules/`). This project standardizes on Yarn (you can see `"packageManager": "yarn@1.22.22..."` pinned in `package.json`). `yarn install` reads `frontend/yarn.lock` — a file that pins the *exact* version of every dependency (and every dependency's dependencies) — guaranteeing that everyone on the team, and every server that ever builds this project, gets identical library versions.

### Step 3.2 — Create your local environment configuration

Create `frontend/.env`:
```env
PORT=3001
REACT_APP_BACKEND_URL=http://localhost:8001
REACT_APP_ACADEMY_NAME=My Test Academy
```

> **Concept Explainer — `REACT_APP_` prefix**
> Create React App only exposes environment variables to your frontend code if their name starts with `REACT_APP_` — this is a deliberate safety guard, since *anything* in a frontend `.env` file ends up embedded in the final JavaScript bundle sent to every visitor's browser (unlike backend `.env` files, which never leave the server). **Never put real secrets in a frontend `.env` file** — only non-sensitive configuration like API URLs.
>
> We set `PORT=3001` here because port 3000 (React's default) might already be used by something else on your machine — you can use the default 3000 if it's free.

### Step 3.3 — Start the frontend

```powershell
yarn start
```

This runs the `start` script defined in [`package.json`](frontend/package.json) (`craco start`), which launches a local development web server and should automatically open your browser.

### ✅ Verification checkpoint

Visit **http://localhost:3001** in your browser. You should see the academy's landing page. Click "Login," enter the admin credentials from Module 2, and confirm you land on the dashboard.

Open your browser's **Developer Tools** (`F12`) → **Network** tab, refresh the page, and find a request to `localhost:8001/api/...` — this is you directly observing the frontend and backend talking to each other over HTTP, exactly as diagrammed in [ARCHITECTURE.md Section 6.1](ARCHITECTURE.md#61-login-flow).

---

## Module 4: Containerize the Backend with Docker

### What we're doing and why

So far, the backend only runs because *you* manually activated a virtual environment and typed a command. A cloud hosting platform needs a way to run it without any of that manual setup — that's exactly what Docker solves: package the app, its dependencies, and instructions for running it, into one portable image.

### Step 4.1 — Understand the Dockerfile

Open [`backend/Dockerfile`](backend/Dockerfile):

```dockerfile
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m appuser && chown -R appuser /app
USER appuser
EXPOSE 8001
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
```

| Instruction | What it does |
|---|---|
| `FROM python:3.12-slim` | Start from an official, minimal Python 3.12 base image — this is our foundation |
| `ENV ...` | Set environment variables inside the image (these two make Python's logging behave better in containers) |
| `WORKDIR /app` | All subsequent commands run inside a folder called `/app` inside the container |
| `COPY requirements.txt .` | Copy just this one file in first... |
| `RUN pip install ...` | ...and install dependencies **before** copying the rest of the code |
| `COPY . .` | Now copy the rest of the application code |
| `RUN useradd ... / USER appuser` | Create a non-root user and switch to it — a security best practice (never run a container's main process as `root` if you don't have to) |
| `EXPOSE 8001` | Documentation that this container listens on port 8001 (doesn't actually open anything by itself) |
| `CMD [...]` | The command that runs when a container starts from this image |

> **Concept Explainer — Why copy `requirements.txt` before the rest of the code?**
> Docker builds images in layers, and **caches** each layer. If you copy *all* your code first and then install dependencies, changing a single line of application code invalidates the cache and forces a full dependency reinstall on every build. By copying only `requirements.txt` first, Docker can reuse the cached "dependencies installed" layer on every subsequent build **unless requirements.txt itself changes** — making rebuilds dramatically faster during development.

### Step 4.2 — Build the image

```powershell
cd backend
docker build -t coaching-backend:local .
```
- `-t coaching-backend:local` **tags** (names) the resulting image so we can refer to it later.
- `.` tells Docker to use the current directory as the **build context** (everything Docker is allowed to `COPY` from).

> **Concept Explainer — Image vs Container**
> An **image** is a static, inert package — like a recipe or a blueprint. A **container** is a *running instance* of that image — like a cake actually baked from the recipe. You can start many containers from the same image, each an independent, isolated process.

### Step 4.3 — Run the container

```powershell
docker run -d --rm --name coaching-backend-test -p 8002:8001 `
  -e MONGO_URL=mongodb://host.docker.internal:27017 `
  -e DB_NAME=coaching_academy `
  -e JWT_SECRET=test-secret `
  coaching-backend:local
```

Notice: we're passing configuration with `-e` (environment variable) flags directly on the command line here, instead of a `.env` file — this container has no `.env` file at all; **all configuration comes from outside**, exactly the pattern described in Module 2's Concept Explainer. `host.docker.internal` is Docker's special hostname that lets a container reach back out to services running on your host laptop (like the MongoDB container from Module 2, which listens on your laptop's `localhost:27017`).

### ✅ Verification checkpoint

```powershell
curl http://localhost:8002/api/
```
You should get the same JSON response as before — but this time, it's coming from a fully isolated Docker container, not your manually-activated virtual environment. Clean up when done:
```powershell
docker stop coaching-backend-test
```

> **The frontend is never containerized in this project.** Because it's built into plain static HTML/CSS/JS files (no server-side code to run), it doesn't need a container — it just needs somewhere to host those files, which is what Azure Static Web Apps does (Module 8).

---

## Module 5: Set Up Cloud Accounts

### Step 5.1 — Azure

1. Go to azure.microsoft.com/free and sign up (a phone number and payment method are required for identity verification, but the free tier and trial credit mean you won't be charged for what this tutorial covers).
2. Once signed up, log in via the CLI:
   ```powershell
   az login
   ```
   This opens a browser window for you to authenticate, then stores a session token locally so future `az` commands don't require logging in again.

> **Concept Explainer — Why does a CLI tool need "login"?**
> Every action `az` performs (creating a server, deleting a database) happens *on Azure's servers*, not on your laptop. Your laptop is just sending authenticated instructions. `az login` proves to Azure's servers who you are and what you're allowed to do, the same way logging into a website with a password does — just via a command-line tool instead of a browser form.

### Step 5.2 — MongoDB Atlas

1. Go to cloud.mongodb.com and sign up.
2. Create a new cluster: choose the **M0 (Free)** tier, cloud provider **Azure**, and a region close to you.
3. Under **Database Access**, create a database user (a username + password specifically for applications to connect with — separate from your own Atlas login).
4. Under **Network Access**, add an IP entry allowing `0.0.0.0/0` ("allow from anywhere") — needed because our Azure-hosted backend won't have a predictable, fixed IP address to allow-list individually.
5. Click **Connect → Drivers**, copy the connection string (it looks like `mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/`).

> **Concept Explainer — Why is "allow from anywhere" acceptable here?**
> Normally, allowing database access from any IP sounds dangerous — but MongoDB Atlas still requires a *correct username and password* for every connection; the network allow-list is a second, independent layer of defense on top of that, not a replacement for it. Opening it to `0.0.0.0/0` is a common, reasonable trade-off for cloud-hosted apps whose server IP isn't fixed or known in advance, **as long as the database credentials themselves are strong and kept secret** — which is exactly why `MONGO_URL` is treated as a sensitive secret throughout this project, never committed to Git.

---

## Module 6: Provision Azure Infrastructure

### What we're doing and why

Before we can deploy our Docker image anywhere, several Azure "resources" (a generic Azure term for any manageable cloud object — a storage account, a database, a container app, etc.) need to exist. We'll create them all via the `az` command-line tool, so every step is a repeatable, documented command rather than manual dashboard clicking.

### Step 6.1 — Pick names and create a Resource Group

```powershell
$RG      = "coaching-academy-rg"
$LOC     = "centralindia"          # pick a region close to you
$ACR     = "myuniqueacademyacr"    # must be globally unique — change this
$ENVNAME = "coaching-env"
$APP     = "coaching-api"
$STORAGE = "myuniqueacademyfiles"  # must be globally unique — change this
$SWA     = "coaching-frontend"

az group create -n $RG -l $LOC
```

> **Concept Explainer — Resource Group**
> A Resource Group is a logical container that groups related Azure resources together for organization, permissions, cost tracking, and — very usefully — bulk deletion (`az group delete` removes everything inside it in one command, handy for cleaning up a tutorial environment afterward).

### Step 6.2 — Create a Storage Account (for file uploads)

```powershell
az storage account create -n $STORAGE -g $RG -l $LOC --sku Standard_LRS --kind StorageV2
$STORAGE_CONN = az storage account show-connection-string -n $STORAGE -g $RG -o tsv
```

This creates the Azure Blob Storage account discussed in [ARCHITECTURE.md Section 4.4](ARCHITECTURE.md#44-file-storage--azure-blob-storage). We don't need to manually create the actual "container" (folder) inside it — [`storage_service.py`](backend/storage_service.py) creates one automatically the first time a file is uploaded.

### Step 6.3 — Create a Container Registry

```powershell
az acr create -n $ACR -g $RG --sku Basic --admin-enabled true
```

This is where our Docker image will live once built — see [ARCHITECTURE.md's Container Registry explainer](ARCHITECTURE.md#azure-container-registry-acr).

### Step 6.4 — Create a Container Apps Environment

```powershell
az extension add --name containerapp --upgrade
az containerapp env create -n $ENVNAME -g $RG -l $LOC
```

> **Concept Explainer — Environment vs App**
> A Container Apps **Environment** is a shared, secure boundary (networking, logging) that one or more individual Container **Apps** run inside — think of the Environment as the "building" and each Container App as a "tenant" inside it. We create the Environment once; we'll create the actual `coaching-api` app inside it in Module 7.

### Step 6.5 — Create the Static Web App

```powershell
az staticwebapp create -n $SWA -g $RG -l eastasia --sku Free
```
(Static Web Apps are only available in a limited set of regions — `eastasia` is used here as an example; check current availability if `centralindia` isn't supported for this resource type.)

### ✅ Verification checkpoint

```powershell
az resource list -g $RG -o table
```
You should see 4 resources listed: the storage account, the container registry, the Container Apps environment, and the static web app.

---

## Module 7: Deploy the Backend to Azure

### Step 7.1 — Build the Docker image in the cloud

```powershell
az acr build --registry $ACR --image coaching-backend:v1 ./backend
```

Notice this is different from Module 4's `docker build` — here, we're not building on our own laptop at all. `az acr build` **uploads the `backend/` folder to Azure and builds the image on Azure's own build servers**, storing the result directly in our registry. This means deployment never depends on your laptop's Docker install being available or powerful enough.

### Step 7.2 — Create the Container App

```powershell
$JWT = python -c "import secrets; print(secrets.token_urlsafe(48))"

az containerapp create -n $APP -g $RG --environment $ENVNAME `
  --image "$ACR.azurecr.io/coaching-backend:v1" `
  --registry-server "$ACR.azurecr.io" `
  --target-port 8001 --ingress external `
  --min-replicas 0 --max-replicas 2 `
  --cpu 0.5 --memory 1.0Gi `
  --secrets mongo-url="<YOUR_ATLAS_CONNECTION_STRING>" jwt-secret="$JWT" storage-conn="$STORAGE_CONN" `
  --env-vars MONGO_URL=secretref:mongo-url JWT_SECRET=secretref:jwt-secret AZURE_STORAGE_CONNECTION_STRING=secretref:storage-conn `
    DB_NAME=coaching_academy ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=changeme `
    CORS_ORIGINS=http://localhost:3001 FRONTEND_URL=http://localhost:3001 `
    ACADEMY_NAME="My Test Academy"
```

> **Concept Explainer — Secrets vs plain Environment Variables in Container Apps**
> Notice two different mechanisms above: `--secrets` stores sensitive values (`mongo-url`, `jwt-secret`) in Azure's encrypted secret store, referenced by env vars using `secretref:name` syntax — the actual value is never visible in the Container App's configuration or logs. `--env-vars` with plain `KEY=value` pairs are for non-sensitive configuration, visible in plaintext in the Azure Portal. **Rule of thumb:** anything that would be bad if leaked (passwords, API keys, connection strings) goes through `--secrets`; anything else (a display name, a feature flag) can be a plain env var.
>
> **Important gotcha to know:** running `az containerapp update --set-env-vars` again later **replaces the entire environment variable list**, it does not merge in new values. Always supply the *complete* list of env vars you want, every time you update — a lesson learned the hard way in this exact project's deployment history.

### ✅ Verification checkpoint

```powershell
$API_URL = "https://" + (az containerapp show -n $APP -g $RG --query properties.configuration.ingress.fqdn -o tsv)
curl $API_URL/api/
```
You should see the same JSON welcome message as your local backend — except this one is now running on the public internet.

---

## Module 8: Deploy the Frontend to Azure

### Step 8.1 — Get the deployment token

```powershell
$SWA_TOKEN = az staticwebapp secrets list -n $SWA -g $RG --query properties.apiKey -o tsv
```

> **Concept Explainer — Deployment Token**
> This is a secret credential specifically scoped to *deploying files to this one Static Web App* — much narrower than a full Azure login. It's the kind of credential you're comfortable handing to an automated tool (like the SWA CLI, or later, GitHub Actions) without worrying it could be used to, say, delete your entire subscription.

### Step 8.2 — Build the frontend for production

```powershell
cd frontend
$env:REACT_APP_BACKEND_URL = $API_URL
yarn build
```

> **Concept Explainer — Development build vs Production build**
> `yarn start` (Module 3) runs a development server: unoptimized, includes helpful error overlays, rebuilds instantly on save. `yarn build` produces a **production build**: minified (whitespace and unnecessary characters stripped to reduce file size), optimized JavaScript/CSS bundled into a `build/` folder — real, final files meant to be uploaded to a real server, not run locally.
>
> Setting `REACT_APP_BACKEND_URL` before running `yarn build` matters because of something specific to Create React App: environment variables starting with `REACT_APP_` are **baked directly into the JavaScript files at build time** — they cannot be changed afterward by editing a config file on the server, the way backend environment variables can. If you need to point the frontend at a different backend URL, you must rebuild it.

### Step 8.3 — Deploy the built files

```powershell
npx @azure/static-web-apps-cli deploy ./build --deployment-token $SWA_TOKEN --env production
```

### ✅ Verification checkpoint

```powershell
$SWA_URL = "https://" + (az staticwebapp show -n $SWA -g $RG --query defaultHostname -o tsv)
```
Open `$SWA_URL` in your browser. You should see the full application, now talking to your Azure-hosted backend instead of `localhost`. Update the backend's CORS setting to allow this real frontend URL:
```powershell
az containerapp update -n $APP -g $RG --set-env-vars CORS_ORIGINS=$SWA_URL FRONTEND_URL=$SWA_URL DB_NAME=coaching_academy ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=changeme MONGO_URL=secretref:mongo-url JWT_SECRET=secretref:jwt-secret AZURE_STORAGE_CONNECTION_STRING=secretref:storage-conn ACADEMY_NAME="My Test Academy"
```
(Remember the "replaces the whole list" gotcha from Module 7 — that's why every variable is repeated here, not just the two that changed.)

---

## Module 9: Set Up CI/CD With GitHub Actions

### What we're doing and why

So far, every deployment has been a manual command you typed. Real teams don't want to do this by hand every time — CI/CD automates it: push code, and within minutes it's live, with no human running deployment commands.

### Step 9.1 — Understand the workflow files

Open [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml):

```yaml
name: Deploy backend to Azure Container Apps

on:
  push:
    branches: [main]
    paths:
      - "backend/**"
      - ".github/workflows/deploy-backend.yml"
  workflow_dispatch:

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Azure login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - name: Build image in ACR
        run: |
          az acr build --registry $ACR_NAME --image coaching-backend:${{ github.sha }} ./backend
      - name: Update Container App
        run: |
          az containerapp update --name $CONTAINER_APP --resource-group $RESOURCE_GROUP --image $ACR_NAME.azurecr.io/coaching-backend:${{ github.sha }}
```

| Part | Meaning |
|---|---|
| `on: push: branches: [main], paths: ["backend/**"]` | Only runs automatically when someone pushes to `main` **and** the change touches something inside `backend/` |
| `workflow_dispatch:` | Also allows manually triggering this workflow from GitHub's web UI, without needing a matching push |
| `runs-on: ubuntu-latest` | GitHub provides a fresh, temporary Linux virtual machine to run these steps on — a "runner" |
| `uses: actions/checkout@v4` | A pre-built, reusable **Action** that downloads your repo's code onto the runner |
| `uses: azure/login@v2` | Another reusable Action, this one authenticates to Azure using the credentials in the `AZURE_CREDENTIALS` secret |
| `${{ github.sha }}` | The unique commit hash of the code being deployed — used as a specific, traceable image tag instead of always overwriting `latest` |

### Step 9.2 — Create a Service Principal for GitHub Actions

```powershell
$SUB = az account show --query id -o tsv
az ad sp create-for-rbac --name coaching-academy-deploy --role contributor `
  --scopes "/subscriptions/$SUB/resourceGroups/$RG" `
  --json-auth
```

> **Concept Explainer — Service Principal**
> A Service Principal is a machine identity in Azure Active Directory — think of it as a robot's own restricted user account, with its own credentials, that only GitHub Actions will ever use. `--role contributor --scopes "/subscriptions/.../resourceGroups/coaching-academy-rg"` deliberately limits what this identity can do: it can create/modify/delete resources **only inside this one resource group**, nothing else in the Azure subscription. This is the security principle of **least privilege** — grant only the access actually needed, nothing more.

Copy the entire JSON output — you'll paste it as a GitHub secret next.

### Step 9.3 — Configure GitHub Secrets and Variables

Using the GitHub CLI:
```powershell
gh secret set AZURE_CREDENTIALS --repo YOUR_USERNAME/coaching-academy
# (paste the JSON from step 9.2 when prompted, then Ctrl+Z then Enter on Windows, or Ctrl+D on Mac/Linux)

gh secret set AZURE_STATIC_WEB_APPS_API_TOKEN --repo YOUR_USERNAME/coaching-academy --body "$SWA_TOKEN"

gh variable set ACR_NAME --repo YOUR_USERNAME/coaching-academy --body $ACR
gh variable set AZURE_RESOURCE_GROUP --repo YOUR_USERNAME/coaching-academy --body $RG
gh variable set CONTAINER_APP_NAME --repo YOUR_USERNAME/coaching-academy --body $APP
gh variable set REACT_APP_BACKEND_URL --repo YOUR_USERNAME/coaching-academy --body $API_URL
gh variable set REACT_APP_ACADEMY_NAME --repo YOUR_USERNAME/coaching-academy --body "My Test Academy"
```

Or, without the CLI: go to your repo on GitHub → **Settings → Secrets and variables → Actions**, and add each one through the web UI.

### Step 9.4 — Trigger it

Make any small change inside `backend/` or `frontend/`, then:
```powershell
git add .
git commit -m "Test CI/CD pipeline"
git push origin main
```

### ✅ Verification checkpoint

```powershell
gh run list --repo YOUR_USERNAME/coaching-academy
```
You should see a workflow run appear with status `in_progress`, then eventually `completed` / `success`. Watch it live:
```powershell
gh run watch --repo YOUR_USERNAME/coaching-academy
```

---

## Module 10: End-to-End Verification Checklist

Run through this list and confirm every item before considering your deployment complete:

- [ ] `curl $API_URL/api/` returns the welcome JSON message
- [ ] Visiting `$SWA_URL` in a browser loads the app's landing page
- [ ] You can log in as the seeded admin
- [ ] Browser DevTools → Network tab shows successful (status 200) requests from the frontend to `$API_URL`
- [ ] No CORS errors appear in the browser console
- [ ] Uploading a file (e.g. a course thumbnail) succeeds — confirms Azure Blob Storage is correctly wired
- [ ] `gh run list` shows at least one successful workflow run for both `deploy-backend.yml` and `deploy-frontend.yml`
- [ ] Pushing a small, harmless code change triggers an automatic redeploy without you running any `az` command manually

---

## 14. Troubleshooting Guide

| Symptom | Likely Cause | Fix |
|---|---|---|
| `curl: (7) Failed to connect to localhost port 8001` | Backend isn't running, or crashed on startup | Check the terminal running `uvicorn` for a Python traceback. Common cause: MongoDB isn't running yet — start the Docker container first |
| Backend crashes with `KeyError: 'MONGO_URL'` | `.env` file missing or not in the `backend/` folder | Confirm `backend/.env` exists and `MONGO_URL` is spelled exactly right (case-sensitive) |
| Browser console shows a CORS error (`No 'Access-Control-Allow-Origin' header`) | The frontend's URL isn't in the backend's `CORS_ORIGINS` | Update `CORS_ORIGINS` (locally: in `backend/.env`; in Azure: via `az containerapp update --set-env-vars`) to include the exact origin shown in the browser's address bar (including `http://` or `https://` and the port) |
| `docker: error during connect... dockerDesktopLinuxEngine` | Docker Desktop application isn't running | Launch Docker Desktop and wait for it to fully start (the whale icon in your system tray stops animating) before running `docker` commands |
| `Something is already running on port 3000` | Another program on your laptop already uses that port | Either stop that program, or run this project's frontend on a different port by setting `PORT=3001` in `frontend/.env` |
| `AADSTS50076: ... must use multi-factor authentication` during `az login` | Your Azure account's tenant requires MFA, but the login flow didn't complete it interactively | Run `az login --tenant YOUR_TENANT_ID` to force a fresh interactive browser login, or use `az login --use-device-code` for a device-code flow that reliably completes MFA |
| Azure CLI misinterprets `/subscriptions/...` as a Windows file path (Git Bash only) | Git Bash on Windows auto-converts arguments that look like POSIX paths | Prefix the command with `MSYS_NO_PATHCONV=1`, e.g. `MSYS_NO_PATHCONV=1 az ad sp create-for-rbac ...` |
| GitHub Actions frontend build fails with `Failed to compile` / ESLint errors, but `yarn build` works fine locally | GitHub's runners set `CI=true`, which makes Create React App treat any ESLint *warning* as a hard build *error* | Add `CI: false` to the deploy step's `env:` block in `deploy-frontend.yml` — see this exact fix already applied in this project's workflow file |
| File upload fails with "Connection string missing required connection details" | The `AZURE_STORAGE_CONNECTION_STRING` secret is empty, malformed, or wasn't actually applied | Re-fetch it fresh with `az storage account show-connection-string`, re-set it with `az containerapp secret set`, then restart the active revision so the new value is actually picked up by a running container |
| `ServerSelectionTimeoutError` connecting to MongoDB Atlas | Your current IP isn't in Atlas's Network Access allow-list | Add your IP (or `0.0.0.0/0` for convenience during development) under Atlas → Network Access |
| Updating one environment variable on a Container App seems to have deleted several others | `az containerapp update --set-env-vars` **replaces the entire list**, it does not merge | Always pass the complete set of env vars you want present, every single time you run this command |
| `401 Unauthorized` on every API request even though you just logged in | The JWT isn't being attached to requests, or `JWT_SECRET` differs between when the token was issued and now | Check the Axios interceptor in `frontend/src/lib/api.js` is wired up; check `JWT_SECRET` wasn't accidentally changed on the backend (which invalidates all previously-issued tokens) |

---

## 15. Interview Preparation

For each topic, three tiers of questions: **(a) basic definition**, **(b) applied to this project**, **(c) scenario/troubleshooting**. Model answers are written so you can speak from genuine hands-on experience with this exact codebase.

### Git & GitHub

**(a) What is Git, and how is it different from GitHub?**
> Git is version control software that runs locally and tracks every change to a set of files over time. GitHub is a cloud service that hosts Git repositories and adds collaboration tools on top — pull requests, issue tracking, and automation via GitHub Actions. Git works completely fine without GitHub (you could push to any Git server); GitHub is one popular *hosting* choice for Git repos.

**(b) How did you use Git/GitHub in this project?**
> I cloned the repository, made changes locally, and used `git add`/`git commit`/`git push` to update the `main` branch. Because this repo has GitHub Actions workflows configured to trigger on pushes to `main` that touch `backend/` or `frontend/`, every push I made automatically kicked off a deployment — so Git wasn't just for saving code, it was the trigger for the entire CI/CD pipeline.

**(c) You pushed a change and nothing deployed. How do you debug that?**
> First, I'd check `git log` to confirm the commit actually landed on `main` and check `git status`/`git diff` to see if the change actually touched files under the path filters in the workflow (`backend/**` or `frontend/**` in this project's `on: push: paths:` config) — a change outside those paths won't trigger anything. Then I'd run `gh run list` to see if a workflow run exists at all; if none appears, the trigger conditions weren't met; if one appears but failed, I'd inspect its logs with `gh run view <id> --log-failed`.

---

### REST APIs & HTTP

**(a) What is a REST API?**
> An API following REST conventions: each resource (a course, a user) has its own URL, and standard HTTP methods express intent — `GET` to read, `POST` to create, `PUT`/`PATCH` to update, `DELETE` to remove. Responses are typically JSON.

**(b) Give an example of a REST endpoint in this project and explain its parts.**
> `POST /api/payments/razorpay/create-order` in `backend/routers/payments.py`. `POST` because it creates something (a payment order) rather than just reading data. It expects a JSON body (validated by a Pydantic model), and requires the caller to be authenticated (enforced via a FastAPI `Depends(get_current_user)` dependency) since only logged-in students can initiate a payment.

**(c) A frontend call to your API returns a 500 error. Walk me through your debugging process.**
> 500 means the server itself crashed while handling the request, as opposed to a 4xx which means the client sent something invalid. I'd check the backend's terminal/logs (or `az containerapp logs show` in Azure) for a Python traceback, which pinpoints the exact line that failed. I'd also check whether the request body actually matches what the Pydantic model expects, since a mismatch that FastAPI doesn't catch automatically can sometimes surface as an unhandled exception deeper in the route logic.

---

### Authentication, JWT & Password Security

**(a) What is a JWT and why use it instead of just storing "logged in" in a database?**
> A JWT (JSON Web Token) is a digitally signed token containing claims about a user (their ID, role, expiry time). Because it's signed with a secret key, the server can verify it's authentic without needing to look anything up in a database on every single request — the token itself carries the proof. This makes authentication checks fast and lets the backend stay "stateless" (not needing to remember every active session in memory).

**(b) Walk me through exactly how login works in this project.**
> The frontend POSTs email/password to `/api/auth/login`. The backend looks up the user by email in MongoDB, and uses `bcrypt.checkpw()` to compare the submitted password against the stored hash — never the plain password itself, since only the hash is ever stored. If it matches, `create_access_token()` in `auth_utils.py` builds a JWT containing the user's ID, email, and role, signed with `JWT_SECRET`, and returns it to the frontend. The frontend stores it in `localStorage` and an Axios interceptor in `lib/api.js` automatically attaches it as an `Authorization: Bearer <token>` header on every subsequent request. The backend's `get_current_user()` dependency decodes and verifies that header on every protected route.

**(c) A user reports they were suddenly logged out of the app for no reason. What could cause this, given how this system works?**
> A few possibilities I'd check, from most to least likely: (1) the JWT reached its expiry time (this project issues tokens valid for 7 days), which is expected behavior, not a bug; (2) `JWT_SECRET` was changed/rotated on the backend since the token was issued — every previously-issued token instantly becomes invalid because it can no longer be verified against the new secret, which is exactly what happens if you regenerate that secret during a deployment; (3) the user's `localStorage` was cleared (private browsing, cache clear); (4) the user document was deleted, so `get_current_user()`'s lookup fails even with a valid token signature.

---

### Databases & MongoDB

**(a) What is a NoSQL database, and how does it differ from a traditional (SQL) database?**
> Traditional relational (SQL) databases enforce a rigid schema — tables with fixed columns, and relationships defined via foreign keys. NoSQL databases like MongoDB store flexible, JSON-like documents where different documents in the same collection can have different fields, and related data can be nested directly inside a document instead of split across tables.

**(b) Give an example of how this project uses MongoDB's flexibility.**
> A `courses` document embeds its entire structure — sections, which contain sub-topics, which contain lessons — as nested arrays directly inside the course document, rather than as separate `sections`/`lessons` tables joined by foreign keys. This makes fetching a full course (with everything a student needs to see it) a single query, at the cost of making some updates (like reordering one lesson) need to modify the whole nested structure.

**(c) Your app is suddenly running very slowly on a specific query. How would you investigate?**
> I'd first check whether that query has a supporting index — `server.py`'s startup function already creates several explicit indexes (e.g. a unique index on `users.email`); a query filtering on a field with no index forces MongoDB to scan every document in the collection ("a full collection scan"), which gets slower as data grows. I'd use MongoDB's `explain()` on the query to see its actual execution plan, then consider adding an index on the field(s) being filtered/sorted on.

---

### Docker & Containers

**(a) What is Docker, and what problem does it solve?**
> Docker packages an application together with everything it needs to run (exact language runtime version, libraries, OS-level dependencies) into a portable image. It solves the "works on my machine" problem — an app that runs correctly inside a Docker container behaves identically regardless of what's installed on the host machine it's running on.

**(b) Why did you containerize the backend but not the frontend in this project?**
> The backend is a long-running server process (Uvicorn, listening on a port, connecting to a database) — it needs an actual runtime environment, which is exactly what a container provides. The frontend, after `yarn build`, is just static files (HTML/CSS/JS) with no server-side logic — it doesn't need a running process at all, just a place to host files, which Azure Static Web Apps provides directly without needing a container.

**(c) Your Docker container builds successfully but fails immediately when you try to run it. What's your debugging approach?**
> First, `docker logs <container-name>` (or in Azure, `az containerapp logs show`) to see what the container printed before it exited — usually a Python traceback pointing at the exact failure. Common causes I'd check first: a required environment variable is missing (the container has no `.env` file, so anything not explicitly passed via `-e` or Azure secrets simply won't exist), or the container can't reach a dependency like the database (e.g. using `localhost` instead of `host.docker.internal` when trying to reach a database running on the host machine, or an unreachable Atlas connection string).

---

### Cloud Computing & Azure

**(a) What is cloud computing?**
> Renting computing resources — servers, storage, databases — from a provider over the internet, paying for what you use, instead of buying and maintaining your own physical hardware.

**(b) Why did you choose Azure Container Apps for the backend instead of, say, a traditional virtual machine?**
> Container Apps is a serverless container platform — Azure handles the underlying servers, scaling, HTTPS certificates, and restarts automatically. I configured it with `--min-replicas 0`, meaning it scales down to zero running containers (and zero cost for compute) when nobody's using the app, and automatically starts one back up on the next incoming request. Managing that scaling behavior manually on a traditional VM would require significantly more setup (a load balancer, auto-scaling rules, manual OS patching).

**(c) Your Container App is returning errors intermittently, but only right after periods of no traffic. What's likely happening, and how would you confirm it?**
> That pattern strongly suggests a "cold start" — because `--min-replicas 0` allows the app to scale to zero, the very first request after idle time has to wait for a new container to actually start (pulling the image, running startup code) before it can respond, which can cause that first request to be slow or, if a client's timeout is too short, appear to fail. I'd confirm by checking `az containerapp revision list` for replica count history around the failure times, and consider raising `--min-replicas` to 1 if this cold-start latency is unacceptable for the use case, accepting a small always-on cost in exchange.

---

### CI/CD & GitHub Actions

**(a) What is CI/CD?**
> Continuous Integration / Continuous Deployment — automatically building, testing, and deploying code the moment it's pushed to a shared repository, rather than a person manually running deployment commands.

**(b) Explain, step by step, what happens when you push a backend change to this project's `main` branch.**
> GitHub detects the push touches files under `backend/`, matching the path filter in `deploy-backend.yml`, and starts that workflow on a fresh runner. The workflow checks out the code, authenticates to Azure using the `AZURE_CREDENTIALS` secret (a Service Principal scoped only to this project's resource group), runs `az acr build` to build a new Docker image directly from the current code in Azure's cloud build service, and finally runs `az containerapp update` to point the live Container App at that new image. The whole thing typically finishes in one to a few minutes with zero manual steps.

**(c) A GitHub Actions workflow that used to work suddenly starts failing on every push. How would you triage it?**
> I'd start with `gh run list` to see the failure, then `gh run view <id> --log-failed` to get the actual error output rather than guessing. From there it's usually one of a few categories: an expired or revoked credential (the Service Principal's secret, or a GitHub secret that got overwritten incorrectly), a change in the underlying cloud resource (e.g. someone deleted the Container App outside of the pipeline), or — as happened in this exact project — an environment difference between local and CI (GitHub's runners set `CI=true`, which changed how strictly Create React App treated ESLint warnings, breaking a build that worked fine locally).

---

### Payment Integration (Razorpay)

**(a) At a basic level, how does an online payment integration work?**
> The merchant's backend asks the payment provider to create an "order" for a specific amount. The provider's checkout widget (loaded on the frontend) collects the customer's payment details directly — the merchant's own servers never see raw card numbers. After payment, the provider sends back a confirmation, which the merchant's backend must independently verify before treating the order as paid.

**(b) Why does this project verify a cryptographic signature after payment instead of just trusting the frontend's "payment succeeded" message?**
> Because a request straight to the backend's API can be faked by anyone — there's nothing stopping a malicious user from calling `/api/payments/razorpay/verify` with made-up data claiming they paid, if the backend just trusted it. Razorpay signs its genuine payment confirmation with an HMAC computed using a secret key (`RAZORPAY_KEY_SECRET`) that only Razorpay and our backend know. The backend recomputes that signature itself and compares it — only a request that actually came from Razorpay, carrying data Razorpay itself generated, will produce a matching signature.

**(c) A student says they paid but their enrollment never appeared. How would you investigate, given this system's design?**
> I'd first check the `payments` collection in MongoDB for a record matching their attempted transaction — if none exists, the `/verify` call likely never completed (network failure between checkout and the verify call, or the signature check failed and the backend rejected it). I'd also check Razorpay's own dashboard for the transaction to see if the charge actually succeeded on their end — it's possible the money was captured by Razorpay but the verification round-trip to our backend never completed, which is exactly the kind of edge case this two-step "create order, then verify" design exists to make detectable and reconcilable, rather than blindly trusting a single client-reported "success."

---

## 16. Presenting This Project in Interviews & On Your Resume

### Skills demonstrated by this project

- Full-stack web development (React frontend, Python/FastAPI backend, REST API design)
- NoSQL database design and querying (MongoDB)
- Authentication & security (JWT, password hashing, role-based access control, CORS)
- Containerization (Docker: writing a Dockerfile, building/running images)
- Cloud infrastructure (Microsoft Azure: Container Apps, Static Web Apps, Blob Storage, Container Registry — provisioned via CLI, not just clicking through a dashboard)
- CI/CD pipeline design (GitHub Actions: multi-job workflows, secrets management, path-based triggers)
- Third-party API integration (payment gateway with cryptographic verification, transactional email, WhatsApp messaging, video conferencing)
- Environment-based configuration management (the same codebase running correctly across local, and cloud environments)
- Debugging real production issues (cold starts, CORS, CI environment differences, credential scoping)

### Sample resume bullet points

> *Adapt these to your actual level of hands-on involvement — don't claim work you didn't personally do.*

- "Deployed a full-stack coaching platform (React + FastAPI + MongoDB) to Microsoft Azure using Docker containers, Azure Container Apps, and Azure Static Web Apps, provisioned entirely via Azure CLI."
- "Built a CI/CD pipeline with GitHub Actions that automatically builds and deploys backend/frontend changes to Azure on every push to main, using a least-privilege Service Principal for authentication."
- "Implemented JWT-based authentication with bcrypt password hashing and role-based access control (student/teacher/admin) across a 17-router REST API."
- "Diagnosed and fixed a production file-upload failure caused by a malformed cloud storage connection string, and a CI-only build failure caused by an environment difference in ESLint strictness between local and GitHub-hosted runners."

### 2-minute project walkthrough script

> Use this as a starting point, not something to memorize word-for-word — speak naturally.

> "This is a coaching platform I built and deployed — think of it like a mini Udemy for exam prep. It's a full-stack app: a React single-page application on the frontend, and a Python FastAPI REST API on the backend, backed by MongoDB.
>
> On the architecture side, the frontend and backend are two completely separate deployments — the frontend is a static site served from Azure Static Web Apps' global CDN, and the backend runs as a Docker container on Azure Container Apps, which auto-scales — including scaling down to zero when there's no traffic, to save cost. They talk to each other purely over a REST API, with JWT tokens handling authentication between requests.
>
> I set up the entire cloud infrastructure myself using the Azure CLI — resource group, container registry, the Container Apps environment, blob storage for file uploads — and wired up CI/CD with GitHub Actions, so any push to main that touches the backend or frontend code automatically rebuilds and redeploys within a couple of minutes, with no manual server access needed.
>
> Along the way I hit and fixed some real production issues — for example, a file upload feature that broke because a storage connection string secret got malformed during setup, and a CI pipeline that failed only in GitHub's environment because of a strictness setting difference in the build tooling that didn't show up locally. Debugging those taught me a lot about the gap between 'it works on my machine' and 'it works reliably in an automated cloud pipeline.'"

### Master list of interview questions (quick revision)

**Basic definitions:**
1. What is Git, and how is it different from GitHub?
2. What is a REST API?
3. What is a JWT?
4. What is a NoSQL database?
5. What is Docker, and what problem does it solve?
6. What is cloud computing?
7. What is CI/CD?
8. At a basic level, how does an online payment integration work?

**Applied to this project:**
9. How did you use Git/GitHub in this project?
10. Give an example of a REST endpoint in this project and explain its parts.
11. Walk me through exactly how login works in this project.
12. Give an example of how this project uses MongoDB's flexibility.
13. Why did you containerize the backend but not the frontend?
14. Why did you choose Azure Container Apps for the backend?
15. Explain, step by step, what happens when you push a backend change to main.
16. Why does this project verify a cryptographic signature after payment?

**Scenario / troubleshooting:**
17. You pushed a change and nothing deployed. How do you debug that?
18. A frontend call to your API returns a 500 error. Walk me through your debugging process.
19. A user reports they were suddenly logged out for no reason. What could cause this?
20. Your app is suddenly running very slowly on a specific query. How would you investigate?
21. Your Docker container builds successfully but fails immediately when you try to run it. What's your approach?
22. Your Container App is returning errors intermittently, only right after idle periods. What's likely happening?
23. A GitHub Actions workflow that used to work suddenly fails on every push. How would you triage it?
24. A student says they paid but their enrollment never appeared. How would you investigate?

Good luck — you now have hands-on experience with the exact same tools and workflows used by professional engineering teams in the industry.
