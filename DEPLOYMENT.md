# Deployment Guide

Stack: **React (CRA)** → Azure Static Web Apps · **FastAPI (Python)** → Azure Container Apps · **MongoDB Atlas** (M0 free) · **Azure Blob Storage** for uploads · **GitHub Actions** for CI/CD.

## 🚀 Live deployment (already provisioned)

| Resource | Value |
|---|---|
| Frontend (Static Web App) | https://yellow-dune-0c8966000.7.azurestaticapps.net |
| Backend API (Container App) | https://coaching-api.blueglacier-f9e6d79e.centralindia.azurecontainerapps.io |
| Resource group | `coaching-academy-rg` (Central India) |
| Container registry | `coachingacademyacr` |
| Storage account | `coachingacademyfiles` |
| Container Apps environment | `coaching-env` |
| MongoDB | Atlas M0 cluster `m0-cluster-mongodb` |
| Admin login | `admin@rgpacademy.com` — password stored only as the Container App secret `admin-password`; **rotate it** (see below) before sharing this app with anyone |

**Manual redeploy after a code change:**

```powershell
# Backend
az acr build --registry coachingacademyacr --image coaching-backend:v2 ./backend
az containerapp update -n coaching-api -g coaching-academy-rg --image coachingacademyacr.azurecr.io/coaching-backend:v2

# Frontend — the prod API URL must be exported in the shell (craco.config.js loads
# frontend/.env via dotenv BEFORE react-scripts' own env chain, so .env.production.local
# is silently ignored; an already-exported shell var wins instead)
cd frontend
$env:REACT_APP_BACKEND_URL = "https://coaching-api.blueglacier-f9e6d79e.centralindia.azurecontainerapps.io"
yarn build
npx @azure/static-web-apps-cli deploy ./build --deployment-token <SWA_TOKEN> --env production
```

Set up the GitHub Actions workflows (section 3 below) to automate this on every push instead.

**Rotate the admin password:**

```powershell
$NEW_PW = python -c "import secrets; print(secrets.token_urlsafe(16))"
az containerapp secret set -n coaching-api -g coaching-academy-rg --secrets "admin-password=$NEW_PW"
az containerapp update -n coaching-api -g coaching-academy-rg --revision-suffix rot1
$NEW_PW   # save this somewhere safe, then close the terminal
```
Note: `ADMIN_PASSWORD` only takes effect via `seed.py` on first ever startup (when no admin exists yet). To change the password of the *existing* admin account, log in as admin and use the app's own change-password/user-management flow instead.

---

## 1. Run locally

Prereqs: Python 3.12+, Node 20+, yarn (`npm i -g yarn`), Docker Desktop.

```powershell
# 1. MongoDB (Docker, persistent volume, auto-restarts with Docker)
docker start coaching-mongo   # first time: docker run -d --name coaching-mongo -p 27017:27017 -v coaching_mongo_data:/data/db --restart unless-stopped mongo:7

# 2. Backend (uses backend/.env — see backend/.env.example)
cd backend
python -m venv .venv          # first time only
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn server:app --host 0.0.0.0 --port 8001

# 3. Frontend (uses frontend/.env; runs on :3001 — :3000 is taken by Grafana)
cd frontend
yarn install                  # first time only
yarn start
```

Open http://localhost:3001 — seeded admin: value of `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `backend/.env`.

File uploads land on local disk (`backend/uploads/`) when `AZURE_STORAGE_CONNECTION_STRING` is unset.

---

## 2. One-time Azure setup (az CLI)

Login and pick names (all lowercase; ACR name must be globally unique, alphanumeric only):

```powershell
az login
$RG        = "coaching-academy-rg"
$LOC       = "centralindia"           # pick your region
$ACR       = "coachingacademyacr"     # must be globally unique
$ENVNAME   = "coaching-env"
$APP       = "coaching-api"
$STORAGE   = "coachingacademyfiles"   # must be globally unique
$SWA       = "coaching-frontend"

az group create -n $RG -l $LOC
```

### 2a. MongoDB Atlas (free M0)

Simplest path — create it directly at https://cloud.mongodb.com (the Azure Marketplace listing just wraps the same signup with pay-as-you-go billing):Coaching App

1. Create a free *0**M* cluster, cloud provider **Azure**, region closest to `$LOC`.
2. Database Access → create a DB user (username + strong password).
3. Network Access → **Allow access from anywhere (0.0.0.0/0)** — Container Apps consumption has no fixed egress IP on the free tier.
4. Copy the connection string, e.g.
   `mongodb+srv://USER:PASS@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`

### 2b. Blob Storage for uploads

```powershell
az storage account create -n $STORAGE -g $RG -l $LOC --sku Standard_LRS --kind StorageV2
$STORAGE_CONN = az storage account show-connection-string -n $STORAGE -g $RG -o tsv
```

The backend creates the container (default name `uploads`, override with `AZURE_STORAGE_CONTAINER`) automatically on first upload.

### 2c. Container registry + Container Apps environment

```powershell
az acr create -n $ACR -g $RG --sku Basic --admin-enabled true
az extension add --name containerapp --upgrade
az containerapp env create -n $ENVNAME -g $RG -l $LOC
```

### 2d. Build & deploy the backend container

```powershell
# Build the image in the cloud (no local docker needed)
az acr build --registry $ACR --image coaching-backend:v1 ./backend

# Generate a production JWT secret
$JWT = python -c "import secrets; print(secrets.token_urlsafe(48))"

az containerapp create -n $APP -g $RG --environment $ENVNAME `
  --image "$ACR.azurecr.io/coaching-backend:v1" `
  --registry-server "$ACR.azurecr.io" `
  --target-port 8001 --ingress external `
  --min-replicas 0 --max-replicas 2 `
  --cpu 0.5 --memory 1.0Gi `
  --secrets mongo-url="<ATLAS_CONNECTION_STRING>" jwt-secret="$JWT" storage-conn="$STORAGE_CONN" admin-password="<STRONG_ADMIN_PASSWORD>" `
  --env-vars MONGO_URL=secretref:mongo-url JWT_SECRET=secretref:jwt-secret AZURE_STORAGE_CONNECTION_STRING=secretref:storage-conn ADMIN_PASSWORD=secretref:admin-password `
    DB_NAME=coaching_academy ADMIN_EMAIL=admin@yourdomain.com `
    CORS_ORIGINS=https://PLACEHOLDER FRONTEND_URL=https://PLACEHOLDER `
    "ACADEMY_NAME=Rohini's Academy for Bio Exams"

# Note the API URL:
$API_URL = "https://" + (az containerapp show -n $APP -g $RG --query properties.configuration.ingress.fqdn -o tsv)
$API_URL
```

`--min-replicas 0` scales to zero when idle (free-ish; first request after idle takes a few seconds to cold-start). Verify: open `$API_URL/api/` — you should see the API welcome JSON.

### 2e. Static Web App (frontend)

```powershell
az staticwebapp create -n $SWA -g $RG -l $LOC --sku Free
$SWA_URL = "https://" + (az staticwebapp show -n $SWA -g $RG --query defaultHostname -o tsv)
$SWA_TOKEN = az staticwebapp secrets list -n $SWA -g $RG --query properties.apiKey -o tsv
$SWA_URL; $SWA_TOKEN
```

Now point the backend CORS at the real frontend URL:

```powershell
az containerapp update -n $APP -g $RG --set-env-vars "CORS_ORIGINS=$SWA_URL" "FRONTEND_URL=$SWA_URL"
```

### 2f. Optional integrations

Add the same way (as secrets + env vars) when ready: `RESEND_API_KEY`, `SENDER_EMAIL`, `ADMIN_NOTIFY_EMAIL`, `TWILIO_*`, `ZOOM_*`, `RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET` (use `rzp_live_*` keys).

---

## 3. CI/CD (GitHub → Azure)

Workflows are in `.github/workflows/`:

| Workflow | Trigger | Does |
|---|---|---|
| `deploy-backend.yml` | push to `main` touching `backend/**` | `az acr build` → `az containerapp update` |
| `deploy-frontend.yml` | push to `main` touching `frontend/**` | Builds CRA and uploads to Static Web Apps |

### GitHub repository → Settings → Secrets and variables → Actions

**Secrets:**

- `AZURE_CREDENTIALS` — service principal JSON:
  ```powershell
  $SUB = az account show --query id -o tsv
  az ad sp create-for-rbac --name coaching-deploy --role contributor --scopes "/subscriptions/$SUB/resourceGroups/$RG" --json-auth
  ```
  Paste the whole JSON output as the secret value.
- `AZURE_STATIC_WEB_APPS_API_TOKEN` — the `$SWA_TOKEN` from step 2e.

**Variables:**

- `ACR_NAME` = value of `$ACR`
- `AZURE_RESOURCE_GROUP` = value of `$RG`
- `CONTAINER_APP_NAME` = value of `$APP`
- `REACT_APP_BACKEND_URL` = value of `$API_URL` (no trailing slash)
- `REACT_APP_ACADEMY_NAME` = your academy display name

Push to `main` → both apps deploy automatically.

---

## 4. Production notes

- **Secrets live only in Container App secrets / GitHub secrets** — never in the repo. `backend/.env` is git-ignored and local-only.
- **`REACT_APP_*` values are public** (baked into the JS bundle). Backend URL and academy name only — never keys.
- **Atlas M0 limits**: 512 MB storage, shared CPU. Upgrade to M2/M10 when you outgrow it; only the `MONGO_URL` secret changes.
- **Scale-to-zero cold starts**: set `--min-replicas 1` (~small monthly cost) if the first-request delay bothers you.
- **Custom domain**: both Static Web Apps and Container Apps support custom domains + free managed TLS (`az staticwebapp hostname set`, `az containerapp hostname add`).
- **Legacy uploads**: files in `backend/uploads/` from the old platform are served as a read-only fallback; new uploads go to Blob Storage.
