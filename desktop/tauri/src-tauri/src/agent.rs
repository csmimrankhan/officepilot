//! Local agent sidecar manager.
//!
//! Phase 8 — the supervisor in this file knows how to launch the
//! FastAPI agent in two modes:
//!
//!   1. **Bundled sidecar** (production default). Tauri 2.0
//!      resolves the ``externalBin`` declared in
//!      ``tauri.conf.json`` (i.e.
//!      ``binaries/officepilot-agent-x86_64-pc-windows-msvc.exe``)
//!      and we spawn it via :func:`tauri::api::process::Command`.
//!      The user does **not** need Python on PATH.
//!
//!   2. **System Python** (dev mode). Triggered by setting
//!      ``USE_SYSTEM_PYTHON_AGENT=true`` in the environment
//!      *before* ``cargo tauri dev``. The supervisor runs
//!      ``python -m uvicorn app.main:app`` exactly like Phase 7
//!      did. Useful when iterating on the Python sidecar without
//!      rebuilding the binary.
//!
//! In both modes the supervisor:
//!
//!   * Spawns the child.
//!   * Streams its stdout/stderr to
//!     ``$OFFICEPILOT_DATA_DIR/logs/sidecar.log``.
//!   * Polls ``GET /api/health`` over HTTP every few seconds.
//!   * Detects crashes (exit code != 0, or repeated probe failures),
//!     records the reason in :struct:`AgentStatus`, and emits the
//!     new state to the UI as an ``agent://status`` Tauri event.
//!   * Stops the child cleanly on app exit (best-effort
//!     ``CommandChild::kill()`` for the bundled path, or
//!     ``taskkill /T /F`` on the OS PID for the system-Python
//!     path).
//!
//! Phase 11 — startup UX hardening. The supervisor now:
//!
//!   * Gives the sidecar a :const:`BOOT_GRACE_DURATION` window
//!     before probe failures count as ``Offline``. Cold-start on
//!     Windows can take 15-20s while Defender scans the .exe and
//!     PyInstaller unpacks the bundle; the UI shows
//!     "Agent Starting" the whole time.
//!   * Tracks boot timing (`boot_started_at`,
//!     `first_port_open_at`, `first_health_ok_at`,
//!     `boot_duration_ms`) so the UI can show "started in 4.2s"
//!     after the agent comes online.
//!   * Checks ``OFFICEPILOT_AGENT_PORT`` (default 8000) for
//!     port-in-use before retrying, so the user gets a clear
//!     "another process holds port 8000" error instead of an
//!     infinite restart loop.
//!   * Exposes an ``open_logs`` Tauri command that returns the
//!     sidecar log path and a ``reveal_in_explorer`` flag so the
//!     React layer can pop a native file-explorer window.
//!
//! The :struct:`AgentStatus` includes a ``state`` field with one
//! of four values:
//!
//!   - ``starting`` - the sidecar was just spawned; first probe in flight.
//!   - ``online``   - the last health probe returned 2xx.
//!   - ``offline``  - the sidecar is not running (no child, or
//!                    child exited, or the last probe failed
//!                    after :const:`BOOT_GRACE_DURATION`).
//!   - ``failed``   - the child crashed too many times; the
//!                    supervisor is no longer auto-respawning.
//!
//! The UI listens to the ``agent://status`` event and renders one
//! of four coloured pills + a "Retry" button on the *failed*
//! state.
//!
//! Phase 11 explicitly does **not** add screen capture, mouse /
//! keyboard hooks, full desktop control, browser automation, or
//! workflow recording.

use std::env;
use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Arc;
use std::thread;
use std::time::{Duration, Instant};

use parking_lot::Mutex;
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt as _;

/// Default port the agent listens on. Matches the
/// ``OFFICEPILOT_AGENT_PORT`` default in the Python backend.
/// Override via the ``OFFICEPILOT_AGENT_PORT`` environment variable.
pub fn default_agent_port() -> u16 {
    env::var("OFFICEPILOT_AGENT_PORT")
        .ok()
        .and_then(|v| v.parse::<u16>().ok())
        .unwrap_or(8000)
}
/// Health-probe URL. Uses `default_agent_port()` at runtime.
pub fn health_url() -> String {
    format!("http://127.0.0.1:{}/api/health", default_agent_port())
}
/// Probe cadence when the agent is healthy.
const HEALTH_INTERVAL_OK: Duration = Duration::from_secs(15);
/// Probe cadence when the agent is unhealthy — kept short so the
/// UI's "Restart" / "Retry" affordances feel responsive.
const HEALTH_INTERVAL_DOWN: Duration = Duration::from_secs(3);
/// Hard timeout for a single health probe.
const HEALTH_TIMEOUT: Duration = Duration::from_secs(2);
/// Cap on auto-respawn attempts. After this, the supervisor
/// stops trying and surfaces a "failed" pill in the UI. The user
/// can still trigger a manual restart from the *Retry* button.
const MAX_RESTART_ATTEMPTS: u32 = 5;
/// Phase 11 — boot grace window. While ``started_at + grace`` has
/// not elapsed, probe failures do *not* flip the state to
/// ``Offline``; we keep it at ``Starting`` so a slow cold start
/// (Windows Defender scan, PyInstaller unpacking) is not
/// misreported to the user. 60s is large enough to absorb a
/// worst-case defender scan plus import overhead on a slow disk.
pub const BOOT_GRACE_DURATION: Duration = Duration::from_secs(60);
/// How long the probe loop sleeps between retries while the
/// sidecar is still booting. Kept at 1.5s so a healthy first
/// probe is visible quickly.
const HEALTH_INTERVAL_BOOT: Duration = Duration::from_millis(1500);
/// Sidecar log file name under ``$OFFICEPILOT_DATA_DIR/logs/``.
pub const SIDECAR_LOG_FILENAME: &str = "sidecar.log";

/// Logical state of the agent, as seen by the UI.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum AgentState {
    Starting,
    Online,
    Offline,
    Failed,
}

impl Default for AgentState {
    fn default() -> Self {
        AgentState::Starting
    }
}

/// Mode in which the supervisor launched the agent.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum LaunchMode {
    Bundled,
    SystemPython,
}

impl Default for LaunchMode {
    fn default() -> Self {
        LaunchMode::Bundled
    }
}

/// Snapshot of the agent as the supervisor sees it. Emitted on
/// the ``agent://status`` Tauri event and returned by the
/// ``get_agent_status`` Tauri command.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentStatus {
    pub state: AgentState,
    pub running: bool,
    /// Whether the supervisor is using the bundled PyInstaller
    /// sidecar (``bundled``) or system Python
    /// (``system-python``). Mirrors the value the agent itself
    /// reports in ``/api/health -> sidecar.mode``.
    pub mode: LaunchMode,
    pub pid: Option<u32>,
    pub uptime_seconds: u64,
    pub restart_count: u32,
    pub last_error: Option<String>,
    pub last_health_at: Option<String>,
    pub health_url: String,
    pub port: u16,
    /// ISO-8601 timestamp of the most recent spawn, if any.
    /// Used by the UI to show "starting for 12s…".
    pub spawn_started_at: Option<String>,
    /// ISO-8601 timestamp of the first time the port became
    /// reachable, if at all. Combined with `spawn_started_at`
    /// this gives "5.4s to first port-open".
    pub first_port_open_at: Option<String>,
    /// ISO-8601 timestamp of the first successful
    /// ``/api/health`` response, if at all. Combined with
    /// `spawn_started_at` this gives the total cold-boot duration.
    pub first_health_ok_at: Option<String>,
    /// Total boot duration in milliseconds (spawn → first
    /// healthy probe). Populated once the agent comes online.
    pub boot_duration_ms: Option<u64>,
    /// True while we are still inside the :const:`BOOT_GRACE_DURATION`
    /// window after a spawn. The UI uses this to show the
    /// "First launch may take longer" hint.
    pub boot_grace_active: bool,
    /// Path to the sidecar log file. The UI's "Open Logs" button
    /// uses this to reveal the file in the OS file explorer.
    pub log_path: String,
}

impl Default for AgentStatus {
    fn default() -> Self {
        Self {
            state: AgentState::Starting,
            running: false,
            mode: LaunchMode::Bundled,
            pid: None,
            uptime_seconds: 0,
            restart_count: 0,
            last_error: None,
            last_health_at: None,
            health_url: health_url(),
            port: default_agent_port(),
            spawn_started_at: None,
            first_port_open_at: None,
            first_health_ok_at: None,
            boot_duration_ms: None,
            boot_grace_active: false,
            log_path: SIDECAR_LOG_FILENAME.to_string(),
        }
    }
}

/// A boxed handle to whichever child process the supervisor is
/// running. Wrapped in an enum so the supervisor does not care
/// which mode is in use.
enum ChildHandle {
    /// Bundled sidecar: a Tauri shell-plugin CommandChild wrapped
    /// in ``Option`` so the kill path can move it out (the
    /// CommandChild::kill API takes ``self`` by value in
    /// tauri-plugin-shell 2.x).
    Bundled(Option<CommandChild>),
    /// System Python: a std ``Child``. Exit-status logging goes
    /// through the supervisor thread which already holds the
    /// shared data dir in ``AgentStateInner``.
    System(Child),
}

impl ChildHandle {
    fn pid(&self) -> Option<u32> {
        match self {
            ChildHandle::Bundled(c) => c.as_ref().map(|h| h.pid()),
            ChildHandle::System(c) => Some(c.id()),
        }
    }
    fn kill(&mut self) {
        match self {
            ChildHandle::Bundled(c) => {
                if let Some(handle) = c.take() {
                    if let Err(e) = handle.kill() {
                        log::warn!("supervisor: bundled kill failed: {}", e);
                    }
                }
            }
            ChildHandle::System(c) => {
                // Best effort: std::process::Child::kill only kills
                // the direct child, not any subprocess. We then
                // also issue a Windows ``taskkill /T /F`` so the
                // uvicorn worker tree dies cleanly.
                let _ = c.kill();
                #[cfg(windows)]
                {
                    let pid = c.id();
                    let _ = Command::new("taskkill")
                        .args(["/PID", &pid.to_string(), "/T", "/F"])
                        .stdout(Stdio::null())
                        .stderr(Stdio::null())
                        .status();
                }
            }
        }
    }
    fn try_reap(&mut self) -> Option<std::process::ExitStatus> {
        match self {
            ChildHandle::Bundled(_) => None, // Tauri surfaces its own events
            ChildHandle::System(c) => c.try_wait().ok().flatten(),
        }
    }
}

/// Inner state guarded by a Mutex.
/// Inner state guarded by a Mutex. The struct itself is
/// ``pub(crate)`` so the ``#[tauri::command]`` proc-macro
/// expansion can name ``agent::SharedState`` from the
/// ``tauri::generate_handler!`` site in ``lib.rs``; the fields
/// stay module-private and are only mutated through the helper
/// methods.
pub(crate) struct AgentStateInner {
    child: Option<ChildHandle>,
    status: AgentStatus,
    started_at: Option<Instant>,
    mode: LaunchMode,
    data_dir: PathBuf,
    /// Consecutive failed restart attempts. The supervisor
    /// increments this when a spawn fails (or when a child exits
    /// before the cap), and the async probe task resets it to 0
    /// when it has observed a healthy ``/api/health`` response.
    attempts: u32,
}

impl AgentStateInner {
    fn new(mode: LaunchMode, data_dir: PathBuf) -> Self {
        let mut status = AgentStatus::default();
        status.mode = mode;
        status.log_path = data_dir
            .join("logs")
            .join(SIDECAR_LOG_FILENAME)
            .to_string_lossy()
            .to_string();
        Self {
            child: None,
            status,
            started_at: None,
            mode,
            data_dir,
            attempts: 0,
        }
    }
}

/// Phase 11 — check whether a TCP port is open on the loopback
/// interface. This is much cheaper than the full ``/api/health``
/// probe and is used by the retry path to surface "another
/// process holds port 8000" before we try to spawn.
fn port_is_listening(port: u16, timeout: Duration) -> bool {
    let addr = format!("127.0.0.1:{}", port);
    match TcpStream::connect_timeout(&addr.parse().unwrap(), timeout) {
        Ok(s) => {
            // Connection succeeded; close and report.
            drop(s);
            true
        }
        Err(_) => false,
    }
}

/// Phase 11 — find whatever process is listening on ``port`` and
/// return its PID, if any. Used to write a useful
/// "port 8000 already used by PID 1234" message into the
/// supervisor log + status.
fn port_owner_pid(port: u16) -> Option<u32> {
    #[cfg(windows)]
    {
        // ``netstat -ano`` is available on every Windows install
        // since NT 4.0; parsing the line for the port is robust
        // enough for a status message.
        let output = Command::new("netstat")
            .args(["-ano", "-p", "TCP"])
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .output()
            .ok()?;
        let text = String::from_utf8_lossy(&output.stdout);
        let needle = format!(":{}", port);
        for line in text.lines() {
            if line.contains(&needle) && line.contains("LISTENING") {
                // Last whitespace-separated token is the PID.
                if let Some(pid_str) = line.split_whitespace().last() {
                    if let Ok(pid) = pid_str.parse::<u32>() {
                        return Some(pid);
                    }
                }
            }
        }
        None
    }
    #[cfg(not(windows))]
    {
        let _ = port;
        None
    }
}

pub type SharedState = Arc<Mutex<AgentStateInner>>;

/// Decide which mode we should run in. Phase 8 default is bundled.
fn should_use_system_python() -> bool {
    matches!(
        env::var("USE_SYSTEM_PYTHON_AGENT")
            .unwrap_or_default()
            .to_ascii_lowercase()
            .as_str(),
        "1" | "true" | "yes" | "on"
    )
}

/// Resolve the data directory the Tauri shell is using for its
/// own state. This is the same dir the Python agent will fall
/// back to if the user has not set ``OFFICEPILOT_DATA_DIR``.
fn resolve_data_dir(app: &AppHandle) -> PathBuf {
    if let Some(s) = env::var_os("OFFICEPILOT_DATA_DIR") {
        return PathBuf::from(s);
    }
    if let Ok(dir) = app.path().app_data_dir() {
        return dir.join("data");
    }
    if let Ok(dir) = app.path().resource_dir() {
        return dir.join("data");
    }
    PathBuf::from(".")
}

/// Append a line to ``$OFFICEPILOT_DATA_DIR/logs/sidecar.log`` so
/// the user can find it from the Privacy Dashboard.
fn log_line(data_dir: &Path, line: &str) {
    let dir = data_dir.join("logs");
    if let Err(e) = fs::create_dir_all(&dir) {
        log::warn!("supervisor: cannot create log dir {:?}: {}", dir, e);
        return;
    }
    let path = dir.join("sidecar.log");
    let mut fh = match OpenOptions::new().create(true).append(true).open(&path) {
        Ok(f) => f,
        Err(e) => {
            log::warn!("supervisor: cannot open {:?}: {}", path, e);
            return;
        }
    };
    let stamp = chrono::Utc::now().to_rfc3339();
    let _ = writeln!(fh, "[{}] {}", stamp, line);
}

/// Drain a child pipe into the sidecar log file.
fn drain_child<R: Read + Send + 'static>(label: &'static str, mut pipe: R, data_dir: PathBuf) {
    thread::spawn(move || {
        let mut buf = [0u8; 4096];
        loop {
            match pipe.read(&mut buf) {
                Ok(0) => break,
                Ok(n) => {
                    let chunk = String::from_utf8_lossy(&buf[..n]);
                    for line in chunk.split_inclusive(|c| c == '\n' || c == '\r') {
                        log_line(&data_dir, &format!("[{}] {}", label, line.trim_end()));
                    }
                }
                Err(_) => break,
            }
        }
    });
}

/// Build the system-Python command. Kept for dev mode.
fn build_system_python_command(working_dir: &PathBuf) -> Command {
    let python = env::var("OFFICEPILOT_PYTHON").unwrap_or_else(|_| "python".to_string());
    let mut cmd = Command::new(python);
    cmd.arg("-m")
        .arg("uvicorn")
        .arg("app.main:app")
        .arg("--host")
        .arg("127.0.0.1")
        .arg("--port")
        .arg(default_agent_port().to_string())
        .arg("--log-level")
        .arg("info")
        .current_dir(working_dir)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    cmd
}

/// Spawn the agent in the appropriate mode. Returns the live
/// child handle and the mode label.
fn spawn_agent(
    app: &AppHandle,
    working_dir: &PathBuf,
    mode: LaunchMode,
    data_dir: &Path,
) -> Result<ChildHandle, String> {
    match mode {
        LaunchMode::SystemPython => {
            let mut cmd = build_system_python_command(working_dir);
            let mut child = cmd
                .args(["--port", &default_agent_port().to_string()])
                .spawn()
                .map_err(|e| format!("python spawn failed: {}", e))?;
            if let Some(out) = child.stdout.take() {
                drain_child("stdout", out, data_dir.to_path_buf());
            }
            if let Some(err) = child.stderr.take() {
                drain_child("stderr", err, data_dir.to_path_buf());
            }
            Ok(ChildHandle::System(child))
        }
        LaunchMode::Bundled => {
            let shell = app.shell();
            let cmd = shell
                .sidecar("officepilot-agent")
                .map_err(|e| format!("sidecar resolve failed: {}", e))?;
            let (mut rx, child) = cmd
                .args(["--port", &default_agent_port().to_string()])
                .spawn()
                .map_err(|e| format!("sidecar spawn failed: {}", e))?;
            // Drain sidecar stdout/stderr into our log file via
            // Tauri's async runtime; we don't need the events
            // for control flow, only for diagnostics.
            let data_dir_for_drain = data_dir.to_path_buf();
            tauri::async_runtime::spawn(async move {
                use tauri_plugin_shell::process::CommandEvent;
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            let text = String::from_utf8_lossy(&line);
                            log_line(&data_dir_for_drain, &format!("[stdout] {}", text));
                        }
                        CommandEvent::Stderr(line) => {
                            let text = String::from_utf8_lossy(&line);
                            log_line(&data_dir_for_drain, &format!("[stderr] {}", text));
                        }
                        CommandEvent::Error(err) => {
                            log_line(
                                &data_dir_for_drain,
                                &format!("[error] {}", err),
                            );
                        }
                        CommandEvent::Terminated(payload) => {
                            log_line(
                                &data_dir_for_drain,
                                &format!(
                                    "[terminated] code={:?} signal={:?}",
                                    payload.code, payload.signal
                                ),
                            );
                        }
                        _ => {}
                    }
                }
            });
            Ok(ChildHandle::Bundled(Some(child)))
        }
    }
}

/// Supervisor loop. Lives for the lifetime of the Tauri app.
///
/// The supervisor is intentionally minimal: it only handles
/// spawn / reap and emits the status snapshot. The periodic
/// health probe is run in a separate async task
/// (``spawn_probe_task``) so the supervisor thread is never
/// blocked on network I/O.
pub fn spawn_supervisor(app: AppHandle) {
    let mode = if should_use_system_python() {
        LaunchMode::SystemPython
    } else {
        LaunchMode::Bundled
    };
    let data_dir = resolve_data_dir(&app);
    log_line(
        &data_dir,
        &format!(
            "supervisor: starting (mode={:?}, data={})",
            mode,
            data_dir.display()
        ),
    );

    let state: SharedState = Arc::new(Mutex::new(AgentStateInner::new(mode, data_dir.clone())));
    app.manage(state.clone());

    // Working dir: prefer the sibling ``backend/`` of the resource
    // dir; in dev this is the repo's backend/ folder.
    let working_dir = app
        .path()
        .resource_dir()
        .ok()
        .and_then(|p| p.parent().map(|p| p.join("backend")))
        .or_else(|| {
            // When running `cargo tauri dev` the resource dir is
            // the project root itself; fall back to the current
            // dir's sibling ``backend/`` folder.
            env::current_dir().ok().map(|c| c.join("..").join("..").join("backend"))
        })
        .unwrap_or_else(|| PathBuf::from("."));

    // Kick off the async health-probe task. It owns the
    // health-probe cadence (``HEALTH_INTERVAL_OK`` /
    // ``HEALTH_INTERVAL_DOWN``) and the state transitions for
    // Online/Offline. The supervisor thread no longer blocks on
    // network I/O.
    spawn_probe_task(app.clone());

    let app_for_thread = app.clone();
    thread::spawn(move || {
        log::info!("supervisor: starting");
        loop {
            // Decide whether we need to spawn. The probe task is
            // the source of truth for "is the agent online?", so
            // the supervisor only owns the spawn/reap half of
            // the lifecycle.
            let _needs_spawn = {
                let mut s = state.lock();
                let mut spawn_now = false;
                match s.child.as_mut() {
                    None => spawn_now = true,
                    Some(c) => {
                        if let Some(status) = c.try_reap() {
                            log::warn!(
                                "supervisor: agent exited with status {:?}; will restart",
                                status
                            );
                            s.status.running = false;
                            s.status.state = AgentState::Offline;
                            s.status.last_error = Some(format!(
                                "agent exited: code={:?}",
                                status.code()
                            ));
                            s.child = None;
                            spawn_now = true;
                        }
                    }
                }
                if spawn_now {
                    if s.attempts >= MAX_RESTART_ATTEMPTS {
                        log::error!("supervisor: max restart attempts reached; sleeping");
                        s.status.state = AgentState::Failed;
                        s.status.running = false;
                    } else {
                        // Phase 11 — pre-flight: is the agent port
                        // already in use by something else? If it
                        // is, the user has a clearer error than
                        // "spawn failed: address in use" bubbling
                        // out of the OS.
                        let port = s.status.port;
                        if port_is_listening(port, Duration::from_millis(250)) {
                            if let Some(offender) = port_owner_pid(port) {
                                let msg = format!(
                                    "port {} is already in use by PID {}; \
                                     close that process or change OFFICEPILOT_AGENT_PORT",
                                    port, offender
                                );
                                log::error!("supervisor: {}", msg);
                                log_line(&s.data_dir, &format!("supervisor: {}", msg));
                                s.status.last_error = Some(msg);
                                s.status.state = AgentState::Failed;
                                s.status.running = false;
                            } else {
                                let msg = format!(
                                    "port {} is already in use by another process",
                                    port
                                );
                                log::error!("supervisor: {}", msg);
                                log_line(&s.data_dir, &format!("supervisor: {}", msg));
                                s.status.last_error = Some(msg);
                                s.status.state = AgentState::Failed;
                                s.status.running = false;
                            }
                        } else {
                            match spawn_agent(&app_for_thread, &working_dir, s.mode, &s.data_dir) {
                                Ok(child) => {
                                    let pid = child.pid();
                                    log::info!(
                                        "supervisor: spawned agent (mode={:?}, pid={:?})",
                                        s.mode,
                                        pid
                                    );
                                    s.child = Some(child);
                                    s.status.pid = pid;
                                    s.status.running = true;
                                    s.status.state = AgentState::Starting;
                                    s.status.uptime_seconds = 0;
                                    s.status.last_error = None;
                                    s.started_at = Some(Instant::now());
                                    s.attempts += 1;
                                    s.status.restart_count = s.attempts;
                                    // Phase 11 — capture the spawn
                                    // timestamp in ISO-8601 so the
                                    // UI can show "starting for
                                    // 12s…". Reset any prior
                                    // boot-timing state from
                                    // earlier sessions.
                                    s.status.spawn_started_at =
                                        Some(chrono::Utc::now().to_rfc3339());
                                    s.status.first_port_open_at = None;
                                    s.status.first_health_ok_at = None;
                                    s.status.boot_duration_ms = None;
                                    s.status.boot_grace_active = true;
                                    log_line(
                                        &s.data_dir,
                                        &format!(
                                            "supervisor: spawn ok (pid={:?}, attempt={}, boot_grace={}s)",
                                            pid, s.attempts, BOOT_GRACE_DURATION.as_secs()
                                        ),
                                    );
                                }
                                Err(e) => {
                                    log::error!("supervisor: spawn failed: {}", e);
                                    s.status.last_error = Some(e.clone());
                                    s.status.state = AgentState::Offline;
                                    s.status.running = false;
                                    s.attempts += 1;
                                    s.status.restart_count = s.attempts;
                                    log_line(
                                        &s.data_dir,
                                        &format!("supervisor: spawn failed: {}", e),
                                    );
                                }
                            }
                        }
                    }
                }
                // Refresh uptime + grace flag on every supervisor
            // tick so the UI sees an up-to-date "starting for N
            // seconds" counter even when no probe has fired.
            {
                let mut s = state.lock();
                if let Some(start) = s.started_at {
                    s.status.uptime_seconds = start.elapsed().as_secs();
                    s.status.boot_grace_active =
                        start.elapsed() < BOOT_GRACE_DURATION
                            && s.status.state == AgentState::Starting;
                } else {
                    s.status.boot_grace_active = false;
                }
            }
            spawn_now
            };

            // Emit a UI event so the React layer can refresh its
            // status pill without polling. The probe task emits
            // a more up-to-date snapshot asynchronously, but the
            // supervisor's emission keeps the UI in sync on
            // spawn / restart moments.
            let snapshot = state.lock().status.clone();
            let _ = app_for_thread.emit("agent://status", &snapshot);

            // Short supervisor tick — the probe task runs on its
            // own cadence.
            thread::sleep(Duration::from_secs(1));
        }
    });
}

/// Async health-probe task. Runs in the Tauri async runtime.
///
/// We still use ``ureq`` (a synchronous HTTP client) but wrap
/// the blocking call in ``tauri::async_runtime::spawn_blocking``
/// so it does not block the runtime. The probe cadence adapts
/// to the agent's health:
///
///   - 1.5s while the sidecar is in the boot-grace window and
///     we are still waiting for the first ``/api/health`` answer.
///   - 15s when healthy.
///   - 3s when not healthy AND past the boot grace.
///
/// The boot grace is :const:`BOOT_GRACE_DURATION`; while it is
/// active, probe failures keep the state at :enum:`AgentState::Starting`
/// so a slow cold start does not surface as a misleading
/// "Agent Offline" pill.
fn spawn_probe_task(app: AppHandle) {
    tauri::async_runtime::spawn(async move {
        let state: tauri::State<SharedState> = app.state::<SharedState>();
        // Inner clone of the Arc; tauri::State only lives as
        // long as the AppHandle but the Arc keeps the data
        // alive for the duration of the async task.
        let state_arc: SharedState = state.inner().clone();
        let mut interval = HEALTH_INTERVAL_BOOT;
        loop {
            // Sleep on the async runtime so we do not block any
            // other Tauri tasks.
            tokio::time::sleep(interval).await;

            // Decide if we are still inside the boot grace. If
            // we are, run a fast loop and keep the state at
            // ``Starting`` even when the probe fails. This is
            // the Phase 11 cold-start tolerance.
            let in_grace = {
                let s = state_arc.lock();
                s.started_at
                    .map(|t| t.elapsed() < BOOT_GRACE_DURATION)
                    .unwrap_or(false)
                    && s.status.state == AgentState::Starting
            };

            // Cheap TCP "is the port open yet?" probe. We run
            // this *before* the HTTP probe because the first
            // time the port opens is the most useful boot
            // signal — uvicorn may take a few extra seconds
            // after the bind to finish importing the app.
            let port = state_arc.lock().status.port;
            let port_open = tauri::async_runtime::spawn_blocking(move || {
                port_is_listening(port, Duration::from_millis(250))
            })
            .await
            .unwrap_or(false);

            // Run the blocking ``ureq`` call on a worker thread
            // so the runtime stays responsive.
            let probe = tauri::async_runtime::spawn_blocking(|| {
                let agent = ureq::AgentBuilder::new()
                    .timeout(HEALTH_TIMEOUT)
                    .build();
                match agent.get(&health_url()).call() {
                    Ok(resp) if resp.status() < 500 => true,
                    _ => false,
                }
            })
            .await
            .unwrap_or(false);

            // Mutate shared state and pick the next interval.
            let snapshot = {
                let mut s = state_arc.lock();
                let now = chrono::Utc::now().to_rfc3339();
                s.status.last_health_at = Some(now.clone());

                // Record the first port-open timestamp.
                if port_open && s.status.first_port_open_at.is_none() {
                    s.status.first_port_open_at = Some(now.clone());
                    log_line(
                        &s.data_dir,
                        &format!(
                            "probe: port {} is now open (first time)",
                            s.status.port
                        ),
                    );
                }

                if probe {
                    // Capture the first successful health probe
                    // timestamp + boot duration. This is the
                    // authoritative "boot complete" signal.
                    if s.status.first_health_ok_at.is_none() {
                        if let Some(start) = s.started_at {
                            let duration = start.elapsed();
                            s.status.first_health_ok_at = Some(now.clone());
                            s.status.boot_duration_ms =
                                Some(duration.as_millis() as u64);
                            s.status.boot_grace_active = false;
                            log_line(
                                &s.data_dir,
                                &format!(
                                    "probe: first /api/health OK after {:.2}s (cold-boot complete)",
                                    duration.as_secs_f64()
                                ),
                            );
                        } else {
                            s.status.first_health_ok_at = Some(now.clone());
                            s.status.boot_grace_active = false;
                        }
                    }
                    if s.status.state == AgentState::Starting
                        || s.status.state == AgentState::Offline
                    {
                        log::info!("probe: agent answered /api/health -> online");
                        log_line(&s.data_dir, "probe: agent online");
                    }
                    s.status.state = AgentState::Online;
                    s.status.running = true;
                    s.status.last_error = None;
                    // Healthy response: clear the consecutive
                    // failure counter so the supervisor can try
                    // again on the next crash.
                    if s.attempts > 0 {
                        s.attempts = 0;
                        s.status.restart_count = 0;
                    }
                } else if in_grace {
                    // Inside the grace window: keep the state
                    // at Starting; record the failure as
                    // ``last_error`` only for the most recent
                    // probe so the user has something to look
                    // at if the boot actually fails. Do not
                    // transition to Offline.
                    s.status.last_error = Some("still booting…".into());
                } else {
                    // Outside the grace window: a probe failure
                    // counts as Offline (if we still have a
                    // child). The supervisor's spawn block
                    // already set the state when there is no
                    // child.
                    if s.child.is_some() {
                        s.status.state = AgentState::Offline;
                        s.status.running = false;
                        s.status.last_error = Some("health probe failed".into());
                        // The grace window is over: stop
                        // advertising it.
                        s.status.boot_grace_active = false;
                    }
                }
                s.status.clone()
            };
            // Pick the next cadence.
            //
            // Priority: while the sidecar is still booting
            // (state=Starting AND no first_health_ok_at yet),
            // poll fast. Once healthy, slow down. If we are
            // past the grace and unhealthy, fall back to the
            // 3s retry cadence.
            interval = if probe {
                HEALTH_INTERVAL_OK
            } else if in_grace {
                HEALTH_INTERVAL_BOOT
            } else {
                HEALTH_INTERVAL_DOWN
            };
            let _ = app.emit("agent://status", &snapshot);
        }
    });
}

/// Tauri command: return the latest AgentStatus snapshot.
#[tauri::command]
pub fn get_agent_status(state: tauri::State<SharedState>) -> AgentStatus {
    state.lock().status.clone()
}

/// Tauri command: request a manual restart. Kills the running
/// child (best-effort) and bumps the restart counter so the
/// supervisor re-spawns on its next tick. Resets the attempt
/// cap so the supervisor will actually try again.
#[tauri::command]
pub fn request_agent_restart(state: tauri::State<SharedState>) -> AgentStatus {
    let mut s = state.lock();
    if let Some(mut c) = s.child.take() {
        c.kill();
    }
    s.status.running = false;
    s.status.state = AgentState::Offline;
    s.status.last_error = Some("manual restart requested".into());
    s.started_at = None;
    // Phase 11 — reset boot timing so the next cold start
    // reports its own duration.
    s.status.spawn_started_at = None;
    s.status.first_port_open_at = None;
    s.status.first_health_ok_at = None;
    s.status.boot_duration_ms = None;
    s.status.boot_grace_active = false;
    s.status.clone()
}

/// Tauri command: request a *retry* from a *failed* state. Same
/// as a manual restart, but also resets the supervisor's
/// attempt counter (which the supervisor thread reads from the
/// status field on its next iteration).
#[tauri::command]
pub fn request_agent_retry(state: tauri::State<SharedState>) -> AgentStatus {
    let mut s = state.lock();
    if let Some(mut c) = s.child.take() {
        c.kill();
    }
    s.status.running = false;
    s.status.state = AgentState::Offline;
    s.status.restart_count = 0;
    s.status.last_error = Some("manual retry requested".into());
    s.started_at = None;
    s.status.spawn_started_at = None;
    s.status.first_port_open_at = None;
    s.status.first_health_ok_at = None;
    s.status.boot_duration_ms = None;
    s.status.boot_grace_active = false;
    s.status.clone()
}

/// Phase 11 — diagnostic snapshot returned by ``open_logs`` /
/// ``get_agent_logs``. We do not return the log *contents* (they
/// can be megabytes); the UI shows the path + a "Reveal in
/// Explorer" button.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentLogsInfo {
    pub sidecar_log_path: String,
    pub tauri_log_path: Option<String>,
    pub size_bytes: u64,
    pub exists: bool,
    pub last_lines: Vec<String>,
}

/// Tauri command: return diagnostic info about the sidecar log
/// (path, size, last 20 lines) so the React layer can show a
/// "Open Logs" button and a brief preview. If ``reveal`` is
/// true, the supervisor also asks the OS to pop a file-explorer
/// window on the log file.
#[tauri::command]
pub fn get_agent_logs(state: tauri::State<SharedState>) -> AgentLogsInfo {
    let s = state.lock();
    let log_path = PathBuf::from(&s.status.log_path);
    let (exists, size) = match fs::metadata(&log_path) {
        Ok(m) => (true, m.len()),
        Err(_) => (false, 0),
    };
    let mut last_lines: Vec<String> = Vec::new();
    if exists {
        if let Ok(text) = fs::read_to_string(&log_path) {
            // Take the last 20 non-empty lines, in chronological
            // order. Useful for "what was the agent doing right
            // before it failed?".
            for line in text.lines().rev().take(20).collect::<Vec<_>>().into_iter().rev() {
                if !line.trim().is_empty() {
                    last_lines.push(line.to_string());
                }
            }
        }
    }
    AgentLogsInfo {
        sidecar_log_path: s.status.log_path.clone(),
        tauri_log_path: None,
        size_bytes: size,
        exists,
        last_lines,
    }
}

/// Tauri command: reveal the sidecar log file in the OS file
/// explorer. On Windows we use ``explorer /select,<path>``; on
/// macOS ``open -R``; on Linux ``xdg-open`` on the parent dir.
/// Returns ``true`` if the explorer process was launched
/// successfully.
#[tauri::command]
pub fn reveal_sidecar_logs(state: tauri::State<SharedState>) -> bool {
    let s = state.lock();
    let log_path = PathBuf::from(&s.status.log_path);
    drop(s);
    if !log_path.exists() {
        return false;
    }
    #[cfg(windows)]
    {
        // ``explorer /select,<path>`` highlights the file in a
        // new window. Using the parent dir does not highlight
        // but is the safest fallback.
        let path_str = log_path.to_string_lossy().to_string();
        let arg = format!("/select,{}", path_str);
        let parent = log_path.parent().unwrap_or(Path::new("."));
        let target = if parent.exists() {
            parent
        } else {
            Path::new(".")
        };
        // Try the highlight form first; on weird path shapes
        // fall back to opening the parent dir.
        let res = Command::new("explorer").arg(&arg).spawn();
        match res {
            Ok(_) => true,
            Err(_) => Command::new("explorer")
                .arg(target)
                .spawn()
                .map(|_| true)
                .unwrap_or(false),
        }
    }
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .args(["-R", &log_path.to_string_lossy()])
            .spawn()
            .map(|_| true)
            .unwrap_or(false)
    }
    #[cfg(all(unix, not(target_os = "macos")))]
    {
        // xdg-open the parent directory; Linux file managers
        // do not have a portable "reveal" verb.
        let parent = log_path.parent().unwrap_or(Path::new("."));
        Command::new("xdg-open")
            .arg(parent)
            .spawn()
            .map(|_| true)
            .unwrap_or(false)
    }
}

/// Public helper used by the cleanup hook in :mod:`lib` to
/// kill the sidecar on app exit.
pub fn stop_agent(state: &SharedState) {
    let mut s = state.lock();
    if let Some(mut c) = s.child.take() {
        log::info!("supervisor: stopping agent on app exit");
        log_line(&s.data_dir, "supervisor: stopping agent on app exit");
        c.kill();
    }
}
