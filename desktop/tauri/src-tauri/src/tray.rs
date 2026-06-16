use tauri::menu::{Menu, MenuItem, PredefinedMenuItem, MenuEvent};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Emitter, Manager};

pub fn build_tray(app: &AppHandle) -> tauri::Result<()> {
    let new_task = MenuItem::with_id(app, "new_task", "New Task", true, None::<&str>)?;
    let plan_mode = MenuItem::with_id(app, "plan_mode", "Plan Mode", true, None::<&str>)?;
    let record_wf = MenuItem::with_id(app, "record_workflow", "Record Workflow", true, None::<&str>)?;
    let wf_memory = MenuItem::with_id(app, "workflow_memory", "Workflow Memory", true, None::<&str>)?;
    let skills = MenuItem::with_id(app, "accounting_skills", "⚡ Skills", true, None::<&str>)?;
    let sep1 = PredefinedMenuItem::separator(app)?;
    let emergency = MenuItem::with_id(app, "emergency_stop", "Emergency Stop", true, None::<&str>)?;
    let sep2 = PredefinedMenuItem::separator(app)?;
    let settings = MenuItem::with_id(app, "settings", "Settings", true, None::<&str>)?;
    let sep3 = PredefinedMenuItem::separator(app)?;
    let exit = MenuItem::with_id(app, "exit", "Quit", true, None::<&str>)?;

    let menu = Menu::with_items(
        app,
        &[
            &new_task,
            &plan_mode,
            &record_wf,
            &wf_memory,
            &skills,
            &sep1,
            &emergency,
            &sep2,
            &settings,
            &sep3,
            &exit,
        ],
    )?;

    let _tray = TrayIconBuilder::with_id("main")
        .tooltip("Accountant AutoPilot")
        .icon(app.default_window_icon().cloned().unwrap_or_else(|| {
            tauri::image::Image::new_owned(vec![0, 0, 0, 0], 1, 1)
        }))
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(handle_menu_event)
        .on_tray_icon_event(handle_tray_event)
        .build(app)?;

    Ok(())
}

fn show_main_window(app: &AppHandle) {
    if let Some(w) = app.get_webview_window("main") {
        let _ = w.show();
        let _ = w.unminimize();
        let _ = w.set_focus();
    }
}

fn handle_menu_event(app: &AppHandle, event: MenuEvent) {
    match event.id().as_ref() {
        "new_task" => {
            show_main_window(app);
            let _ = app.emit("tray://new-task", ());
        }
        "plan_mode" => {
            show_main_window(app);
            let _ = app.emit("tray://plan-mode", ());
        }
        "record_workflow" => {
            show_main_window(app);
            let _ = app.emit("tray://record-workflow", ());
        }
        "workflow_memory" => {
            show_main_window(app);
            let _ = app.emit("tray://workflow-memory", ());
        }
        "accounting_skills" => {
            show_main_window(app);
            let _ = app.emit("tray://skills", ());
        }
        "emergency_stop" => {
            show_main_window(app);
            let _ = app.emit("tray://emergency-stop", ());
        }
        "settings" => {
            show_main_window(app);
            let _ = app.emit("tray://settings", ());
        }
        "exit" => {
            log::info!("tray: exit requested");
            app.exit(0);
        }
        _ => {}
    }
}

fn handle_tray_event(tray: &tauri::tray::TrayIcon, event: TrayIconEvent) {
    if let TrayIconEvent::Click { button, button_state, .. } = event {
        if button == MouseButton::Left && button_state == MouseButtonState::Up {
            let app = tray.app_handle();
            show_main_window(app);
            let _ = app.emit("tray://open-agent", ());
        }
    }
}
