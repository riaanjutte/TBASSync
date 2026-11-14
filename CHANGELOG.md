# Changelog

All notable changes to TBASSync are documented here. This project follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) loosely and uses
integer version numbers that match `Services/versionManager.py`.

## [Unreleased]

### Added
- The notification after new skins are installed now names them, for example "New skin: TBAS Bf110-E2 by MayheM-1."
- A hangar in the main window: every skin of the TBAS collection as a picture card, grouped by aircraft, with the name of whoever made it. Skins that arrived on your PC in the last 14 days are listed first under "Latest arrivals" and marked NEW. Click a card to open the skin on HSD.
- Under the "Cockpit notes/photos" list, a line now describes the selected pack: what it contains, who made it and how many aircraft it covers. Click "Preview" to see the pack's notes for each aircraft before you choose it, with a link to the pack on HSD.
- A Windows installer, TBASSync-Setup.exe. It installs TBAS Sync for your Windows account only (no admin password needed), adds a Start Menu shortcut (and a desktop shortcut if you want one), and can be removed from Windows Settings > Apps. Your settings are kept when you switch from the zip, and the zip is still available if you prefer it.

### Changed
- The window opens a little larger, to make room for the hangar.

### Fixed
- With "Restricted symbols" set to "Hide", every skin update failed with "Unexpected error during update" as long as the collection held a skin that only exists with restricted symbols. Such skins are now skipped when symbols are hidden.

### Removed
- The "Also sync Friends of TBAS collection" setting. Friends of TBAS skins you already have stay installed, but are no longer updated.

## [17] - 2026-11-09

### Added
- A "Keep running in the background and start with Windows" setting, on by default. Turn it off and TBAS Sync works like a normal window: closing it quits the app, and it no longer starts with Windows.
- New skins aren't installed while you're flying. If IL-2 is running, TBAS Sync waits until you quit the game. "Update Now" still installs them straight away.
- A "Remove old TBAS skins" button appears when skins are taken out of the TBAS collection. It lists them and asks before deleting anything, and it never touches your own skins. Only skins removed from now on are found.
- TBAS Sync checks there is enough free disk space before downloading, and tells you how much room it needs.
- Hover over the tray icon to see what TBAS Sync is doing, for example "Everything is up to date (10:42)".
- Closing the window shows a notification that TBAS Sync is still running in the background.
- After an update, this list of what's new is shown once.

### Changed
- Cockpit notes and photos work again. They now come from the cockpit notes packs on HSD, and the list shows every pack there, including new ones such as "FTC Cockpit Notes". Your choice is kept, and photos you already have aren't downloaded again. A pack that's offline shows as "Unavailable".
- Starting TBAS Sync yourself now always opens its window, even when it's already running in the tray. It only stays hidden in the tray when Windows starts it at sign-in.
- The log file no longer grows without limit.

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
