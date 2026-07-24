# Mobile Notifications API Guide

Guide for mobile app developers integrating JustClick student notifications (in-app list + push).

## Overview

Students receive notifications in three ways:

| Channel | Where | Mobile app work |
|---------|--------|-----------------|
| **In-app** | `user_notifications` table | Call REST APIs below |
| **Email** | Student inbox | No app work (backend + email worker) |
| **Push** | Phone lock screen | Register FCM token + handle payload |

**When notifications are created automatically:**

1. **New material uploaded** (`event_type: material_created`) — admin creates an enabled material
2. **Material file updated** (`event_type: material_updated`) — admin replaces file or URL
3. **Admin broadcast** (`event_type: admin_broadcast`) — admin sends manual message from dashboard

All go to **active, approved, email-verified students**.

---

## Base URL & auth

```
Base: http://YOUR_HOST:7000/api
```

All endpoints require:

1. **Session cookie** (after `POST /api/auth/login`) — same as web app  
   OR your app’s existing auth mechanism if you proxy cookies.

2. **Company scope** — pass `company_id` as query param or rely on session `company_id`.

Example login (Postman):

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "C12292",
  "password": "your-password"
}
```

Save the session cookie (`cmcp_session` or your configured name) for later requests.

---

## Student APIs (implement these in the mobile app)

### 1. List notifications

```http
GET /api/notifications/list?company_id=1&page=1&per_page=20
GET /api/notifications/list?company_id=1&unread_only=true
```

**Response:**

```json
{
  "success": true,
  "message": "OK",
  "data": {
    "data": [
      {
        "id": 42,
        "event_type": "material_created",
        "title": "New material: Chapter 4 Slides",
        "body": "A new study material \"Chapter 4 Slides\" was uploaded for CS101 · Intro to CS.",
        "data": {
          "type": "material_created",
          "material_id": "152",
          "link": "http://localhost:3000/materials/152"
        },
        "material_id": 152,
        "read_at": null,
        "is_read": false,
        "created_at": "2026-07-24T18:00:00+00:00"
      }
    ],
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 5,
      "pages": 1
    },
    "unread_count": 3
  }
}
```

**`event_type` values:**

| Value | Meaning |
|-------|---------|
| `material_created` | New study material |
| `material_updated` | Material file updated |
| `admin_broadcast` | Admin manual announcement |

**Deep link:** use `data.link` or build `/materials/{material_id}` from `material_id`.

---

### 2. Unread badge count

```http
GET /api/notifications/unread-count?company_id=1
```

**Response:**

```json
{
  "success": true,
  "message": "OK",
  "data": { "unread_count": 3 }
}
```

Poll this on app open and after push received.

---

### 3. Mark one notification read

```http
POST /api/notifications/read?company_id=1
Content-Type: application/json

{
  "notification_id": 42
}
```

**Response:**

```json
{
  "success": true,
  "message": "Marked as read."
}
```

Call when user opens a notification detail.

---

### 4. Mark all read

```http
POST /api/notifications/read-all?company_id=1
Content-Type: application/json

{}
```

**Response:**

```json
{
  "success": true,
  "message": "Marked 3 as read.",
  "data": { "marked": 3 }
}
```

---

### 5. Register device for push (FCM)

Call after login when you have the FCM token:

```http
POST /api/notifications/devices/register?company_id=1
Content-Type: application/json

{
  "token": "fcm-device-token-from-firebase",
  "platform": "android"
}
```

`platform`: `android` | `ios` | `web`

**Response:**

```json
{
  "success": true,
  "message": "Device registered.",
  "data": { "id": 1, "platform": "android" }
}
```

Re-register when FCM token refreshes.

---

## Push notification payload (FCM)

When backend sends push, data payload includes:

```json
{
  "type": "material_created",
  "material_id": "152",
  "link": "http://localhost:3000/materials/152"
}
```

Notification title/body match the in-app row. On tap:

1. Open `link` or material screen using `material_id`
2. Call `POST /api/notifications/read` with the in-app `id` (fetch from list if needed)

---

## Recommended mobile flow

```
App launch
  → Login (session cookie)
  → GET /notifications/unread-count  → show badge
  → POST /notifications/devices/register (FCM token)

Notifications screen
  → GET /notifications/list?page=1&per_page=20
  → Pull to refresh / paginate with page=

User taps notification
  → POST /notifications/read { notification_id }
  → Navigate to material (material_id or data.link)

Push received (foreground/background)
  → Refresh unread count
  → Optionally refresh list
```

---

## Postman collection (quick test)

1. **Login** → save cookie  
2. **List:** `GET {{base}}/notifications/list?company_id=1`  
3. **Unread:** `GET {{base}}/notifications/unread-count?company_id=1`  
4. **Register device:** `POST {{base}}/notifications/devices/register?company_id=1`  
   Body: `{ "token": "test-token-123", "platform": "android" }`  
5. **Mark read:** `POST {{base}}/notifications/read?company_id=1`  
   Body: `{ "notification_id": 1 }`

**Permission required:** student session with `Student Material Interaction:READ` (and `CREATE` for device register, `UPDATE` for mark read).

---

## How backend creates notifications (for context)

You do **not** call these from the mobile app — they explain when students get notified.

| Trigger | Who receives | Channels |
|---------|--------------|----------|
| Admin creates material (enabled) | Eligible students | in-app + email + push |
| Admin updates material file/URL | Eligible students | in-app + email + push |
| Admin → Notifications → Send | All or selected students | chosen channels |

Delivery:

- **In-app** — immediate insert into `user_notifications`
- **Email** — queued in `email_outbox`, sent by `email_worker.py`
- **Push** — queued in `push_outbox`, sent by `notification_worker.py` (needs `FIREBASE_SERVER_KEY`)

---

## Background workers (ops / backend team)

```bash
# Email (verification, material emails, broadcasts)
cd backend && CMCP_SKIP_CHATBOT_WARMUP=1 .venv/bin/python scripts/email_worker.py

# Push (FCM)
cd backend && CMCP_SKIP_CHATBOT_WARMUP=1 .venv/bin/python scripts/notification_worker.py
```

Mobile dev: push only works when ops runs the push worker and `FIREBASE_SERVER_KEY` is set. In-app APIs work without workers.

---

## Error handling

| HTTP | Meaning |
|------|---------|
| 401 | Not logged in — re-login |
| 403 | Missing permission or wrong company |
| 404 | Notification not found (mark read) |
| 400 | Invalid body (e.g. missing `notification_id`) |

Standard envelope:

```json
{
  "success": false,
  "message": "Human readable error",
  "data": null
}
```

---

## Smoke test (backend)

```bash
cd /mnt/dev/just-click/backend
CMCP_SKIP_CHATBOT_WARMUP=1 PYTHONPATH=src .venv/bin/python scripts/test_notifications_api.py
```

---

## Related docs

- [`NOTIFICATIONS_AND_WORKERS.md`](./NOTIFICATIONS_AND_WORKERS.md) — workers, env vars, admin UI
