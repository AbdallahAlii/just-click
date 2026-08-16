# Production hosting: seed, workers, and chatbot index

Use this checklist when hosting JustClick on a VPS (for example VPSDime).

**You are correct:** if the long-running workers are not running in production, emails stay in `email_outbox`, push stays in `push_outbox`, and new materials will not become usable in JustClick AI until they are indexed.

This architecture intentionally uses **separate worker processes** (common production pattern: API + background workers). You do **not** need one mega-command that does everything. Prefer **systemd** (or Supervisor/PM2) so each worker restarts on reboot and on crash.

All commands below assume:

```bash
cd /path/to/just-click/backend
source .venv/bin/activate   # or use .venv/bin/python directly
```

Set `CMCP_SKIP_CHATBOT_WARMUP=1` on API/workers that should not load the chatbot model at startup (email/push workers).

---

## 1. First-time deploy order

1. Configure `.env` (DB, SMTP, `APP_BASE_URL` / `FRONTEND_BASE_URL`, secrets).
2. Run migrations.
3. Seed RBAC + university demo data (first time only, or when you intentionally refresh demo data).
4. Start API (gunicorn/uwsgi/systemd).
5. Start **three** long-running workers (email, notification/push, chatbot index).
6. After seed / bulk material import: queue reindex, then keep the chatbot index worker running.

### Migrations

```bash
cd /path/to/just-click/backend
CMCP_SKIP_CHATBOT_WARMUP=1 .venv/bin/flask --app cmcp db upgrade
# or your project's usual alembic/flask-migrate command
```

### Seed (first time / demo data)

Use Flask seed CLI (registered from `cmcp.cli.seed_command`):

```bash
cd /path/to/just-click/backend
# Full demo stack (core + RBAC + university materials/users)
CMCP_SKIP_CHATBOT_WARMUP=1 .venv/bin/flask --app cmcp seed all

# Or Jamhuriya university stack
CMCP_SKIP_CHATBOT_WARMUP=1 .venv/bin/flask --app cmcp seed university
```

University seed is **idempotent** (get-or-create by natural keys). Re-running should not explode duplicates; the first run may take time while storing mock files.

The demo dataset is intentionally small: about **8 courses** (1–2 per semester), **2 chapters per course**, **~6 materials per chapter**, plus a syllabus and at most **2 videos** university-wide. Target is **100–180** `edu_materials` rows (never mass-generated from large MP4s).

If production already has the old ~1,230-material seed, **do not** rely on `seed all` to shrink it. Use the explicit destructive reset first (never part of deploy):

```bash
# Preview scope (exits without deleting)
CMCP_SKIP_CHATBOT_WARMUP=1 .venv/bin/flask --app cmcp demo-reset

# After you have reviewed the printed tables/directories:
CMCP_SKIP_CHATBOT_WARMUP=1 .venv/bin/flask --app cmcp demo-reset --yes
CMCP_SKIP_CHATBOT_WARMUP=1 .venv/bin/flask --app cmcp seed all
```

After seed:

```bash
CMCP_SKIP_CHATBOT_WARMUP=1 PYTHONPATH=src .venv/bin/python scripts/reindex_existing_materials.py
CMCP_SKIP_CHATBOT_WARMUP=1 PYTHONPATH=src .venv/bin/python scripts/chatbot_index_worker.py --until-empty
```

`--until-empty` processes pending index jobs, releases the embedding model / Chroma client, and **exits**. An empty queue does not need a multi-GB worker sitting in RAM. Keep the systemd unit as-is for future uploads, or run `--until-empty` after bulk imports.

The long-running worker also unloads the model after `CHATBOT_INDEX_WORKER_IDLE_UNLOAD_SECONDS` (default 60) of an empty queue, then reloads on the next job.

---

## 2. Long-running workers (must stay up)

| Worker | Script | Why it must run |
|--------|--------|-----------------|
| **Email** | `scripts/email_worker.py` | Sends rows from `email_outbox` (verify, approval, material emails, **forgot-password**, admin broadcasts). Without it, emails are queued but never delivered. |
| **Push** | `scripts/notification_worker.py` | Sends mobile FCM from `push_outbox`. Without Firebase key, jobs may be skipped; worker can still run. |
| **Chatbot index** | `scripts/chatbot_index_worker.py` | Indexes material files into the AI store. Without it, new/updated materials are not usable in chat. |

### Recommended commands

```bash
# Terminal / systemd unit 1 — email
cd /path/to/just-click/backend
CMCP_SKIP_CHATBOT_WARMUP=1 .venv/bin/python scripts/email_worker.py

# Terminal / systemd unit 2 — push notifications
cd /path/to/just-click/backend
CMCP_SKIP_CHATBOT_WARMUP=1 .venv/bin/python scripts/notification_worker.py

# Terminal / systemd unit 3 — chatbot indexing
cd /path/to/just-click/backend
CMCP_SKIP_CHATBOT_WARMUP=1 .venv/bin/python scripts/chatbot_index_worker.py

# Optional one-shot drain (after seed / bulk import; exits when queue is empty)
CMCP_SKIP_CHATBOT_WARMUP=1 .venv/bin/python scripts/chatbot_index_worker.py --until-empty
CMCP_SKIP_CHATBOT_WARMUP=1 .venv/bin/python scripts/chatbot_index_worker.py --once
```

**Yes: run each as its own process.** That is correct for this codebase. Do not expect the Flask API alone to send email or index materials.

### Stable production management (recommended)

Use **systemd** with three services, for example:

- `justclick-email.service`
- `justclick-notification.service`
- `justclick-chatbot-index.service`

Each unit should:

- `WorkingDirectory=/path/to/just-click/backend`
- `Environment=CMCP_SKIP_CHATBOT_WARMUP=1`
- Load the same env file as the API
- `Restart=always`
- `ExecStart=/path/to/just-click/backend/.venv/bin/python scripts/<worker>.py`

Enable on boot:

```bash
sudo systemctl enable --now justclick-email justclick-notification justclick-chatbot-index
```

Supervisor or PM2 can do the same job. A single “all-in-one” process is optional and not required by the app.

---

## 3. One-shot / maintenance scripts

| Script | When |
|--------|------|
| `scripts/reindex_existing_materials.py` | After first seed or bulk import: queue all enabled materials that have files |
| `scripts/chatbot_index_worker.py` | Long-running queue consumer, or `--until-empty` / `--once` to drain and exit |
| `scripts/chatbot_index_worker.py --until-empty` | After seed/bulk import: process pending jobs, release RAM, exit |
| `scripts/diagnose_chatbot_index.py` | Inspect job counts, failures, embedding model |
| `scripts/reset_failed_index_jobs.py` | After fixing model/path issues, retry failed jobs |

Index flow:

```bash
# After seed / bulk import
python scripts/reindex_existing_materials.py
python scripts/chatbot_index_worker.py --until-empty

# Optional: keep running (systemd) so later uploads get indexed
python scripts/chatbot_index_worker.py
```

---

## 4. Environment variables that matter for hosting

```env
# Links inside emails (forgot password, verify, materials)
APP_BASE_URL=https://your-frontend-domain
FRONTEND_BASE_URL=https://your-frontend-domain

# SMTP (email_worker)
MAIL_PROVIDER=smtp
MAIL_FROM_EMAIL=...
MAIL_FROM_NAME=JustClick
SMTP_HOST=...
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=...
SMTP_PASSWORD=...

# Optional mobile push
FIREBASE_SERVER_KEY=...

# Password reset link lifetime (minutes)
PASSWORD_RESET_TOKEN_TTL_MINUTES=60

# Unload embedding model after the index queue has been empty this long
CHATBOT_INDEX_WORKER_IDLE_UNLOAD_SECONDS=60
```

Do **not** hard-code localhost in production. Workers and API both need the same DB and mail settings.

---

## 5. What happens if you forget a worker

| Missing worker | Symptom |
|----------------|---------|
| Email worker | Signup verify / approval / material / **forgot password** emails never arrive; rows stuck `pending` in `email_outbox` |
| Notification worker | Mobile push not delivered |
| Chatbot index worker | Materials exist in UI but AI chat has no indexed content for them |

In-app notifications (DB rows) do **not** need the email worker.

---

## 6. Minimal production process set

Always running:

1. Frontend (Next.js)
2. Backend API (Flask/gunicorn)
3. `email_worker.py`
4. `notification_worker.py` (optional until FCM is configured; still safe to run)
5. `chatbot_index_worker.py`

One-time / occasional:

- migrations (`flask --app cmcp db upgrade`)
- seed (`flask --app cmcp seed all`)
- shrink an old oversized demo (`flask --app cmcp demo-reset --yes`, then `seed all`) — **never** during deploy
- `reindex_existing_materials.py`
- `chatbot_index_worker.py --until-empty` after seed
- diagnose / reset failed index jobs

### FAQ

**Do I run email + notification workers each as their own process?**  
Yes. That is correct for this project.

**Can one command manage them?**  
Use systemd/Supervisor/PM2 to manage multiple processes — not a single Python script that merges all workers (unless you deliberately write a process supervisor). Keep them separate so one crash does not stop the others.

**If workers are not running, will emails send?**  
No. Forgot-password, verification, approval, and material emails stay pending in `email_outbox` until `email_worker.py` runs.

**If the chatbot index worker is not running?**  
New materials will not be indexed for AI chat until jobs are processed.

---

## Related docs

- `PRODUCTION_ENV_AND_DEPLOYMENT.md` — full DEV/PROD env, media, encryption, Nginx notes
- `NOTIFICATIONS_AND_WORKERS.md` — email/push details
- `CHATBOT.md` (if present) — indexing and RAG notes
