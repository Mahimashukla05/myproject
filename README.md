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

### Current Implementation (Phases 1 - 4 Complete)
- **Phase 1 Foundation**: Flask API + React (Vite) + MongoDB availability detection.
- **Phase 2 Authentication & RBAC**: Session-based auth with HTTP-only cookies, CSRF protection, rate limiting, secure password hashing, and role permissions (`admin`, `operator`, `user`).
- **Phase 3A Parcel Model & Validation**: `ParcelModel` with backend input validation rules.
- **Phase 3B Routing Engine**: Dedicated `RoutingService` executing weight-based department rules (`MAIL`, `REGULAR`, `HEAVY`) and value-based insurance rules (`NOT_REQUIRED`, `REQUIRED`).
- **Phase 3C Insurance Workflow & Lifecycle**: Admin insurance approval/rejection with failure reasons, state machine transitions (`RECEIVED` → `ASSIGNED` → `IN_PROCESSING` → `COMPLETED` / `FAILED`), and audit logging (`audit_logs`).
- **Phase 3D Batch Upload (JSON/XML)**: Secure batch parcel upload endpoint (`POST /api/parcels/batch`) with XML XXE hardening, partial success/failure handling, configurable size limits, and RBAC (`admin` and `operator` only).
- **Phase 4 Dashboard & Operational Views**: Dashboard summary endpoint (`GET /api/dashboard/summary`), time period filters (`today`, `week`, `all`), department distribution (`MAIL`, `REGULAR`, `HEAVY`), paginated & filterable parcel history endpoint (`GET /api/parcels`), parcel detail view (`GET /api/parcels/<id>`), and user-level parcel scoping for Normal Users.
- **Phase 5 Routing Rule Management & Change Requests**: Dynamic versioned routing rules in MongoDB (`routing_rules` collection), Default Version 1 seeding, strict rule set validation (gap/overlap prevention), Operator rule change request workflow (`rule_change_requests` collection) supporting `ADD`, `MODIFY`, `DEACTIVATE` across `INSURANCE` and `DEPARTMENT` categories, Admin approval workflow (creating monotonic Version 2+ and logging audit events `RULE_CHANGE_APPROVED` & `RULE_VERSION_ACTIVATED`), Admin rejection workflow (with required rejection reason and `RULE_CHANGE_REJECTED` audit logging), Operator withdrawal of pending requests, rule version history tracking (`GET /api/routing-rules/history`), and frontend governance UI (`RuleManagement.jsx`).

### Operational Dashboard & Rule Management Features (Phases 4 & 5)
- **Dashboard Summary**: `GET /api/dashboard/summary?period=today|week|all` (restricted to `admin` and `operator`). Time periods: `today` (00:00 UTC today), `week` (current calendar week from Monday 00:00:00 UTC), `all` (all time). Metrics: `insurancePending` (`insuranceStatus == "PENDING"`) and `insuranceRejected` (`insuranceStatus == "REJECTED"`) are based strictly on authoritative `insuranceStatus`.
- **Operational Listing**: `GET /api/parcels?status=...&department=...&insuranceStatus=...&parcelId=...&page=1&limit=20&sort=-submittedAt` with server-side pagination and NoSQL-safe whitelist sorting.
- **Rule Governance**: Dynamic active rule retrieval (`GET /api/routing-rules/active`), version history (`GET /api/routing-rules/history`), request creation (`POST /api/rule-change-requests`), Admin approval (`POST /api/rule-change-requests/<id>/approve`), Admin rejection (`POST /api/rule-change-requests/<id>/reject`), and Operator withdrawal (`POST /api/rule-change-requests/<id>/withdraw`).
- **RBAC & User Scoping**: Admin and Operator see system-wide metrics, parcel listings, and routing rule management. Normal Users access only their own submitted parcels; attempts to query or view other users' parcels or access rule management are blocked with HTTP 403. Existing evaluated parcels retain their evaluated department/insurance status upon rule version activation.

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

## Running Automated Tests

### Backend Tests (pytest)
```bash
cd backend
.\venv\Scripts\pytest
```

### Frontend Tests (Vitest)
```bash
cd frontend
npm test
```
