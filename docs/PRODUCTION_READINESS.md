# Production Readiness

## Dashboard

The Production Readiness dashboard provides a real-time status overview of all
critical system components. Each component is shown with a green/yellow/red
status indicator.

## Components Checked

| Component | Description |
|-----------|-------------|
| Backend Process | Is the server process running |
| Database | Is the database reachable and responding |
| Storage Path | Does the data directory exist |
| Disk Space | Free disk space (warning if < 1 GB) |
| Safety Policy | Which risky features are enabled |
| Kill Switch | Is the global kill switch active |
| OCR Engine | Is Tesseract installed and working |
| Playwright | Is Playwright available for browser automation |
| Gmail | Is Gmail integration configured |
| Accounting | Are QuickBooks/Xero credentials configured |
| Audit Exports | Last successful audit export timestamp |

## Interpreting Status

- **Green**: Component is healthy and properly configured.
- **Yellow**: Component is functional but has a warning (e.g., risky feature
  enabled, not configured).
- **Red**: Component has a critical issue that must be addressed.

## How to Test

1. Open the Production Readiness page.
2. Review each component status card.
3. Click "Refresh" to update.
4. Address any red items before relying on the system.
