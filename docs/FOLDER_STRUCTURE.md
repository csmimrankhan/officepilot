# Project Folder Structure

This document outlines the organization of the OfficePilot AI repository to help developers navigate the codebase efficiently.

## 1. Root Level Overview
- `/backend`: Python FastAPI local agent and business logic.
- `/frontend`: React/Vite web application.
- `/desktop`: Tauri desktop shell and packaging configuration.
- `/docs`: Project documentation (Manuals, Architecture, Safety).
- `/samples`: Sample data for testing (Invoices, Excel files, Workflows).
- `/marketing`: Landing page assets and screenshot placeholders.
- `/scripts`: PowerShell and Shell scripts for building and deployment.
- `/storage`: Local data storage for uploaded files and snapshots.
- `/data`: App-specific data (backups, recordings, audit exports).
- `AGENTS.md`: High-level overview for AI development agents.
- `README.md`: Project introduction and setup instructions.
- `.env.example`: Template for environment variables.

---

## 2. Backend Structure (`/backend`)
### `/app`
- `main.py`: Entry point; initializes FastAPI, routers, and lifespan handlers.
- `config.py`: Centralized Pydantic Settings; loads environment variables.
- `db.py`: Database engine and session management.
- **`/models`**: SQLAlchemy ORM definitions (one file per table).
- **`/schemas`**: Pydantic models for request/response validation.
- **`/services`**: The core business logic layer. Decoupled from API.
- **`/routers`**: API route definitions grouped by domain (auth, invoice, accounting).
- **`/utils`**: Helper functions (encryption, formatting).

### `/tests`
- Phase-based test files (e.g., `test_phase10.py`).
- Domain-specific tests (e.g., `test_accounting.py`).
- `conftest.py`: Shared pytest fixtures.

---

## 3. Frontend Structure (`/frontend`)
### `/src`
- `App.jsx`: Main routing and layout wrapper.
- `api.js`: The **single source of truth** for all backend API calls.
- `auth.js`: Authentication state management (JWT handling).
- **`/pages`**: Route-level components (Dashboard, Review Queue, Settings).
- **`/components`**: Reusable UI elements (Modals, Buttons, Voice Assistant).
- `styles.css`: Centralized styling (Tailwind-compatible or Vanilla CSS).

### `/tests`
- Vitest/React-Testing-Library tests for UI components and pages.

---

## 4. Desktop Structure (`/desktop/tauri`)
- `tauri.conf.json`: Main configuration for the desktop shell.
- **`/src-tauri`**: Rust-based entry point and system-level commands.
- **`/binaries`**: Storage for the bundled Python sidecar executable.

---

## 5. Documentation Structure (`/docs`)
- `USER_MANUAL.md`: End-user instructions.
- `ADMIN_MANUAL.md`: System administration and safety.
- `SYSTEM_FLOW_AND_ARCHITECTURE.md`: Technical overview.
- `TECHNICAL_DETAIL.md`: Implementation specifics for developers.
- `NONTECHNICAL_OVERVIEW.md`: Product summary for stakeholders.
- `CLEAN_WINDOWS_QA.md`: Verification steps for a fresh install.

---

## 6. Naming Conventions
- **Files**: `snake_case` for Python, `camelCase` for JavaScript components (e.g., `InvoiceRow.jsx`).
- **Models**: `singular_purpose.py`.
- **Routers**: `plural_domain.py` (e.g., `invoices.py`).
- **Services**: `domain_logic.py`.
- **Docs**: `UPPERCASE_TOPIC.md`.

---

## 7. Developer Rules: Where to add things
| Requirement | Action |
| :--- | :--- |
| **New API Endpoint** | 1. Schema, 2. Service Logic, 3. Router, 4. Frontend API call. |
| **New Database Table** | 1. Model, 2. Schema, 3. Update `models/__init__.py`. |
| **New Frontend Page** | 1. Component in `/pages`, 2. Route in `App.jsx`. |
| **New Reusable UI** | Component in `/components`. |
| **New Test** | File in `backend/tests` or `frontend/tests`. |

---

## 8. What NOT to do
- **Logic in Routers**: Routers should only handle request parsing and calling services.
- **Secret Leaks**: Never hardcode keys; use `config.py` and `.env`.
- **Direct DB calls in UI**: All data must flow through the API.
- **Bloated Components**: Keep UI components small and focused.
