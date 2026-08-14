# SmartManager

CRM API + workers stubs для екосистеми **SmartZno**.

Окремий репозиторій (не monorepo). Споживачі:

- [SmartZno Land](https://github.com/Sneezyan123/SmartZno) — `http://localhost:3000`
- [SmartZno Manager](https://github.com/Sneezyan123/SmartZno_Manager) — `http://localhost:3001`

## Stack

Python 3.12 · FastAPI · Motor (Mongo `smartzno_crm`) · JWT · Pydantic Settings

Якщо Mongo недоступна — автоматичний **in-memory** режим (зручно для skeleton).

## Run

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Health: `GET http://localhost:8000/health`

## Demo login (CRM staff)

| Email | Password | Role |
|---|---|---|
| admin@smartzno.com | admin | admin |
| sales@smartzno.com | sales_manager | sales_manager |
| curator@smartzno.com | curator_lead | curator_lead |
| ads@smartzno.com | targetologist | targetologist |

## Demo student (кабінет)

| Email | Password |
|---|---|
| pupil@smartzno.com | pupil123 |

Підписки demo-учня: math (~12 дн.), ukr (~3 дн.), history (прострочена).

## Telegram

У `.env` задайте:

```
TELEGRAM_BOT_TOKEN=123:ABC...
TELEGRAM_NOTIFY_CHAT_ID=123456789
```

Без токена повідомлення пишуться в колекцію `telegram_outbox` (і в лог) — локальний stub.

## Thin-slice routes

- `POST /auth/login`, `GET /auth/me`
- `POST /leads/incoming`, `GET /leads` → Telegram notify
- `POST /diagnostics/attempts`, `GET /diagnostics/attempts/{id}` → lead + Telegram
- `POST /students/register`, `POST /students/login`, `GET /students/me`
- `POST /demo-accesses`
- `POST /subscriptions`, `GET /subscriptions/{id}`
- `POST /payments/webhook` (header `x-api-key`)
- `POST /cohorts`, `POST /cohorts/{id}/enroll`
- `POST /curators/assign`, `GET /curators/sla`

## ERD (ключове)

Parent 1—N Student · Student 1—N Subscription · Subscription → Cohort + Curator · Lead → Parent/Student · DiagnosticAttempt / DemoAccess на Student.
