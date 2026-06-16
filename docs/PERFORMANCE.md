# OfficePilot AI — Performance & Resource Guide

> **Last updated:** 2026-06-15 (Phase 38.5)

## Expected Performance

| Operation | Typical Time | Notes |
|-----------|-------------|-------|
| **Frontend dev build** | ~8-10s | `npm run build` (Vite, ~1889 modules) |
| **Frontend test suite** | ~45-60s | 498 tests across 27 files |
| **Backend test suite (unit)** | ~3-5s | 104 unit tests (Phase 23C + automation + voice) |
| **Backend test suite (full)** | ~8-10 min | ~1110 tests (full regression) |
| **Python sidecar build** | ~2-3 min | PyInstaller bundling |
| **Tauri build (Rust release)** | ~4-5 min | MSI + NSIS installers |
| **Whisper transcription (ggml-small.bin, ~500MB)** | ~2-10s | CPU-only, depends on audio length |
| **Whisper transcription (ggml-base.en.bin, ~150MB)** | ~1-5s | CPU-only, English only |
| **LLM plan generation (Ollama, Llama 3.1 8B)** | ~3-8s | Local CPU, depends on model size |
| **LLM plan generation (cloud API)** | ~1-3s | OpenAI/DeepSeek, depends on network |

## Resource Usage

| Resource | Typical | Peak |
|----------|---------|------|
| **RAM (backend)** | ~150-300 MB | ~500 MB (large Excel files) |
| **RAM (frontend dev)** | ~200-400 MB | ~600 MB |
| **RAM (whisper.cpp, ggml-small.bin)** | ~1.2-1.5 GB | ~2 GB |
| **RAM (whisper.cpp, ggml-base.en.bin)** | ~400-600 MB | ~800 MB |
| **RAM (Ollama + Llama 3.1 8B)** | ~4-6 GB | ~8 GB |
| **Disk (base install)** | ~1 GB | Sidecar ~150 MB + Tauri ~6 MB |
| **Disk (whisper models)** | 75-500 MB | Based on model size |
| **Disk (Ollama models)** | ~4-8 GB | Per model |
| **Disk (data dir)** | 50-500 MB | Invoices, exports, snapshots, logs |
| **CPU** | Low (<5%) idle | Up to 100% on 1-2 cores during transcription/LLM |

Note: Running both Ollama (local LLM) and whisper.cpp simultaneously on an i5/8GB machine
will cause significant memory pressure. On such machines, use the mock provider (no LLM)
or the cloud provider instead of local Ollama.

## Whisper Model Sizes

| Model | Size | Languages | Accuracy | Recommended For |
|-------|------|-----------|----------|-----------------|
| `ggml-tiny.en.bin` | ~75 MB | English only | Low | Quick tests |
| `ggml-base.en.bin` | ~150 MB | English only | Medium | English-only users |
| `ggml-small.bin` | ~500 MB | 100+ languages | High | Multilingual users (default) |
| `ggml-small.en.bin` | ~500 MB | English only | High | English-only, better accuracy |

## Transcription Latency

Transcription latency is logged by the backend. Check the logs for lines like:
```
whisper.cpp transcription took 3.45s (model: 500MB, audio: C:\...\voice_1234567890.wav)
```

If transcription takes >10 seconds, consider:
- Using a smaller model (`ggml-base.en.bin` if English-only)
- Reducing audio length (default max 30s)
- Checking CPU usage (whisper.cpp is CPU-only)
- Using a faster machine (SSD recommended, whisper reads the full model into memory)

## LLM Provider Latency

| Provider | Plan Generation | Notes |
|----------|----------------|-------|
| **Mock** | <10ms | Keyword-based, no network |
| **Cloud (DeepSeek/OpenAI)** | 1-3s | Requires internet; rate-limited by API |
| **Local (Ollama, Llama 3.1 8B)** | 3-8s | CPU-dependent; faster with GPU |
| **Local (Ollama, Mistral 7B)** | 2-5s | Smaller model, slightly less capable |

## Recommendations

- **Minimum hardware**: i5 8th gen, 8 GB RAM, SSD
- **Recommended**: i7 10th gen, 16 GB RAM, SSD
- **Better**: any modern CPU, 16+ GB RAM, optional GPU (for Ollama)
- **For multilingual use**: `ggml-small.bin` (500 MB model, ~2-10s transcription)
- **For English-only use**: `ggml-base.en.bin` (150 MB model, ~1-5s transcription)
- **For offline LLM**: Ollama + Llama 3.1 8B (needs ~6 GB RAM free)
- **For low-RAM machines**: Mock provider + `ggml-base.en.bin` (no LLM overhead)
