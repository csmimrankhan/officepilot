# Pilot Readiness

## Overview
The Pilot Readiness checklist ensures all critical features are working before inviting pilot users.

## Checklist Steps
1. Owner account created
2. Demo data loaded
3. Sample invoice approved
4. Excel export tested
5. Audit log viewed
6. Backup tested
7. Kill switch tested
8. Readiness dashboard reviewed (green/yellow)
9. Feedback button tested
10. Bug report tested

## Usage Tracking
- All events are tracked locally only
- No external analytics or cloud telemetry
- Tracking can be disabled via `USAGE_TRACKING_ENABLED=false`

## How to Verify Readiness
1. Navigate to Pilot → Pilot Readiness
2. Complete each step
3. The "Ready for pilot demo" badge will activate when all required steps are done

## API Endpoints
- GET /api/pilot/readiness
- POST /api/pilot/readiness/complete-step
- POST /api/pilot/readiness/reset
- POST /api/usage/events
- GET /api/usage/summary
- GET /api/usage/events
