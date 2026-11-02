# ReLoop

ReLoop is a device-recovery decision support app. It records devices and condition assessments, ranks eligible next steps, explains the score, lists service-provider records, and tracks user-created recovery requests.

## Stack

- Backend: FastAPI, SQLAlchemy, SQLite by default, PostgreSQL-compatible schema
- Frontend: Next.js 14, React 18, TypeScript
- Recommendation weights: financial feasibility 35%, useful life 30%, convenience 15%, reuse potential 20%

## Backend setup

Use Python 3.11 or newer. From PowerShell:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`; interactive API documentation is at `/docs`. The default SQLite URL is relative to the `backend` directory and uses `backend/reloop.db`. Startup creates missing tables and adds missing sample categories and providers; it does not drop tables or delete existing records. No schema migration framework is configured, so changes to existing production table layouts need a reviewed migration before deployment.

The backend reads `backend/.env` and process environment variables. A development signing key is generated randomly when `SECRET_KEY` is blank; tokens issued with that key stop working after a process restart. Set a stable random `SECRET_KEY` of at least 32 characters for production and set `APP_ENV=production`. Keep `.env` private; it is ignored by Git.

To provision an administrator on a new database, set both `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` in `backend/.env` before the first startup. The password must be 12 to 72 characters. Startup creates that account only if its email is not already present. Public registration always creates a regular user; there are no default demo accounts or hardcoded passwords.

`CORS_ORIGINS` is a comma-separated list. The default allows `http://localhost:3000`. Add only trusted frontend origins when deploying.

## Frontend setup

Use Node.js 18.17 or newer. In a separate terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The default API URL is `http://localhost:8000/api`. Override it by setting `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local` before starting Next.js. The browser stores the bearer token in session storage and clears it when signing out or when the API rejects it.

## Database and sample data

SQLite tables are initialized from the SQLAlchemy models. `backend/schema.sql` is the PostgreSQL DDL reference. The seed script creates device categories and clearly marked sample provider listings. Sample locations and contact details are illustrative, not verified businesses. Replace them with confirmed provider records before treating the directory as operational. ReLoop does not book, dispatch, or arrange transport.

The existing `backend/reloop.db` is local application data and must not be uploaded. Tests use a temporary database and remove it after the run.

## Assessment estimates

The assessment endpoint creates deterministic repair-cost ranges from category-specific labor/part bands for battery, screen/display, motherboard, charging-port, liquid-damage, and keyboard faults. Distinct faults are combined at a reduced secondary rate, while duplicate descriptions are charged once. Brand/model tier and age adjust pricing; OLED/AMOLED/Retina and foldable displays add a display multiplier when inferred from the model or fault text. Explicit LCD/LED details use the category baseline. Replacement, resale, and remaining-life estimates use category, age, condition, function, and matched faults. The response includes normalized matched fault classes, range bounds, estimate midpoint, and confidence; an unknown panel type lowers confidence and asks for more detail.

These are approximate planning ranges based on built-in category part/labor assumptions, not a live regional pricing feed, live part catalog, provider quote, appraisal, or guaranteed market price. If a fault is unclassified or a screen technology cannot be inferred, the API reports low confidence and includes the missing-detail guidance. The midpoint is persisted and used by the existing recommendation scorer; the low/high bounds and matched faults are returned for display.

## Tests and checks

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
```

From `frontend`:

```powershell
npm run lint
npm run typecheck
npm run build
```

The API tests cover registration/login, admin authorization, device creation, estimated assessment persistence and retrieval, recommendation ranking, provider lookup, recovery creation, and private tracking. Engine tests cover route eligibility, weighted scoring, distinct battery/screen/motherboard/charging-port estimates, display/model adjustments, multiple-fault deduplication, condition/function impact, confidence, missing estimates, and the Reuse route.

## Current limitations

- Convenience is a route-level heuristic; provider distance is not included in scoring.
- Provider records seeded by default are samples and are not verified real-world services.
- Recovery status changes are entered by an administrator; there are no automatic logistics or recycler integrations.
- Access tokens are stateless and are cleared client-side on logout; server-side token revocation is not implemented.
- Existing database tables are not automatically migrated when the model changes.
- Fault price bands are fixed rule-based planning assumptions and are not calibrated against live local labor or parts prices.
