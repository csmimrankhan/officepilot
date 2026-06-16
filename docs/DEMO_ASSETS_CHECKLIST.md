# Demo Assets Checklist

Screenshots to capture for the OfficePilot AI landing page and demo materials.

## Prerequisites

- Run app in demo mode: `DEMO_MODE=true`
- Seed sample invoice data (at least 4-5 invoices in various states)
- Browser window at 1280x800 viewport
- No real invoice data in screenshots

## Screenshot List

### 1. Invoice Review Queue
- **File**: `marketing/screenshot_invoice_review.png`
- **Description**: Review Queue page with extracted invoices, confidence scores, Approve/Reject buttons
- **Show**: 4+ invoices with mixed confidence (high, medium, low)
- **Status**: ⬜ Not captured

### 2. Excel Export Preview
- **File**: `marketing/screenshot_excel_export.png`
- **Description**: Export page with preview table and column mappings
- **Show**: 3-4 invoice rows in the preview, highlight column mapping section
- **Status**: ⬜ Not captured

### 3. Accounting Sync Preview
- **File**: `marketing/screenshot_accounting_sync.png`
- **Description**: Accounting sync modal with draft journal entries
- **Show**: Entry details, vendor name, amount, Approve/Reject buttons
- **Status**: ⬜ Not captured

### 4. Audit Log & Version History
- **File**: `marketing/screenshot_audit_restore.png`
- **Description**: Two-panel layout — audit log timeline + version history card
- **Show**: Restore action with reason highlighted
- **Status**: ⬜ Not captured

### 5. Safety Policy Center
- **File**: `marketing/screenshot_safety_policy.png`
- **Description**: Policy toggles, kill switch status, permissions grid
- **Show**: 5 policy toggle cards, global kill switch at top, permissions table
- **Status**: ⬜ Not captured

### 6. Screen Assistant with Voice
- **File**: `marketing/screenshot_voice_screen.png`
- **Description**: Screen Assistant panel with active window context
- **Show**: Panel docked to right, detected window name, action buttons
- **Status**: ⬜ Not captured

## After Capturing

1. Update `frontend/public/landing.html` to reference the actual images
2. Update the in-app `MarketingAssets.jsx` page with screenshot previews
3. Add alt text for accessibility
4. Optimize images for web (~1200px width, JPEG or WebP)
