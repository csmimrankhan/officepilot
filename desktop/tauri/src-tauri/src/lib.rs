//! OfficePilot AI — Tauri desktop shell library entry point.
//!
//! Phase 8 — wires the system tray, the agent supervisor
//! (bundled sidecar by default, system Python in dev), and a
//! small set of ``#[tauri::command]`` entry points the React UI
//! can call. The Tauri ``Builder::on_window_event`` keeps the
//! existing close-to-tray behaviour from Phase 7.
//!
//! Phase 28 — adds global shortcut plugin for voice layer:
//!   Ctrl+Alt+Space = Dictation mode
//!   Ctrl+Alt+A     = AI Mode
//!   Ctrl+Alt+O     = Agent command mode

mod agent;
mod tray;

use std::sync::Arc;
use std::fs::OpenOptions;
use std::io::Write;
use parking_lot::Mutex;
use serde::Serialize;
use tauri::{Emitter, Manager};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState as PluginShortcutState};

/// Debug log: writes a line to %TEMP%\officepilot-debug.log
fn debug_log(msg: &str) {
    let path = std::env::temp_dir().join("officepilot-debug.log");
    if let Ok(mut f) = OpenOptions::new().create(true).append(true).open(&path) {
        let stamp = chrono::Local::now().format("%Y-%m-%d %H:%M:%S.%3f");
        let _ = writeln!(f, "[{}] {}", stamp, msg);
    }
}

/// Shared state for tracking registered shortcut keys.
#[derive(Default, Serialize, Clone)]
pub struct ShortcutRegistrations {
    pub dictation_registered: bool,
    pub ai_mode_registered: bool,
    pub agent_registered: bool,
}

pub type SharedShortcutState = Arc<Mutex<ShortcutRegistrations>>;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info"))
        .init();

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        // Auto-update plugin (Phase 9 hardening). The plugin
        // itself is wired in unconditionally; the React layer
        // is responsible for *not* calling ``check()`` on launch
        // until a real manifest endpoint is configured (see
        // ``plugins.updater`` in ``tauri.conf.json``). The
        // plugin is built with no auto-check behaviour, so a
        // missing manifest only matters if the UI asks for one.
        .plugin(tauri_plugin_updater::Builder::new().build())
        .invoke_handler(tauri::generate_handler![
            agent::get_agent_status,
            agent::request_agent_restart,
            agent::request_agent_retry,
            agent::get_agent_logs,
            agent::reveal_sidecar_logs,
            cmd_shortcut_state,
        ])
        .setup(|app| {
            // Bring the main window to the front on launch.
            if let Some(w) = app.get_webview_window("main") {
                let _ = w.show();
                let _ = w.set_focus();
            }
            // Build the system tray.
            tray::build_tray(&app.handle())?;
            // Start the agent supervisor (bundled sidecar by
            // default, system Python when USE_SYSTEM_PYTHON_AGENT
            // is set).
            agent::spawn_supervisor(app.handle().clone());

            // ── Phase 28: Register global shortcuts ──────────
            let shortcut_state: SharedShortcutState = Arc::new(Mutex::new(ShortcutRegistrations::default()));
            app.manage(shortcut_state.clone());

            register_voice_shortcuts(app)?;

            // ── Phase 36B: Updater diagnostic ──────────────
            tauri::async_runtime::spawn(async move {
                tokio::time::sleep(std::time::Duration::from_secs(15)).await;
                debug_log(&format!(
                    "DIAG: startup complete (pid={})",
                    std::process::id()
                ));

                // 1. Test HTTPS with default TLS (should use rustls-platform-verifier)
                let client = match reqwest::Client::builder().build() {
                    Ok(c) => c,
                    Err(e) => {
                        debug_log(&format!("DIAG: reqwest build failed: {}", e));
                        return;
                    }
                };
                let url = "https://localhost:8766/api/app/updater/windows/stable";
                debug_log(&format!("DIAG: HTTPS GET {}", url));
                match client.get(url).send().await {
                    Ok(resp) => {
                        debug_log(&format!(
                            "DIAG: HTTPS OK status={}", resp.status()
                        ));
                    }
                    Err(e) => {
                        debug_log(&format!("DIAG: HTTPS FAILED: {:?}", e));
                        // Insecure fallback to distinguish TLS from network errors
                        match reqwest::Client::builder()
                            .danger_accept_invalid_certs(true)
                            .build()
                        {
                            Ok(ic) => {
                                match ic.get(url).send().await {
                                    Ok(r) => debug_log(&format!("DIAG: HTTPS (insecure) OK status={}", r.status())),
                                    Err(e2) => debug_log(&format!("DIAG: HTTPS (insecure) FAILED: {:?}", e2)),
                                }
                            }
                            Err(e2) => debug_log(&format!("DIAG: insecure build failed: {}", e2)),
                        }
                        // Control: HTTP
                        let http_url = "http://localhost:8766/api/app/updater/windows/stable";
                        match client.get(http_url).send().await {
                            Ok(r) => debug_log(&format!("DIAG: HTTP OK status={}", r.status())),
                            Err(e2) => debug_log(&format!("DIAG: HTTP FAILED: {:?}", e2)),
                        }
                    }
                }
                debug_log("DIAG: complete");
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            // Close → hide instead of quit. The tray menu's
            // "Exit" entry is the only way to actually quit the
            // app. This is the standard behaviour for a
            // background-style app and matches the requirement
            // that the agent keeps running until the user
            // explicitly quits.
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                if window.label() == "main" {
                    let _ = window.hide();
                    api.prevent_close();
                }
            }
        })
        .build(tauri::generate_context!())
        .expect("error while running OfficePilot AI desktop shell");

    // Safe shutdown: when the OS / tray "Exit" triggers an
    // app exit, kill the sidecar so we do not leak a Python
    // process.
    app.run(|app_handle, event| {
        if let tauri::RunEvent::ExitRequested { .. } = &event {
            if let Some(state) = app_handle.try_state::<agent::SharedState>() {
                agent::stop_agent(&state);
            }
        }
    });
}

/// Register all three voice shortcuts.
fn register_voice_shortcuts(app: &tauri::App) -> Result<(), Box<dyn std::error::Error>> {
    let shortcuts = [
        ("dictation", Modifiers::CONTROL | Modifiers::ALT, Code::Space),
        ("ai_mode", Modifiers::CONTROL | Modifiers::ALT, Code::KeyA),
        ("agent_command", Modifiers::CONTROL | Modifiers::ALT, Code::KeyO),
    ];

    let state: tauri::State<SharedShortcutState> = app.state::<SharedShortcutState>();

    for (mode, mods, code) in &shortcuts {
        let shortcut = Shortcut::new(Some(*mods), *code);
        let mode_name = *mode;
        match app.global_shortcut().on_shortcut(shortcut, move |app_handle, _shortcut, event| {
            if event.state == PluginShortcutState::Pressed {
                log::info!("global shortcut pressed: {}", mode_name);
                if let Some(w) = app_handle.get_webview_window("main") {
                    let _ = w.show();
                    let _ = w.unminimize();
                    let _ = w.set_focus();
                }
                let _ = app_handle.emit("voice://shortcut", serde_json::json!({
                    "mode": mode_name,
                }));
            }
        }) {
            Ok(_) => {
                log::info!("registered shortcut: {} ({:?}+{:?})", mode, mods, code);
                let mut s = state.lock();
                match mode_name {
                    "dictation" => s.dictation_registered = true,
                    "ai_mode" => s.ai_mode_registered = true,
                    "agent_command" => s.agent_registered = true,
                    _ => {}
                }
            }
            Err(e) => {
                log::warn!("failed to register shortcut {}: {}", mode, e);
            }
        }
    }

    Ok(())
}

/// Tauri command: return the current shortcut registration state.
#[tauri::command]
fn cmd_shortcut_state(state: tauri::State<SharedShortcutState>) -> ShortcutRegistrations {
    state.lock().clone()
}
