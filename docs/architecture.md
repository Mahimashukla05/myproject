# Parcel Routing System - Architecture Overview

## Overview
The Parcel Routing System is designed to handle parcel intake, routing criteria evaluation, insurance workflow management, audit tracking, and administrative rule governance.

---

## 1. Current Phase 1 Implementation

- **Project Foundation**: Clean project structure separating React + Vite frontend and Flask Python backend.
- **Database Connection**: Basic MongoDB connection setup (`backend/config/db.py`) with explicit database status detection (`connected` vs `unavailable`).
- **Dependency / Error Handling Policy**:
  - Genuinely empty database: UI displays zero count metrics and clean "No parcels found" empty states.
  - Database unavailable: Backend returns `database: unavailable` status and UI displays an explicit **Database Error** banner (`"Database unavailable: Cannot connect to MongoDB database"`), preventing false 0 metrics.
- **Logging Configuration**: Standard Python rotating file logging (`app.log`) configured separately from planned database audit logs.
- **Automated Testing**: Baseline health check test with `pytest` on backend and smoke/empty-state test with `Vitest` on frontend.

---

## 2. Planned Architecture (Phase 2 & Beyond)

### SOLID Architectural Principles
- **Single Responsibility (S)**: HTTP routes, business services, and database persistence modules remain strictly separated.
- **Open/Closed (O)**: Routing engine allows rule evaluation extensions without modifying core workflow pipelines.
- **Liskov Substitution (L)**: Data access objects and service contracts respect interchangeable interfaces.
- **Interface Segregation (I)**: Minimal, focused service parameters and database access contracts.
- **Dependency Inversion (D)**: Business logic services remain independent from concrete infrastructure.

### Role-Based Access Control (RBAC)
Server-side authorization for two defined roles:
- **Admin**: Dashboard, rule approvals (requires case-sensitive confirmation `"ACTIVATE"`), user management, audit logs, system alerts. Admin registration requires environment-configured `ADMIN_REGISTRATION_KEY`.
- **Operator**: Single parcel intake form, batch file upload (JSON/XML), rule change requests, system-wide parcel history, work alerts.
- *Normal User role is completely removed from registration, login, and authorization flows.*

### Parcel & Audit Lifecycles
- **Operational Dashboard (Phase 4)**: System summary metrics (`totalParcels`, `successfullyProcessed`, `failed`, `insurancePending`, `insuranceRejected`) and department distribution (`MAIL`, `REGULAR`, `HEAVY`) over configurable time boundaries (`today`, `week` meaning current calendar week from Monday 00:00:00 UTC, `all`) via `GET /api/dashboard/summary`. `insurancePending` and `insuranceRejected` are based strictly on authoritative `insuranceStatus` (`PENDING` / `REJECTED`).
- **Paginated Parcel Operational Views (Phase 4)**: Server-side paginated and filterable parcel history endpoint (`GET /api/parcels`) with NoSQL-safe whitelist sorting.
- **Routing Rule Governance & Change Requests (Phase 5 & Phase 7)**: Dynamically versioned routing rules in MongoDB (`routing_rules`), active version lookup (`GET /api/routing-rules/active`), version history (`GET /api/routing-rules/history`), Operator rule change requests (`rule_change_requests`), Admin approval (`POST /api/rule-change-requests/<id>/approve` requiring exact body `{"confirmation": "ACTIVATE"}`), Admin rejection (`POST /api/rule-change-requests/<id>/reject`), Operator withdrawal (`POST /api/rule-change-requests/<id>/withdraw`), and `audit_logs` integration (`RULE_CHANGE_APPROVED`, `RULE_VERSION_ACTIVATED`, `RULE_CHANGE_REJECTED`).
- **Audit Logs**: Mongo-backed administrative change audit tracking (`audit_logs`).

---

## 3. Implemented Architecture Summary (Phases 1 - 7)

The application implements a clean, layered architecture:
- **Routes & Controllers**: `auth_routes.py`, `parcel_routes.py`, `batch_routes.py`, `dashboard_routes.py`, `rule_routes.py`, `admin_routes.py`, `operator_routes.py`.
- **Business Services**: `auth_service.py`, `parcel_service.py`, `batch_service.py`, `routing_service.py`, `rule_service.py`, `alert_service.py`, `dashboard_service.py`, `lifecycle_service.py`.
- **Data Models**: `UserModel`, `ParcelModel`, `AuditModel`, `RoutingRuleModel`, `RuleChangeRequestModel`.
- **Frontend Architecture**: React components (`LoginPage`, `RegisterPage`, `DashboardMetrics`, `BatchUpload`, `ParcelTable`, `ParcelDetailModal`, `RuleManagement`, `AuditLogTable`, `OperatorWorkAlerts`, `AdminSystemAlerts`), state context (`AuthContext`), and responsive CSS (`index.css`).
- **Production Readiness & Security**: Environment-driven CORS and cookie settings (`HttpOnly`, `Secure`, `SameSite=Lax`), NoSQL injection parameter whitelisting, XML XXE security parsing, login rate-limiting, and deployment configuration for Vercel, Render, and MongoDB Atlas.
