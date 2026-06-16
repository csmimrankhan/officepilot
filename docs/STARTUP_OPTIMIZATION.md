# Startup Optimization (Phase 21)

## Measuring Startup Time

### Metrics Endpoint

```
GET /api/system/startup-metrics
```

Returns:
```json
{
  "marks": {
    "process_start": 1748000000.123,
    "lifespan_started": 1748000000.456,
    "backend_ready": 1748000002.789
  },
  "elapsed": {
    "lifespan_started": 0.333,
    "backend_ready": 2.666
  },
  "total_startup_seconds": 2.666
}
```

### Health Endpoint

`GET /api/health` now includes `startup_seconds` field.

## Cold Start Optimization

### Before Optimization

- All parser engines imported at module load
- PaddleOCR/Tesseract loaded even if not used
- Playwright imported even if browser automation disabled
- Accounting SDK imports on every startup

### After Optimization

- Parser engines loaded lazily on first parse request via `_ensure_engines()`
- Playwright imported only when first browser action runs
- Screen OCR dependencies deferred until first capture
- All heavy imports moved inside try/except in lifespan hooks

## Measuring Cold Start

1. Start the app with `python -m uvicorn app.main:app`
2. Observe the startup log line: `startup=2.66s`
3. Hit `GET /api/system/startup-metrics` for detailed breakdown
4. Hit `GET /api/health` to confirm fast response (< 100ms)

## Sidecar Startup (Desktop)

The Tauri supervisor records these additional timing marks:

| Mark | Description |
|------|-------------|
| `sidecar_launch_started` | Tauri spawns sidecar process |
| `sidecar_port_open` | Sidecar TCP port is accepting connections |
| `frontend_ready` | Tauri WebView has finished loading |

## Known Limits

- Python import overhead is ~0.5-1.5s depending on installed packages
- First request to parser endpoint may be slower due to lazy loading
- Cold start on HDD vs SSD differs significantly
