# Feedback Capture

## How to Submit Feedback

1. Click the "Feedback" button in the sidebar
2. Select a feedback type
3. Enter a title and message
4. Select severity
5. Click Submit

## Feedback Types
- bug — Something is broken
- confusing_ux — Feature is hard to use
- extraction_mistake — Invoice fields were extracted incorrectly
- missing_feature — Something the product doesn't do yet
- performance_issue — Feature is slow or unresponsive
- security_concern — Something doesn't feel secure
- general_feedback — Anything else

## Viewing Feedback (Admin)
- Navigate to Pilot → Feedback Inbox
- Filter by status or type
- Update status as you triage

## API Endpoints
- POST /api/feedback
- GET /api/feedback
- GET /api/feedback/{id}
- PATCH /api/feedback/{id}
