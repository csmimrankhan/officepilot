# Backup and Restore

## Overview

OfficePilot AI provides local database backup and restore testing capabilities.
This is **not** a cloud backup solution — backups are stored on the local
filesystem and must be managed by the operations team.

## Backup Location

Backups are stored in `{data_dir}/backups/` as SQLite database files with
timestamps in the filename (e.g., `officepilot_backup_20260607_120000.db`).

## How to Backup

### API

- `GET /api/backup/status` — View backup status, last backup time, disk space
- `POST /api/backup/run-local` — Create a new local backup
- `POST /api/backup/test-restore` — Test restoring the latest backup

### Production Readiness Page

1. Open the Production Readiness page.
2. Scroll to the Backup Status section.
3. Click **Run Backup** to create a backup.
4. Click **Test Restore** to verify backup integrity.

## Restore Testing

The restore test:
1. Finds the most recent backup file.
2. Restores it to a temporary SQLite database.
3. Verifies the restored database has valid tables.
4. Reports pass/fail status.

This test does not overwrite the live database.

## Disk Space Warning

The system will warn if free disk space drops below 1 GB. Always ensure
sufficient free space for backups to complete successfully.

## Limitations

- Local filesystem only — no cloud or network backup support.
- No automated scheduling — backups must be triggered manually or via cron.
- No incremental backups — each backup is a full database copy.
