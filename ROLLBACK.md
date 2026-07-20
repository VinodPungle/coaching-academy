# Rollback runbook

This file documents how to roll the application back to a known-good
snapshot. It's a manual procedure — nothing here runs automatically.

## Current stable snapshot: `v1.0-stable` (2026-07-20)

What it covers, as of commit `b604354`:
- Course syllabus management (teacher upload/replace/delete, student view)
- Password-reset flow fixed and working
- DNS cutover complete — `www.bioexamprep.com` is the canonical production
  domain, backed by Azure (Static Web App + Container App + MongoDB Atlas)
- Show/hide password toggle on login, register, and reset-password pages

Three things were captured for this snapshot; each rolls back independently.

---

## 1. Application code — git tag

**Snapshot:** annotated tag `v1.0-stable` on commit `b604354`, pushed to
GitHub.

**To inspect what's tagged:**
```
git show v1.0-stable
```

**To roll the code back** (choose one):

- **Revert forward** (preferred — keeps history, safe if others have pulled):
  ```
  git revert --no-commit v1.0-stable..HEAD
  git commit -m "Revert to v1.0-stable"
  git push origin main
  ```
- **Hard reset** (only if you're sure no one else needs the commits being
  discarded — rewrites `main`'s history):
  ```
  git reset --hard v1.0-stable
  git push --force origin main
  ```

Either way, pushing to `main` triggers the existing GitHub Actions
workflows and redeploys both frontend (Static Web App) and backend
(Container App) automatically — no manual Azure steps needed for code.

**Faster backend-only rollback** (skips the ~2-3 min container build):
every backend deploy is already stored in Azure Container Registry, tagged
by commit SHA — but only for commits that touched `backend/**` (the deploy
workflow's path filter skips frontend-only commits, so the tag doesn't
necessarily match your latest `git log` entry). As of this snapshot, the
image matching the current production backend is tagged with the full SHA
of `e5a4b96` (the syllabus-management commit — the last one that changed
backend code as of `v1.0-stable`):
```
az containerapp update -n coaching-api -g coaching-academy-rg \
  --image coachingacademyacr.azurecr.io/coaching-backend:e5a4b961ae412f0fe5e78f83c78efb502e010f4c
```
Run `az acr repository show-tags -n coachingacademyacr --repository coaching-backend --orderby time_desc -o table`
to list all available image tags/SHAs if you need a different commit —
match against `git log -- backend/` to find which commit built which tag.

---

## 2. Database — MongoDB Atlas dump

**Snapshot:** full `mongodump` of the `coaching_academy` database, taken
2026-07-20, saved in two places:
- Local: `C:\Users\Vinod\coaching-academy-backups\v1.0-stable-2026-07-20\`
  (raw BSON) and `...-mongo-dump.zip` (zipped)
- Cloud: `backups/v1.0-stable-2026-07-20/mongo-dump.zip` in the
  `coachingacademyfiles` storage account (survives this machine)

Atlas's free M0 tier has **no automated backups** — this manual dump is
the only recovery point. Take a fresh one before any risky change:

```powershell
# from a folder containing the extracted MongoDB Database Tools
$mongo = az containerapp secret list -n coaching-api -g coaching-academy-rg --show-values -o json |
  ConvertFrom-Json | Where-Object { $_.name -eq 'mongo-url' } | Select-Object -ExpandProperty value
.\mongodump.exe --uri="$mongo" --db=coaching_academy --out="C:\Users\Vinod\coaching-academy-backups\<label>"
```

**To restore** (⚠️ `--drop` overwrites current data with the snapshot —
back up current state first if there's any doubt):
```powershell
.\mongorestore.exe --uri="$mongo" --db=coaching_academy --drop `
  "C:\Users\Vinod\coaching-academy-backups\v1.0-stable-2026-07-20\coaching_academy"
```

To restore from the cloud copy instead of local disk, download and unzip
`backups/v1.0-stable-2026-07-20/mongo-dump.zip` first (see storage account
access below).

**If MongoDB Database Tools aren't installed:** the Windows installer
(`winget install MongoDB.DatabaseTools`) requires admin elevation and can
hang waiting for a UAC prompt in non-interactive shells. Use the portable
ZIP instead — no install needed:
```
https://fastdl.mongodb.org/tools/db/mongodb-database-tools-windows-x86_64-100.17.0.zip
```
Extract it and run `mongodump.exe`/`mongorestore.exe` directly from
`<extracted>\bin\`.

---

## 3. Uploaded files — Blob storage

**Snapshot:** the `uploads` container was copied (server-side, in Azure)
into `backups/v1.0-stable-2026-07-20/uploads/...` in the same storage
account, preserving the original folder structure.

**Also enabled, as an extra safety net for *future* changes** (not specific
to this snapshot — protects everything going forward):
- Blob soft delete — 30 days
- Container soft delete — 30 days
- Blob versioning

This means any file overwritten or deleted after 2026-07-20 can be
recovered from its previous version/soft-deleted state for 30 days, even
without a manual snapshot.

**To restore the point-in-time snapshot** (copies the backup files back
over the live `uploads` container):
```powershell
$conn = az containerapp secret list -n coaching-api -g coaching-academy-rg --show-values -o json |
  ConvertFrom-Json | Where-Object { $_.name -eq 'storage-conn' } | Select-Object -ExpandProperty value
$env:AZURE_STORAGE_CONNECTION_STRING = $conn
az storage blob copy start-batch --source-container backups `
  --source-path "v1.0-stable-2026-07-20/uploads" `
  --destination-container uploads --pattern "*"
Remove-Item Env:\AZURE_STORAGE_CONNECTION_STRING
```

**To recover an individual soft-deleted/overwritten file** (no snapshot
needed, works for anything deleted in the last 30 days):
```powershell
az storage blob undelete --container-name uploads --name "<path/to/file>"
```
or browse previous versions in the Azure Portal → Storage account →
Containers → uploads → (blob) → Versions.

---

## Access needed to run any of this

- **GitHub**: push access to this repo.
- **Azure CLI**: `az login --tenant "5028b9e1-e6fd-4032-975c-6c4531e04f24" --scope "https://management.core.windows.net//.default"`
  (this tenant requires MFA on every fresh login).
- Resource group: `coaching-academy-rg`. Backend: `coaching-api`.
  Frontend: `coaching-frontend`. Storage account: `coachingacademyfiles`.

## Creating a new snapshot later

Repeat the same three steps with a new label (e.g. `v1.1-stable`,
or a date-based tag) — see [ARCHITECTURE.md](ARCHITECTURE.md) and
[TUTORIAL.md](TUTORIAL.md) for background on each Azure resource.
