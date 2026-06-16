# Icons

The icon files in this directory are **placeholder** auto-generated
PNGs and an ICO produced by the OfficePilot build scripts. They
exist so `cargo tauri build` does not fail with "icon not found".

For a production build, replace them with real OfficePilot AI
branding. Two options:

1. Drop a single 1024x1024 PNG at `app-icon.png` (repo root or
   anywhere convenient) and run:

       cargo tauri icon path/to/app-icon.png

   This regenerates every required size (`32x32.png`,
   `128x128.png`, `128x128@2x.png`, `icon.ico`, and more) inside
   `src-tauri/icons/`.

2. Or hand-edit each file. Tauri requires at minimum:

       src-tauri/icons/32x32.png
       src-tauri/icons/128x128.png
       src-tauri/icons/128x128@2x.png
       src-tauri/icons/icon.ico

   for a Windows MSI/NSIS bundle.
