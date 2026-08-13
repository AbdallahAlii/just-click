# Notifications, Email, and Background Workers

Quick reference for the JustClick backend notification stack.

## What each channel means

| Channel | Where it goes | Worker needed |
|---------|---------------|---------------|
| **In-app** | `user_notifications` table → mobile/web API `/api/notifications/list` | None (immediate) |
| **Email** | `email_outbox` table → SMTP send | `email_worker.py` |
| **Mobile push** | `push_outbox` table → Firebase Cloud Messaging | `notification_worker.py` + `FIREBASE_SERVER_KEY` |

Push is **only for mobile app alerts** (phones with FCM token registered). It is not email and not the same as in-app notifications.

## Commands (run from `backend/`)

### 1. Email worker (verification, approval, material emails, admin broadcasts)

```bash
cd /mnt/dev/just-click/backend
CMCP_SKIP_CHATBOT_WARMUP=1 .venv/bin/python scripts/email_worker.py
```

Polls `email_outbox` where `status=pending`, sends via SMTP, marks `sent` or `failed`.

### 2. Push notification worker (mobile FCM)

```bash
cd /mnt/dev/just-click/backend
CMCP_SKIP_CHATBOT_WARMUP=1 .venv/bin/python scripts/notification_worker.py
```

Polls `push_outbox` where `status=pending`. Without `FIREBASE_SERVER_KEY`, rows are marked `skipped`.

### 3. Smoke test (notifications API + DB wiring)

```bash
cd /mnt/dev/just-click/backend
CMCP_SKIP_CHATBOT_WARMUP=1 PYTHONPATH=src .venv/bin/python scripts/test_notifications_api.py
```

Creates a test in-app notification and queues email for one student.

## Required environment variables

### Email (Gmail example)

```env
MAIL_PROVIDER=smtp
MAIL_FROM_EMAIL=justclick.cmc@gmail.com
MAIL_FROM_NAME=JustClick
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=justclick.cmc@gmail.com
SMTP_PASSWORD=your-16-char-app-password
```

**Important:** Gmail normal passwords fail with `534 5.7.9 WebLoginRequired`. Create an [App Password](https://myaccount.google.com/apppasswords) and put that in `SMTP_PASSWORD`.

### Push (optional)

```env
FIREBASE_SERVER_KEY=your-firebase-server-key
```

### Links in emails

```env
APP_BASE_URL=http://localhost:3000
```

## Auto notifications (materials)

When admin creates an enabled material or updates its file/URL, the system queues:

- In-app notification for eligible students (active, approved, verified email)
- Email (`material_published` or `material_updated` template)
- Push (if students registered device tokens)

## Admin manual send

UI: **Academic → Notifications**

API: `POST /api/notifications/admin/send`

Recent batches now show delivery status: `sent`, `pending`, or `failed` (from email/push outbox).

## Mobile app APIs

| Endpoint | Purpose |
|----------|---------|
| `GET /api/notifications/list` | Paginated notifications |
| `GET /api/notifications/unread-count` | Badge count |
| `POST /api/notifications/read` | Mark one read |
| `POST /api/notifications/read-all` | Mark all read |
| `POST /api/notifications/devices/register` | Register FCM token |

## Typical local dev setup

Use **three terminals** (plus chatbot index worker if you use JustClick AI):

1. Flask API server
2. Email worker
3. Push worker (optional until FCM is configured)
4. Chatbot index worker (required for AI over materials)

Notifications are **queued immediately** when you click Send or upload a material. Workers deliver them asynchronously.

Forgot-password emails also go through `email_outbox` (`password_reset` template) and require the email worker.

For VPS/production process layout, seed order, and systemd guidance, see **[PRODUCTION_WORKERS_AND_SEED.md](./PRODUCTION_WORKERS_AND_SEED.md)**.

## Mobile app integration

See **[MOBILE_NOTIFICATIONS_API.md](./MOBILE_NOTIFICATIONS_API.md)** for the full mobile developer guide (Postman examples, response shapes, FCM registration, event types).
