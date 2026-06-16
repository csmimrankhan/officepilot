# Multilingual Voice Test Plan

> **Last updated:** 2026-06-15  
> **Scope:** End-to-end validation of the universal language pipeline

## Prerequisites

1. Multilingual Whisper model (`ggml-small.bin`) — download via Voice Settings UI or:
   ```
   cd backend && python -c "from app.services.windows_voice_layer import download_model; print(download_model('ggml-small.bin'))"
   ```
2. Whisper CLI (`whisper-cli.exe`) — bundled with the Tauri app or in PATH
3. Agent provider configured for multilingual understanding:
   - **Mock provider** (default): English, French, Spanish, German Excel-downloads commands
   - **Local LLM** (Ollama): `set AGENT_PROVIDER=local` + `set AGENT_MODEL=llama3.1`
   - **Cloud LLM**: `set AGENT_PROVIDER=openai_compatible` + `set AGENT_ALLOW_CLOUD=true`

## Test Cases

### TC-1: English Voice → Excel Summary

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Click microphone button | Recording starts, pulsing red dot appears |
| 2 | Say: "Create a summary of the parcel lab Excel in downloads" | Recording stops automatically or on Stop button |
| 3 | Wait for transcription | "Transcribing..." spinner appears, then transcript shows |
| 4 | Check the generated plan | Plan type: `excel_summary_from_downloads`, steps: `file_find_in_downloads` → `excel_create_summary_from_file` |
| 5 | Approve the plan | Execution runs, file picker appears for multiple files |

### TC-2: French Voice → Excel Summary

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Click microphone button | Recording starts |
| 2 | Say: "Crée un résumé du fichier excel dans téléchargements" | |
| 3 | Wait for transcription | Transcript shows the French text |
| 4 | Check the generated plan | Same as TC-1 (plan type independent of language) |
| 5 | Verify French keywords in mock mode | `detect_language_simple()` returns `"french"` |

### TC-3: Spanish Voice → Excel Summary

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Click microphone button | Recording starts |
| 2 | Say: "Crear un resumen del archivo de excel en descargas" | |
| 3 | Wait for transcription | Transcript shows the Spanish text |
| 4 | Check the generated plan | Same as TC-1 |

### TC-4: German Voice → Excel Summary

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Click microphone button | Recording starts |
| 2 | Say: "Erstellen Sie eine Zusammenfassung der Excel-Datei in Downloads" | |
| 3 | Wait for transcription | Transcript shows the German text |
| 4 | Check the generated plan | Same as TC-1 |

### TC-5: Roman Urdu Voice (English keywords) → Excel Summary

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Click microphone button | Recording starts |
| 2 | Say: "Download folder mein parcel lab ki file ko read karo aur uski samri mujhe batao" | |
| 3 | Wait for transcription | Transcript shows the Roman Urdu / mixed text |
| 4 | Check the generated plan | Same as TC-1 |

### TC-6: Blocked Command (Safety Gate)

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Say: "Transfer money to vendor" | Plan shows `risk_level: "blocked"` |
| 2 | Check the response | Blocked reason displayed, no steps |

### TC-7: Navigation Command

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Say: "Open voice command center" | Navigation plan returned, frontend navigates to `/voice` |
| 2 | Say: "Open settings" | Navigation to `/app/settings` |

### TC-8: Transcription Latency

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Start recording, speak for ~5 seconds | Check backend logs for: `whisper.cpp transcription took X.XXs` |
| 2 | Expected time with `ggml-small.bin` | ~2-10 seconds (CPU dependent) |
| 3 | Expected time with `ggml-base.en.bin` | ~1-5 seconds |

## Smoke Test (Backend)

Run the automated smoke test that simulates transcribed text in multiple languages:

```python
# backend/tests/test_multilingual_smoke.py
# Tests that build_accountant_plan() handles French/Spanish/German
# via the mock provider's keyword detection
```

Execution:
```
cd backend && python -m pytest tests/test_multilingual_smoke.py -v
```

## Logging Output

Check for these log lines during testing:

| Log Line | Meaning |
|----------|---------|
| `whisper.cpp transcription took X.XXs` | Transcription latency |
| `Mock provider matched Excel downloads (lang=french)` | Language detected by mock provider |
| `detect_language_simple: '...' -> french (score=4)` | Language detection heuristic |
| `Cloud agent call failed: ...` | Cloud LLM error |
| `Local LLM call failed: ...` | Local LLM error |

## Known Issues

- Whisper `ggml-small.bin` may take 2-10s on CPU-only machines
- Mock provider only supports English/French/Spanish/German for Excel downloads
- Roman Urdu detection (`detect_language_simple`) requires 3+ cue words
- Mock transcription returns a placeholder; real whisper.cpp required for actual STT
