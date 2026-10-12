# Changelog

All notable changes to TBASSync are documented here. This project follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) loosely and uses
integer version numbers that match `Services/versionManager.py`.

## [Unreleased]

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
