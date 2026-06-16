# Local Cleanup & Data Retention (Phase 21)

## Safety Rules

Cleanup **never** removes:
- Real invoices
- Real audit logs
- Real accounting sync logs
- Backups
- Version history (entity_versions, workflow_versions, file_snapshots)

Cleanup **may** remove:
- Old demo walkthrough data (>30 days, completed only)
- Old bug report packages (>50 packages, oldest removed)
- Old audit export packages (>50 exports, oldest removed)
- Old bug report records (>90 days)
- Excess usage events (>10,000 events, oldest removed)

## Endpoints

### Storage Usage
```
GET /api/system/storage-usage
```
Returns sizes and file counts for: bug_reports, audit_exports, browser_screenshots, cache_dir, demo_invoices.

### Cleanup Preview
```
GET /api/system/cleanup-preview
```
Shows what would be removed without actually removing it. Returns a list of items with type, path, size, and reason.

### Run Cleanup
```
POST /api/system/cleanup-run
Body: { "confirmed": true }
```
Performs the actual cleanup. Requires `confirmed=true`. Returns a summary of what was removed.

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `LOG_RETENTION_DAYS` | 90 | Bug report records older than this are deleted |
| `DEMO_DATA_RETENTION_DAYS` | 30 | Completed demo walkthroughs older than this are deleted |
| `MAX_AUDIT_EXPORTS` | 50 | Only keep this many audit export files |
| `MAX_BUG_REPORT_PACKAGES` | 50 | Only keep this many bug report package files |

## Testing Cleanup

1. `GET /api/system/storage-usage` — verify storage stats
2. `GET /api/system/cleanup-preview` — verify what would be removed
3. Confirm no real invoices in the preview
4. `POST /api/system/cleanup-run` with `confirmed=true`
5. Verify only safe files were removed
6. `GET /api/system/storage-usage` again — verify reduced usage
