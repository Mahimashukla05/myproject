# Parcel Routing System

A clean, understandable Parcel Routing System built for an engineering assessment using React + Vite on the frontend, Python + Flask on the backend, and MongoDB for database persistence.

## Tech Stack

- **Frontend**: React, JavaScript (JSX), Vite, CSS
- **Backend**: Python 3.10+, Flask
- **Database**: MongoDB / MongoDB Atlas (pymongo driver)
- **Testing**: pytest (backend), Vitest + React Testing Library (frontend)
- **Logging**: Python standard logging (`RotatingFileHandler`)

## Project Structure

```
myproject/
├── frontend/             # React + Vite frontend
│   ├── src/              # React components, pages, services, utils
│   ├── index.html        # Main HTML entry
│   ├── vite.config.js    # Vite & Vitest configuration
│   └── package.json      # Node package dependencies
├── backend/              # Flask backend API
│   ├── config/           # App, logging, and DB settings
│   ├── routes/           # REST API endpoints
│   ├── services/         # Business logic
│   ├── models/           # MongoDB data access layer
│   ├── tests/            # pytest suite
│   ├── logs/             # Application log directory
│   ├── app.py            # Flask application entry point
│   └── requirements.txt  # Python dependencies
├── docs/                 # Architectural documentation
│   └── architecture.md
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore file
└── README.md             # Project documentation
```

## Implementation Status

### Current Implementation (Phases 1 - 7 Complete)
- **Phase 1 Foundation**: Flask API + React (Vite) + MongoDB availability detection.
- **Phase 2 Authentication & RBAC**: Session-based auth with HTTP-only cookies, CSRF protection, rate limiting, secure password hashing, and role permissions (`admin`, `operator`, `user`).
- **Phase 3A Parcel Model & Validation**: `ParcelModel` with backend input validation rules.
- **Phase 3B Routing Engine**: Dedicated `RoutingService` executing weight-based department rules (`MAIL`, `REGULAR`, `HEAVY`) and value-based insurance rules (`NOT_REQUIRED`, `REQUIRED`).
- **Phase 3C Insurance Workflow & Lifecycle**: Admin insurance approval/rejection with failure reasons, state machine transitions (`RECEIVED` → `ASSIGNED` → `IN_PROCESSING` → `COMPLETED` / `FAILED`), and audit logging (`audit_logs`).
- **Phase 3D Batch Upload (JSON/XML)**: Secure batch parcel upload endpoint (`POST /api/parcels/batch`) with XML XXE hardening, partial success/failure handling, configurable size limits, and RBAC (`admin` and `operator` only). Batch-created parcels remain in `RECEIVED` state without automatic routing.
- **Phase 4 Dashboard & Operational Views**: Dashboard summary endpoint (`GET /api/dashboard/summary`), time period filters (`today`, `week` for current calendar week, `all`), department distribution (`MAIL`, `REGULAR`, `HEAVY`), paginated & filterable parcel history endpoint (`GET /api/parcels`), parcel detail view (`GET /api/parcels/<id>`), and user-level parcel scoping for Normal Users.
- **Phase 5 Routing Rule Management & Change Requests**: Dynamic versioned routing rules in MongoDB (`routing_rules` collection), Default Version 1 seeding, strict rule set validation (gap/overlap prevention), Operator rule change request workflow (`rule_change_requests` collection) supporting `ADD`, `MODIFY`, `DEACTIVATE` across `INSURANCE` and `DEPARTMENT` categories, Admin approval workflow (creating monotonic Version 2+ and logging audit events `RULE_CHANGE_APPROVED` & `RULE_VERSION_ACTIVATED`), Admin rejection workflow (with required rejection reason and `RULE_CHANGE_REJECTED` audit logging), Operator withdrawal of pending requests, rule version history tracking (`GET /api/routing-rules/history`), and frontend governance UI (`RuleManagement.jsx`).
- **Phase 6 Admin Audit UI & Operator Alerts**: Server-side paginated audit logs endpoint (`GET /api/admin/audit-logs`) with filtering (`action`, `actorUsername`, `actorRole`, `parcelId`) restricted to Admin, Operator Work Alerts endpoint (`GET /api/operator/alerts`) for high-priority operational items, Admin System Alerts endpoint (`GET /api/admin/alerts`) for system-wide failure rates, volume spikes, department concentrations, and insurance backlogs.
- **Phase 7 Security Hardening & Production Readiness**: NoSQL injection protection via whitelisting & strict type enforcement, XML/XXE protection, production cookie security (`HttpOnly`, `Secure`, `SameSite=Lax`), CSRF token validation on state-changing requests, generic error responses preventing account enumeration, rate limiting on login failures, CORS environment-driven origin configuration, full test regression, and deployment configuration for Vercel (Frontend), Render (Backend), and MongoDB Atlas (Database).

## Roles & Permissions

- **Admin**: Full access to operational dashboard, system-wide parcel listings, parcel detail views, insurance approval/rejection, dynamic routing rule management & approvals, audit log viewer, system-wide alerts, and user management.
- **Operator**: Access to parcel submission, batch file upload (JSON/XML), operational parcel listing, parcel detail views, rule change request creation/withdrawal, active rules (read-only), and personal work alerts. No access to audit logs, admin system alerts, or user management.
- **Normal User**: Access strictly limited to submitting parcels and viewing their own submitted parcels. Cannot view other users' parcels or access operator/admin features.

## Parcel Lifecycle & Workflow

1. **Intake**: Single parcel entry or JSON/XML batch upload creating parcels in `RECEIVED` state.
2. **Routing**: Explicit routing evaluation applying active rule set to determine `department` (`MAIL`, `REGULAR`, `HEAVY`) and `insuranceRequired` (`REQUIRED`, `NOT_REQUIRED`).
3. **Insurance Workflow**: High-value parcels require Admin insurance approval. If approved, parcel transitions to `RECEIVED` (insurance status `APPROVED`); if rejected with reason, transitions to `INSURANCE_REJECTED`.
4. **Processing State Machine**: `RECEIVED` → `ASSIGNED` → `IN_PROCESSING` → `COMPLETED` (or `FAILED` if technical processing error occurs).

## Deployment Architecture

- **Frontend**: Vercel (React + Vite build output in `frontend/dist`)
- **Backend**: Render (Python Flask WSGI application using `backend/app.py`)
- **Database**: MongoDB Atlas (Cloud-hosted MongoDB cluster)

### Environment Variables Matrix

| Variable Name | Component | Description | Production Example |
| :--- | :--- | :--- | :--- |
| `PORT` | Backend | Port for Flask application | `5000` |
| `FLASK_ENV` | Backend | Environment mode | `production` |
| `SECRET_KEY` | Backend | Flask session signing secret | `<strong-random-secret>` |
| `MONGO_URI` | Backend | MongoDB connection string | `mongodb+srv://<user>:<pass>@cluster.mongodb.net/parcel_routing_db` |
| `ADMIN_REGISTRATION_KEY` | Backend | Key required for Admin registration | `<secure-admin-key>` |
| `ALLOWED_ORIGINS` | Backend | Comma-separated CORS origins | `https://your-app.vercel.app` |
| `SESSION_COOKIE_SECURE` | Backend | Enforce HTTPS-only session cookies | `True` |
| `VITE_API_BASE_URL` | Frontend | Backend API base URL | `https://your-api.onrender.com/api` |

## Setup & Running Locally

### 1. Environment Setup
Copy `.env.example` to `.env` in the project root:
```bash
cp .env.example .env
```

### 2. Backend Setup
Navigate to `backend/`, create a virtual environment, install dependencies, and run Flask:
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
python app.py
```
The backend server runs on `http://localhost:5000`.

### 3. Frontend Setup
Navigate to `frontend/`, install dependencies, and start the Vite dev server:
```bash
cd frontend
npm install
npm run dev
```
The frontend dev server runs on `http://localhost:5173`.

## Running Automated Tests & Production Build

### Backend Tests (pytest)
```bash
cd backend
.\venv\Scripts\pytest backend\tests
```

### Frontend Tests (Vitest)
```bash
cd frontend
npm test
```

### Frontend Production Build
```bash
cd frontend
npm run build
```

