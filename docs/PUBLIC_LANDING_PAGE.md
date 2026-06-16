# Public Landing Page

## Purpose

A professional landing page that explains what OfficePilot AI is, who it's for,
and how to join the pilot program. Serves as the first impression for potential
users.

## Components

### Static HTML (`frontend/public/landing.html`)

Standalone HTML page served by Vite at `/landing.html`. No React build step
required. Works without JavaScript enabled for basic viewing.

**Sections:**
1. **Hero** — Title, subtitle, CTA buttons
2. **Problem** — 3 cards (manual data entry, email chaos, no audit trail)
3. **How It Works** — 4-step numbered workflow
4. **Demo Walkthrough** — Brief description + screenshot placeholder
5. **Safety & Trust** — 5 badge cards
6. **FAQ** — 11 collapsible questions
7. **Waitlist Form** — Name, email, company, role, invoice volume
8. **Footer** — GitHub, Docs, License links

### In-App React Page (`/welcome`)

Mirror of the landing page for authenticated users to reference.

## Key Decisions

- Static HTML file avoids React dependency for the public-facing page
- Waitlist form POSTs directly to `/api/public/waitlist` via `fetch`
- Page events recorded via `/api/public/page-event`
- No external CSS/JS dependencies — all inline
- Mobile-responsive via media queries

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/public/waitlist` | None | Submit waitlist signup |
| POST | `/api/public/page-event` | None | Record page view/tracking event |

## Target Audience

- Potential pilot users evaluating the product
- Visitors from GitHub or documentation links
- Anyone who wants to understand what OfficePilot does before downloading
