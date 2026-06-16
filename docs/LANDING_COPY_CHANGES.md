# Landing Page Copy Changes

Documenting all copy improvements made during Phase 22 (Pilot Demo Videos, Outreach, Landing Polish).

## Frontend Files Changed

### `frontend/public/landing.html`

| Change | Before | After |
|--------|--------|-------|
| CTA Button | "Join the Pilot" | "Join the Early Pilot Program" |
| Hero subtitle | "Your safe AI office worker for invoices, Excel, email, and accounting." | "A safe AI office worker for accountants, bookkeepers, and admin teams." |
| Waitlist pitch | "Be among the first to use OfficePilot AI. Submit your details and we'll reach out with early access information." | "Try OfficePilot free during our early pilot program. No credit card needed. Sample data included so you can explore before using your own invoices." |

### `frontend/src/pages/Landing.jsx`

| Change | Before | After |
|--------|--------|-------|
| Hero subtitle | "Turn invoice emails into Excel and accounting records — with approval, audit logs, and restore." | "Turn invoice emails into Excel and accounting records — with approval, audit logs, and restore. Built for accountants, bookkeepers, and admin teams." |
| CTA Button | "Join the Waitlist" | "Join the Early Pilot Program" |
| Section header | "Get Early Access" | "Join the Early Pilot Program" |
| Form submit | "Join the Waitlist" | "Join the Early Pilot Program" |

### `frontend/src/pages/FAQPage.jsx`

| Change | Before | After |
|--------|--------|-------|
| "Is my data safe?" answer | Generic safety description | "Your team controls every button through approval gates and role-based permissions. Snapshots are taken before every mutation, and a global kill switch can halt all automation instantly." |
| Added new FAQ | — | "What makes OfficePilot different from other invoice tools?" — explains local-first, approval gates, version history, kill switch |

### `frontend/src/pages/DemoScript.jsx`

| Change | Before | After |
|--------|--------|-------|
| Pilot CTA banner | (none) | Blue banner at top: "Want to try OfficePilot? Join the early pilot program — free, no credit card, sample data included. Sign up or learn more." |

### `frontend/src/pages/ProductPositioning.jsx`

No changes — content was already solid and consistent with Phase 22 positioning.

## Copy Principles Applied

- **CTA clarity**: Changed from generic "Join the Pilot" / "Join the Waitlist" to specific "Join the Early Pilot Program" — sets clearer expectations
- **Target user naming**: Added "accountants, bookkeepers, and admin teams" directly in hero subtitle so visitors immediately know if it's for them
- **Safety positioning**: Strengthened data safety FAQ with "Your team controls every button" language — addresses the core trust question directly
- **Differentiation**: New FAQ "What makes OfficePilot different from other invoice tools?" — gives visitors a concise why-choose-us answer
- **Demo page conversion**: Added pilot CTA banner at top of demo script page — captures interested demo visitors who want to try
- **Waitlist pitch**: Changed from generic "be among the first" to specific value proposition "free during pilot, no credit card, sample data included" — reduces friction

## One-Liner (unchanged)

"OfficePilot AI turns invoice emails and PDFs into Excel and accounting drafts, with approval, audit logs, and restore."
