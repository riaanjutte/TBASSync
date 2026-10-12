# Changelog

All notable changes to TBASSync are documented here. This project follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) loosely and uses
integer version numbers that match `Services/versionManager.py`.

## [Unreleased]

### Added
- Skin preview strip: after a scan, previews of every skin to be downloaded
  or updated scroll right → left (tagged NEW / UPDATE); during an update each
  skin's preview slides in as its download starts, with a progress bar and a
  ✓ / ✗ when it finishes. Hidden when nothing needs updating. Default window
  height is now 560 px to make room for it.
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

### Fixed
- Scan, sync, update check, collection loading and the IL-2 folder search no
  longer touch Tk widgets from background threads (could freeze or crash the
  window with "main thread is not in main loop"); UI work is handed to the Tk
  thread through `GUI/Components/uiDispatcher.py`.

### Removed
- Collection-search and collection-URL modals (and their panel) — out of
  scope for the rebranded single-site use case.
- Legacy `Ressources/` directory (typo) — replaced by `Resources/`.

## Upstream history

Earlier versions (v1–v9) were released under the upstream name
`IL2GB-HSDSync`. See that project for prior changelog entries:
https://github.com/RaphED/IL2GB-HSDSync/releases
