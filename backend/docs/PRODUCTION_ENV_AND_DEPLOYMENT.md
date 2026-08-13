# JustClick production environment & VPSDime readiness

This document uses the **actual setting names** from the codebase.  
Do **not** use S3/MinIO/AWS object storage for JustClick media — keep the existing **local encrypted media** architecture.

Related: [PRODUCTION_WORKERS_AND_SEED.md](./PRODUCTION_WORKERS_AND_SEED.md), [NOTIFICATIONS_AND_WORKERS.md](./NOTIFICATIONS_AND_WORKERS.md)

---

## Architecture (DEV vs PROD)

### Development

| Layer | URL |
|-------|-----|
| Next.js frontend | `http://localhost:3000` |
| Flask backend | `http://127.0.0.1:7000` (or `http://localhost:7000`) |

Browser calls **only** same-origin Next routes:

```text
Browser → http://localhost:3000/api/backend/...
       → Next Route Handler (FLASK_ORIGIN)
       → http://127.0.0.1:7000/api/...
```

Media view/download also go through the proxy after URL normalization:

```text
/api/media/file/<key>  →  /api/backend/media/file/<key>  →  Flask /api/media/file/<key>
```

### Production (VPS + Nginx later)

| Layer | Typical |
|-------|---------|
| Public site | `https://your-domain.com` (Next.js) |
| Internal Flask | `http://127.0.0.1:7000` (not exposed publicly, or only via Nginx) |

Same proxy pattern:

```text
Browser → https://your-domain.com/api/backend/...
       → Next (FLASK_ORIGIN=http://127.0.0.1:7000)
       → Flask
```

Nginx can reverse-proxy `/` → Next and optionally `/api/` → Flask.  
If you keep the Next proxy, `FLASK_ORIGIN` should be the **internal** Flask URL.  
Do **not** put the VPS IP into application source code — only into env files.

---

## Frontend `.env`

File: `frontend/.env.local` (dev) or deployment env for Next.

| Variable | Server-only? | Rebuild needed? | DEV example | PROD example |
|----------|--------------|-----------------|-------------|--------------|
| `FLASK_ORIGIN` | **Yes** (never `NEXT_PUBLIC_`) | **Yes** (Next server reads at runtime for Route Handlers; rebuild/restart after change) | `http://127.0.0.1:7000` | `http://127.0.0.1:7000` (same machine) or internal Docker service URL |
| `NODE_ENV` | set by Next | — | `development` | `production` |

There are **no** `NEXT_PUBLIC_*` backend URL variables. Keep it that way.

### Frontend commands

```bash
cd frontend
# DEV
npm run dev

# PROD
npm run build
npm run start
```

---

## Backend `.env`

File: `backend/.env` (loaded via `CMCP_ENV_FILE` or default).

### Core / security (must stay stable)

| Variable | Notes |
|----------|-------|
| `ENV` | `development` locally; **`production`** on VPS (disables media debug route) |
| `SECRET_KEY` | Session + media URL signing. **Never rotate casually** without accepting session invalidation |
| `SECURITY_PASSWORD_SALT` | Keep stable |
| `ENCRYPTION_KEY` | Fernet key for uploaded files. **If this changes, existing media becomes unreadable**. Backup this value |

Generate Fernet key once:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Database

| Variable |
|----------|
| `DATABASE_HOST` |
| `DATABASE_PORT` |
| `DATABASE_USER` |
| `DATABASE_PASSWORD` |
| `DATABASE_NAME` |

### Frontend / email links

| Variable | Purpose |
|----------|---------|
| `APP_BASE_URL` | Preferred public frontend URL (password reset, verify, material emails) |
| `FRONTEND_BASE_URL` | Fallback if `APP_BASE_URL` unset |
| `PUBLIC_API_BASE_URL` | Optional. Only if you need **absolute** media API URLs. Leave empty to use portable relative `/api/media/...` paths (recommended with Next proxy) |
| `PASSWORD_RESET_TOKEN_TTL_MINUTES` | default `60` |
| `EMAIL_VERIFY_TOKEN_TTL_MINUTES` | default `30` |
| `CONTACT_NOTIFY_EMAIL` | Contact Us notify target (default `justclick.cmc@gmail.com`) |

DEV:

```env
APP_BASE_URL=http://localhost:3000
FRONTEND_BASE_URL=http://localhost:3000
PUBLIC_API_BASE_URL=
```

PROD:

```env
APP_BASE_URL=https://your-domain.com
FRONTEND_BASE_URL=https://your-domain.com
PUBLIC_API_BASE_URL=
```

### Sessions / CORS

| Variable | DEV | PROD |
|----------|-----|------|
| `SESSION_COOKIE_SECURE` | `false` | `true` (HTTPS) |
| `SESSION_COOKIE_SAMESITE` | `lax` | `lax` (same-site via Next proxy) |
| `SESSION_COOKIE_DOMAIN` | empty | empty or your domain if needed |
| `CORS_ALLOWED_ORIGINS` | `["http://localhost:3000"]` | `["https://your-domain.com"]` |
| `CROSS_SITE_COOKIES` | `false` | `false` unless frontend/API are different sites |

### SMTP (email worker)

| Variable |
|----------|
| `MAIL_PROVIDER` (`smtp`) |
| `MAIL_FROM_EMAIL` |
| `MAIL_FROM_NAME` |
| `SMTP_HOST` |
| `SMTP_PORT` |
| `SMTP_USE_TLS` |
| `SMTP_USERNAME` |
| `SMTP_PASSWORD` |

### Local encrypted media (no S3)

| Variable | DEV | PROD recommendation |
|----------|-----|---------------------|
| `MEDIA_BACKEND` | `local` | `local` |
| `LOCAL_MEDIA_ROOT` | `media` (resolves to `backend/media`) | **absolute** path e.g. `/var/lib/justclick/media` **or** keep `backend/media` on a persistent disk |
| `MEDIA_MAX_MB` | `100` | as needed |
| `MEDIA_ALLOWED_EXTS` | defaults in `media_config.py` | keep defaults unless you know you need more |

Relative `LOCAL_MEDIA_ROOT` is resolved against the **backend project root**, so API and chatbot worker share the same files even if cwd differs.

### Chatbot

Share with API + index worker: DB, `ENCRYPTION_KEY`, `LOCAL_MEDIA_ROOT` / `MEDIA_BACKEND`, Chroma/embedding settings, `DEEPSEEK_API_KEY`.

Workers should set `CMCP_SKIP_CHATBOT_WARMUP=1`.

### Push (optional)

| Variable |
|----------|
| `FIREBASE_SERVICE_ACCOUNT_JSON` or project’s FCM key env as already configured |

---

## Media flow (local encrypted storage)

```text
Admin uploads multipart file
  → Material API validates extension/size
  → Fernet encrypt (ENCRYPTION_KEY)
  → Store under LOCAL_MEDIA_ROOT/materials_files/<id>/file.<ext>.enc
  → PostgreSQL Material.file_url = /api/media/file/<key>   (portable path)
Student opens material
  → API returns read_url/download_url (relative or PUBLIC_API_BASE_URL)
  → Frontend rewrites to /api/backend/media/...
  → Next proxies to Flask
  → Permission check (or signed token)
  → Decrypt + stream
```

### View vs download

| Action | Endpoint | Notes |
|--------|----------|-------|
| View | `GET /api/media/file/<key>` | Requires Material READ session (or signed variant) |
| Download | `GET /api/media/download/<key>` | Attachment + download tracking via materials API |
| Signed | `GET /api/media/file-signed/<key>?t=...` | HMAC with `SECRET_KEY`, TTL clamped 30–3600s |

Knowing a storage key alone is not enough for session-protected routes. Signed URLs are capability tokens until expiry.

### Debug route

`GET /api/media/_debug/raw/<filename>` is registered **only** when:

- `MEDIA_BACKEND=local` **and**
- `ENV` is **not** `production` / `prod`

---

## Persistent media directory on VPS

Recommended:

```text
/var/lib/justclick/media
```

Or keep project-local:

```text
/path/to/just-click/backend/media
```

Requirements:

- Owned by the OS user that runs Flask + chatbot index worker (same user)
- Writable: `chmod 750` (or similar), not world-writable
- **Outside** any deploy step that deletes the app directory, **or** bind-mounted / separate volume
- Back up regularly together with PostgreSQL and `ENCRYPTION_KEY`

`.env`:

```env
MEDIA_BACKEND=local
LOCAL_MEDIA_ROOT=/var/lib/justclick/media
```

Processes that need access:

1. Backend API  
2. Chatbot index worker  

Email/notification workers do **not** need media disk access.

---

## Upload limits (current defaults)

From `media_config.py` / `validate_upload`:

- **Max size:** `MEDIA_MAX_MB` (default **100 MB**)
- **Extensions:** png, jpg, jpeg, webp, pdf, doc, docx, ppt, pptx, key, mp4, mkv, mov, csv, xlsx, xls  
- **MIME:** client-provided / guessed; extension allowlist is the hard gate  
- **Sanitization:** key segments sanitized; `..` and absolute keys rejected  
- Material types in product: PDF, SLIDES, DOC, VIDEO, LINK (links store URL, not encrypted upload)

---

## Workers (keep separate)

| Process | Command |
|---------|---------|
| API | gunicorn/uwsgi or `python server.py` |
| Next | `npm run start` |
| Email | `CMCP_SKIP_CHATBOT_WARMUP=1 .venv/bin/python scripts/email_worker.py` |
| Push | `CMCP_SKIP_CHATBOT_WARMUP=1 .venv/bin/python scripts/notification_worker.py` |
| Chatbot index | `CMCP_SKIP_CHATBOT_WARMUP=1 .venv/bin/python scripts/chatbot_index_worker.py` |

After first seed/bulk import:

```bash
python scripts/reindex_existing_materials.py
```

Manage with systemd (three worker units + API + Next). Do not merge workers into one Python process.

---

## Example production snippets (placeholders only)

### `frontend` env

```env
FLASK_ORIGIN=http://127.0.0.1:7000
```

### `backend/.env` (excerpt)

```env
ENV=production
SECRET_KEY=change-me-long-random
SECURITY_PASSWORD_SALT=change-me-salt
ENCRYPTION_KEY=change-me-fernet-44-char-urlsafe-base64=

DATABASE_HOST=127.0.0.1
DATABASE_PORT=5432
DATABASE_USER=justclick
DATABASE_PASSWORD=change-me
DATABASE_NAME=justclick

APP_BASE_URL=https://your-domain.com
FRONTEND_BASE_URL=https://your-domain.com
PUBLIC_API_BASE_URL=

SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=lax
CORS_ALLOWED_ORIGINS=["https://your-domain.com"]

MEDIA_BACKEND=local
LOCAL_MEDIA_ROOT=/var/lib/justclick/media
MEDIA_MAX_MB=100

MAIL_PROVIDER=smtp
MAIL_FROM_EMAIL=justclick.cmc@gmail.com
MAIL_FROM_NAME=JustClick
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=justclick.cmc@gmail.com
SMTP_PASSWORD=your-app-password
CONTACT_NOTIFY_EMAIL=justclick.cmc@gmail.com

# chatbot vars as already used in your .env
CMCP_SKIP_CHATBOT_WARMUP=1
```

---

## Nginx (later — not deploying now)

Typical shape:

```nginx
# public → Next.js :3000
# optional: /api/ → Flask :7000  OR keep Next /api/backend proxy only
```

If Next remains the only public entrypoint, Flask can listen on localhost only.  
Set `APP_BASE_URL` to the public HTTPS site. Leave `PUBLIC_API_BASE_URL` empty when using the Next media proxy.

---

## Secrets to back up

1. PostgreSQL dumps  
2. Entire `LOCAL_MEDIA_ROOT` tree  
3. `ENCRYPTION_KEY`  
4. `SECRET_KEY` / `SECURITY_PASSWORD_SALT`  
5. SMTP / Firebase credentials  

Losing `ENCRYPTION_KEY` without ciphertext recovery means **permanent loss of readable uploads**.
