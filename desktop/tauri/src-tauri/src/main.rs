// Windows release builds hide the console window; on debug builds we
// keep it so log output is visible.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    officepilot_desktop_lib::run();
}
