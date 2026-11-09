# Changelog

All notable changes to TBASSync are documented here. This project follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) loosely and uses
integer version numbers that match `Services/versionManager.py`.

## [Unreleased]

### Added
- "Keep running in the background and start with Windows" checkbox (ticked by default; `trayMode` in `TBASSync-config.json`). Unticked, TBAS Sync has no tray icon, quits when its window is closed, and removes its Windows startup entry. Ticking it again restores the tray icon and autostart immediately.
- After an update, TBAS Sync shows what changed since the version you had, once. A fresh install doesn't.
- Skins aren't installed automatically while IL-2 is running; they wait until the game closes (checked every minute). "Update Now" still installs them right away.
- Closing the window in tray mode shows a notification that TBAS Sync is still running in the background, with how to open or quit it.
- The tray icon tooltip shows the current status and when it changed, e.g. "Everything is up to date (10:42)".
- Free disk space is checked before a sync. If the IL-2 drive is too full, TBAS Sync says how much is needed instead of failing part-way (one notification, not one every 10 minutes).
- "Remove old TBAS skins" button: offers to delete skins that TBAS Sync installed and that their collection no longer has, after listing them and asking. TBAS Sync now records the skins it installed (`TBASSync-installed.json`), so it never offers the user's own skins, and never when a collection failed to load or arrived incomplete (checked against its `skins_count`). Skins dropped before this version are not detected.
- `tests/`: the GUI and service tests, run with `venv\Scripts\python.exe tests\run_all.py`.

### Changed
- Cockpit notes/photos work again, from HSD's cockpit notes packs. The IRRE server dropped its catalogs in October 2026 (every scan logged a 404 and installed nothing). The "Cockpit notes/photos" list now offers every pack online on HSD (reloaded with every 10-minute check), so new packs such as "FTC Cockpit Notes" appear without an app update. `cockpitNotesMode` saves the pack id; the four names saved by older versions map to HSD packs 4, 2, 3 and 1, the same files Fizz moved there, so photos already installed aren't downloaded again.
- A saved pack that isn't online, or a list that couldn't be loaded, shows the choice as "Unavailable: ...".
- The log file stops at 1 MB and keeps one previous file (`TBASSync.log.1`). A missing cockpit catalog is logged as one line instead of a full error on every scan; before, a tray copy wrote about 2,000 log lines a day.
- The window title is built from `currentVersion`, so a release only bumps `Services/versionManager.py`.
- Starting TBAS Sync yourself now always opens its window. Only the launch at Windows sign-in stays hidden in the tray (the startup entry now passes `-autostart`).
- Starting TBAS Sync while it already runs opens the running copy's window, instead of showing an "already running" message.

## [16] - 2026-10-31

### Added
- Anonymous usage statistics: on launch and once a day, the app sends a random device ID, its version and its install date to the TBAS VPS (`server/usage_server.py`). No IP addresses are stored. Opt out with `"usageTracking": false` in `%APPDATA%\TBASSync\TBASSync-device.json`.

## [15] - 2026-10-30

### Changed
- TBAS Sync now runs as a system tray app. It checks for new or updated skins on launch and every 10 minutes, installs them silently, and shows a Windows notification when done (including when skins fail). The window starts hidden unless setup is needed; closing it hides it to the tray. Tray menu: Open, Check for skin updates now, Quit.
- Only one instance can run at a time; launching it again says it's already running in the tray.
- Starts automatically with Windows (per-user `Run` registry entry, refreshed on every launch so it follows the exe). Disable it in Task Manager > Startup apps.
- Built with Python 3.14-compatible Pillow and PyInstaller.

## [14] - 2026-10-22

### Fixed
- Scans no longer fail with "Scan failed" when cockpit notes/photos are enabled: the IRRE cockpit photo catalogs are offline (HTTP 404), and that error used to abort the whole scan, blocking all skin updates. Cockpit photos are now skipped (and logged) while skins scan and update normally.

## [13] - 2026-10-12

### Added
- Skin preview strip: after a scan, previews of every skin to be downloaded
  or updated scroll right → left (tagged NEW / UPDATE); during an update each
  skin's preview slides in as its download starts, with a progress bar and a
  ✓ / ✗ when it finishes. Hidden when nothing needs updating. Default window
  height is now 560 px to make room for it.

### Fixed
- Scan, sync, update check, collection loading and the IL-2 folder search no
  longer touch Tk widgets from background threads (could freeze or crash the
  window with "main thread is not in main loop"); UI work is handed to the Tk
  thread through `GUI/Components/uiDispatcher.py`.
- Scan no longer crashes when the IL-2 `data\graphics\skins` folder doesn't
  exist yet (fresh install); every subscribed skin is listed as missing.
- A skin's secondary `#1.dds` file is no longer attached to a same-named skin
  of a different aircraft (which left the real owner permanently "to be
  updated").
- All HTTP requests now time out (10 s connect, 60 s between bytes) instead of
  hanging the scan, update or update check forever on a stalled connection.

## [12] - 2026-09-19

### Added
- After syncing cockpit photos, explain that they only appear in the cockpit
  during flight (the Plane Settings preview always shows the default photo).

### Changed
- App icon switched to `TBAS.ico`.
- Exceptions are logged with their full traceback.
- README: main-window screenshot.

### Removed
- Dead code left over from the pre-headless updater.

## [11] - 2026-05-15

### Added
- Opt-in checkbox to also sync the "Friends of TBAS" collection.

## [10] - 2026-04-20

First release under the TBASSync name.

### Added
- Headless self-update; the release ships `TBASSync.exe` alongside the zip.
- `.github/` issue templates, PR template, and PyInstaller build workflow.
- `CHANGELOG.md`.

### Changed
- Rebranded from **HSDSync** to **TBASSync**: renamed entry points,
  resources, spec file, workspace, and version-info metadata.
- Config, subscriptions, hashes, and log moved to `%APPDATA%\TBASSync\` with
  automatic one-time migration from the legacy location next to the exe.
- Self-update now points at `riaanjutte/TBASSync` releases
  (`Services/versionManager.py`).
- Various GUI / theming / scanner cleanups carried forward from the rebrand
  branch.

### Removed
- Collection-search and collection-URL modals (and their panel) — out of
  scope for the rebranded single-site use case.
- Legacy `Ressources/` directory (typo) — replaced by `Resources/`.

## Upstream history

Earlier versions (v1–v9) were released under the upstream name
`IL2GB-HSDSync`. See that project for prior changelog entries:
https://github.com/RaphED/IL2GB-HSDSync/releases
