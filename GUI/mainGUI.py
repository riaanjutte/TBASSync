import os
import shutil
import sys
import threading
import time
from tkinter import ttk, messagebox
import tkinter as tk
import webbrowser
import requests
from PIL import Image, ImageTk

import Services.loggingService as loggingService
import Services.synchronizerService as SynchronizerService
import Services.scannerService as ScannerService
from Services import autostartService, changelogService, instanceService, localService, remoteService, updateService, usageService
from Services.messageBrocker import MessageBrocker
from Services.loggingService import getLogFilePath
from Services.versionManager import getVersionLabel
from Services.configurationService import (
    configurationFileExists,
    generateConfFile,
    checkIL2InstallPath,
    getConf,
)
from Services.filesService import getRessourcePath, getIconPath, cleanTemporaryFolder

from Services.subscriptionsService import getAllSubcriptions, invalidateSubscriptionsCache
from GUI.parametersPanel import ParametersPanel
from GUI.statusPanel import StatusPanel
from GUI.actionsPanel import ActionPanel

from GUI.previewStrip import PreviewStrip, KIND_NEW, KIND_UPDATE
from GUI.progressBar import ProgressBar
from GUI.Components.clickableIcon import CliquableIcon
from GUI.Components.uiDispatcher import UiDispatcher
from GUI.Components.trayIcon import TrayIcon
from GUI.customTheme import apply_theme, TBASDarkTheme
from GUI.changelogDialog import showChangelog

CHECK_INTERVAL_MS = 10 * 60 * 1000
GAME_POLL_SECONDS = 60
DISK_SPACE_MARGIN = 100 * 1024 * 1024   # leave Windows and the game some room
USAGE_HEARTBEAT_MS = 24 * 60 * 60 * 1000


class MainGUI:

    def __init__(self, root, first_launch=False, startup_exception: Exception = None,
                 check_for_update=False, force_update=False, update_prerelease=False,
                 started_at_login=False):
        self.root = root
        self._first_launch = first_launch
        self._startup_exception = startup_exception
        self._check_for_update = check_for_update
        self._force_update = force_update
        self._update_prerelease = update_prerelease
        self._software_updating = False
        # Worker threads hand UI work to the Tk thread through this; they must
        # never touch widgets (or call root.after) directly.
        self.ui = UiDispatcher(self.root)
        self.tray = None
        self._tray_status = "TBAS Sync"
        self._waiting_for_game = False
        self._retired_skins = []   # kept apart from currentScanResult, which a finished sync clears
        self._changelog = []   # what changed since the version last shown, until it is shown
        self.root.iconbitmap(getRessourcePath("TBAS.ico"))

        apply_theme(self.root)

        self.root.title(f"TBAS Sync {getVersionLabel()}")
        self.root.geometry("900x560")
        self.root.minsize(750, 520)

        # ── HEADER ──────────────────────────────────────────────────────────
        self._build_header()

        # ── TOP: Parameters ─────────────────────────────────────────────────
        top_main_frame = tk.Frame(self.root)
        top_main_frame.pack(side="top", fill="both")

        self.parametersPanel = ParametersPanel(
            top_main_frame,
            on_parameters_change=self.on_parameters_change,
            ask_broad_search=self._ask_broad_search_via_status,
            ui=self.ui,
            on_background_change=self.set_tray_mode,
        )

        # ── PROGRESS BAR ─────────────────────────────────────────────────────
        progress_bar_frame = tk.Frame(self.root, bg=TBASDarkTheme.BG_DARKER, height=16)
        progress_bar_frame.pack(fill="x")
        progress_bar_frame.pack_propagate(False)

        self.progressBar = ProgressBar(progress_bar_frame)
        self.progressBar.pack(fill="x", padx=0, pady=4)

        # ── FOOTER: Action buttons (packed first with side=bottom so its
        # space is reserved — it must always stay visible, even when the
        # window is shrunk). ────────────────────────────────────────────────
        footer_frame = tk.Frame(self.root)
        footer_frame.pack(side="bottom", fill="x")
        self.actionPanel = ActionPanel(
            footer_frame,
            scanCommand=self.start_scan_async,
            syncCommand=self.start_synchronization_async,
            cleanupCommand=self.remove_retired_skins,
        )

        # ── BOTTOM: Status panel (fills remaining space above the footer) ──
        bottom_main_frame = tk.Frame(self.root)
        bottom_main_frame.pack(side="bottom", fill="both", expand=True)

        self.statusPanel = StatusPanel(bottom_main_frame, on_status=self._set_tray_status)

        # ── PREVIEW STRIP: between status and footer, only packed while at
        # least one skin is to be downloaded/updated ─────────────────────────
        self._status_container = bottom_main_frame
        self.previewStrip = PreviewStrip(self.root)
        self._preview_strip_visible = False
        self._sync_new_skin_ids = set()
        MessageBrocker.registerSkinSyncHook(self._on_skin_sync_event)

        # State
        self.currentScanResult: SynchronizerService.ScanResult = None
        self.pendingProcessing = False

        # ── TRAY: in tray mode (the default) the app lives in the system tray; closing the
        # window only hides it. When Windows starts it at sign-in the window starts hidden,
        # unless the user has to act on something; a launch by the user always shows it.
        # Unticking "Keep running in the background" (config "trayMode") makes it a plain window
        # app instead: no tray icon, closing it quits, no autostart.
        self._quit_after_sync = False
        self._last_failure = None   # last failure notified, so a skin failing every check isn't re-notified

        if self._startup_exception is not None:
            # After a startup error the app does nothing in the tray, so closing the window quits it.
            self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
            self.root.after(0, lambda: self._show_startup_exception(self._startup_exception))
            return
        tray_mode = getConf("trayMode")
        self.set_tray_mode(tray_mode)
        if tray_mode and started_at_login and not (first_launch or not checkIL2InstallPath()):
            self.root.withdraw()
        instanceService.listenForShowRequests(lambda: self.ui.call(self.show_window))
        # after an update, show what changed once; a window starting hidden shows it when first opened
        self._changelog = changelogService.pendingChangelog(first_launch)
        if self.root.state() != "withdrawn":
            self.root.after(500, self._show_changelog)
        threading.Thread(target=self._load_cockpit_packs, daemon=True).start()

        if self._check_for_update:
            self.root.after(0, self.start_update_check_async)
        else:
            self.root.after(0, self.load_collections_async)
        self.root.after(CHECK_INTERVAL_MS, self._periodic_check)
        usageService.ping("launch")
        self.root.after(USAGE_HEARTBEAT_MS, self._usage_heartbeat)

    def _usage_heartbeat(self):
        # the tray app can run for weeks without a relaunch; this keeps "last used" current
        self.root.after(USAGE_HEARTBEAT_MS, self._usage_heartbeat)
        usageService.ping("heartbeat")

    # ── TRAY ─────────────────────────────────────────────────────────────────

    def set_tray_mode(self, enabled):
        if enabled and self.tray is None:
            self.tray = TrayIcon(self.ui, on_open=self.show_window, on_check=self.check_now, on_quit=self.quit_app)
            self.tray.set_status(self._tray_status)
        elif not enabled and self.tray is not None:
            self.tray.stop()
            self.tray = None
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray if enabled else self.quit_app)
        autostartService.setAutostart(enabled)

    def hide_to_tray(self):
        """The window's X in tray mode: hide the window, and say the app keeps running."""
        self.root.withdraw()
        self._notify("TBAS Sync is still running in the background and keeps your skins up to date. "
                     "Click its tray icon to open it, or right-click the icon and choose Quit to close it.")

    def _load_cockpit_packs(self):
        # worker thread: list HSD's cockpit notes packs for the dropdown
        try:
            packs = remoteService.getCockpitNotesPacks()
        except Exception as e:
            loggingService.warning(f"Cannot list the cockpit notes packs: {e}")
            packs = []
        self.ui.call(self.parametersPanel.set_cockpit_packs, packs)

    def _set_tray_status(self, title):
        # hovering the tray icon shows the latest status and when it changed
        self._tray_status = f"TBAS Sync: {title} ({time.strftime('%H:%M')})"
        if self.tray is not None:
            self.tray.set_status(self._tray_status)

    def _notify(self, message):
        # without the tray icon the window is the only UI, and its status panel already says this
        if self.tray is not None:
            self.tray.notify("TBAS Sync", message)

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self._show_changelog()

    def _show_changelog(self):
        if not self._changelog:
            return
        showChangelog(self.root, self._changelog)
        self._changelog = []
        changelogService.markChangelogSeen()

    def quit_app(self):
        # A sync in progress keeps the process alive until its files are moved: keep the tray
        # icon until then (the sync-finished handlers quit), or the app runs with no icon.
        if self.actionPanel._state == ActionPanel.STATE_SYNCING:
            self._quit_after_sync = True
            # with no tray icon, keep a taskbar entry so the app doesn't look gone while it finishes
            self.root.withdraw() if self.tray is not None else self.root.iconify()
            return
        if self.tray is not None:
            self.tray.stop()
        self.root.destroy()

    def _periodic_check(self):
        self.root.after(CHECK_INTERVAL_MS, self._periodic_check)
        # the tray app runs for weeks: pick up new packs, and recover from a slow HSD at start
        threading.Thread(target=self._load_cockpit_packs, daemon=True).start()
        self.check_now()

    def check_now(self):
        """Re-download the collections (to see skins added or updated on HSD) and scan, unless busy."""
        if self.actionPanel._state not in (ActionPanel.STATE_UP_TO_DATE, ActionPanel.STATE_UPDATES):
            return
        invalidateSubscriptionsCache()
        self.start_scan_async()

    def _show_startup_exception(self, exception: Exception):
        self.lock_components_actions()
        self.actionPanel.set_state(ActionPanel.STATE_LOADING)
        self.actionPanel.primaryButton.configure(text="\u2717  Crashed")
        if isinstance(exception, requests.exceptions.ConnectionError):
            self.statusPanel.showError(
                "No internet connection",
                "TBAS Sync could not reach the server.",
            )
        else:
            self.statusPanel.showError(
                "TBAS Sync has crashed",
                f"Please consult the log file:\n{getLogFilePath()}",
            )

    def _build_header(self):
        header = tk.Frame(self.root, bg=TBASDarkTheme.BG_DARKER, height=85)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)

        # Logo
        logo_path = getRessourcePath("TBAS.png")
        img = Image.open(logo_path).convert("RGBA")
        logo_h = 65
        logo_w = int(img.width * logo_h / img.height)
        img = img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
        self._logo_base_img = img
        self._logo_photo = ImageTk.PhotoImage(img)

        self._logo_label = tk.Label(
            header,
            image=self._logo_photo,
            bg=TBASDarkTheme.BG_DARKER
        )
        self._logo_label.pack(side="left", padx=(10, 6), pady=8)

        self.root.after(0, self._start_logo_spin)

        tk.Label(
            header,
            text="TBAS Sync",
            font=("Bahnschrift Light Condensed", 29, "bold"),
            fg=TBASDarkTheme.FG_PRIMARY,
            bg=TBASDarkTheme.BG_DARKER
        ).pack(side="left", padx=(0, 0))

        # Right-side icons
        self.helpIcon = CliquableIcon(
            header,
            icon_path=getIconPath("help-32.png"),
            tooltip_text="Online HSD documentation",
            onClick=open_link_HSDDocumentation,
            bg=TBASDarkTheme.BG_DARKER
        )
        self.helpIcon.pack(side="right", padx=(4, 12), pady=18)

        self.discordIcon = CliquableIcon(
            header,
            icon_path=getIconPath("discord.png"),
            tooltip_text="Join the TBAS Discord",
            onClick=open_link_TBASDiscord,
            opacityFactor=60,
            onMouseOverOpacityFactor=220,
            bg=TBASDarkTheme.BG_DARKER
        )
        self.discordIcon.pack(side="right", padx=4, pady=18)

        # Orange accent rule beneath the header
        tk.Frame(self.root, height=2, bg=TBASDarkTheme.ACCENT_PRIMARY).pack(
            side="top", fill="x"
        )

    def _start_logo_spin(self, duration_ms=1000, rotations=1, interval_ms=40):
        total_frames = max(1, duration_ms // interval_ms)
        self._logo_spin_frames = []
        for i in range(1, total_frames + 1):
            angle = -(i / total_frames) * 360 * rotations
            rotated = self._logo_base_img.rotate(angle, resample=Image.Resampling.BILINEAR)
            self._logo_spin_frames.append(ImageTk.PhotoImage(rotated))
        self._logo_spin_index = 0
        self._advance_logo_spin(interval_ms)

    def _advance_logo_spin(self, interval_ms):
        if self._logo_spin_index < len(self._logo_spin_frames):
            self._logo_label.configure(image=self._logo_spin_frames[self._logo_spin_index])
            self._logo_spin_index += 1
            self.root.after(interval_ms, self._advance_logo_spin, interval_ms)
        else:
            self._logo_label.configure(image=self._logo_photo)
            self._logo_spin_frames = None

    # ── APP AUTO-UPDATE ──────────────────────────────────────────────────────

    def start_update_check_async(self):
        self.lock_components_actions()
        self.actionPanel.set_state(ActionPanel.STATE_LOADING)
        self.statusPanel.showLoading()
        threading.Thread(target=self._update_check_worker, daemon=True).start()

    def _update_check_worker(self):
        try:
            release_info = updateService.checkForUpdate(
                prerelease=self._update_prerelease,
                force=self._force_update,
            )
        except Exception as e:
            loggingService.error(e)
            release_info = None
        self.ui.call(self._on_update_check_done, release_info)

    def _on_update_check_done(self, release_info):
        # No update (or check failed — offline users still get the app): continue
        # with the normal startup path.
        if release_info is None:
            self.load_collections_async()
            return
        self._start_software_update_download(release_info)

    def _start_software_update_download(self, release_info):
        self._software_updating = True
        version = release_info.get("tag_name")
        self.lock_components_actions()
        self.actionPanel.set_state(ActionPanel.STATE_SOFTWARE_UPDATING)
        self.statusPanel.showSoftwareUpdating(version)
        MessageBrocker.emitProgress(0.0)
        threading.Thread(
            target=self._update_download_worker,
            args=(release_info,),
            daemon=True,
        ).start()

    def _update_download_worker(self, release_info):
        try:
            new_exe_path = updateService.downloadReleaseAsset(
                release_info,
                updateService.exe_file_name,
                progress_callback=MessageBrocker.emitProgress,
            )
        except Exception as e:
            loggingService.error(e)
            self.ui.call(self._on_update_download_failed)
            return
        self.ui.call(self._on_update_download_complete, new_exe_path)

    def _on_update_download_complete(self, new_exe_path):
        try:
            current_exe = os.path.abspath(sys.executable)
            updateService.handoffToUpdaterChild(new_exe_path, current_exe)
        except Exception as e:
            loggingService.error(e)
            self._on_update_download_failed()
            return
        MessageBrocker.emitProgressSuccess()
        # Close this window; the updater child (now running) will relaunch the
        # replaced exe. A small delay lets the user see the bar hit 100% green.
        self.root.after(400, self.quit_app)

    def _on_update_download_failed(self):
        self._software_updating = False
        MessageBrocker.emitProgress(0.0)
        self.statusPanel.showError(
            "Update failed",
            "Proceeding with the current version.",
        )
        # Give the user a moment to read the error, then resume normally.
        self.root.after(2500, self.load_collections_async)

    # ── COMPONENT LISTENERS ──────────────────────────────────────────────────

    def load_collections_async(self):
        self._on_collections_loading_start()

        def worker():
            try:
                getAllSubcriptions()
                self.ui.call(self._on_collections_loading_completed)
            except Exception as e:
                loggingService.error(e)
                self.ui.call(self._on_collections_loading_failed)
        threading.Thread(target=worker).start()

    def _on_collections_loading_start(self):
        self.lock_components_actions()
        self.actionPanel.set_state(ActionPanel.STATE_LOADING)
        self.statusPanel.showLoading()

    def _on_collections_loading_completed(self):
        self.unlock_components_actions()
        if self._first_launch and not checkIL2InstallPath():
            self._first_launch = False
            self.parametersPanel.auto_find_path(on_complete=self.start_scan_async)
        else:
            self.root.after(0, self.start_scan_async)

    def _on_collections_loading_failed(self):
        self.unlock_components_actions()
        self.actionPanel.set_state(ActionPanel.STATE_UP_TO_DATE)
        self.statusPanel.showError("Cannot load collection from server")

    def on_parameters_change(self):
        self.root.after(0, self.start_scan_async)

    def _ask_broad_search_via_status(self, on_answer):
        self.statusPanel.showPrompt(
            title="IL-2 not found via Steam",
            detail="Search your entire computer for the IL-2 folder?\nThis may take a minute.",
            primary_label="Search computer",
            on_primary=lambda: on_answer(True),
            secondary_label="Not now",
            on_secondary=lambda: on_answer(False),
        )

    # ── LOCK / UNLOCK ────────────────────────────────────────────────────────

    def lock_components_actions(self):
        self.parametersPanel.lock_actions()

    def unlock_components_actions(self):
        self.parametersPanel.unlock_actions()

    def _refresh_action_state(self):
        if self._hasPendingChanges():
            self.actionPanel.set_state(ActionPanel.STATE_UPDATES)
        else:
            self.actionPanel.set_state(ActionPanel.STATE_UP_TO_DATE)

    def _pendingSkinCount(self):
        if self.currentScanResult is None:
            return 0
        return len(self.currentScanResult.missingSkins) + len(self.currentScanResult.toBeUpdatedSkins)

    def _pendingCockpitCount(self):
        if self.currentScanResult is None:
            return 0
        return len(self.currentScanResult.toBeUpdatedCockpitNotes)

    def _hasPendingChanges(self):
        if self.currentScanResult is None:
            return False
        return self._pendingSkinCount() > 0 or self._pendingCockpitCount() > 0

    def _refresh_status_from_scan(self):
        if self.currentScanResult is None:
            self.statusPanel.showError("Scan did not complete")
        elif not self._hasPendingChanges():
            self.statusPanel.showUpToDate()
        else:
            self.statusPanel.showUpdatesNeeded(
                skins=self._pendingSkinCount(),
                cockpit=self._pendingCockpitCount(),
            )

    # ── SCAN & SYNC ──────────────────────────────────────────────────────────

    # ── PREVIEW STRIP ────────────────────────────────────────────────────────

    def _show_preview_strip(self):
        if self._preview_strip_visible:
            return
        self._preview_strip_visible = True
        self.previewStrip.pack(side="bottom", fill="x", before=self._status_container)
        self.statusPanel.setCompact(True)

    def _hide_preview_strip(self):
        if not self._preview_strip_visible:
            return
        self._preview_strip_visible = False
        self.previewStrip.pack_forget()
        self.previewStrip.clear()
        self.statusPanel.setCompact(False)

    @staticmethod
    def _preview_item(skin, kind):
        return (skin.id(), skin.name(), kind, skin.preview_image_path())

    def _show_scan_previews(self):
        result = self.currentScanResult
        if result is None or self._pendingSkinCount() == 0:
            self._hide_preview_strip()
            return
        items = [self._preview_item(skin, KIND_NEW) for skin in result.missingSkins]
        items += [self._preview_item(skin, KIND_UPDATE) for skin in result.toBeUpdatedSkins]
        self._show_preview_strip()
        self.previewStrip.show_pending(items)

    def _on_skin_sync_event(self, event, skin, value):
        # Called from download worker threads: only the strip's queue-based API is used here.
        if event == "started":
            kind = KIND_NEW if skin.id() in self._sync_new_skin_ids else KIND_UPDATE
            self.previewStrip.skin_started(*self._preview_item(skin, kind))
        elif event == "progress":
            self.previewStrip.skin_progress(skin.id(), value)
        elif event == "done":
            self.previewStrip.skin_done(skin.id(), bool(value))

    # ── SCAN & SYNC ──────────────────────────────────────────────────────────

    # The *_async methods run on the Tk thread: they update the UI, then start a
    # worker thread that does only the scan/sync and reports back via self.ui.

    def start_scan_async(self):
        self.currentScanResult = None
        self.actionPanel.set_cleanup_count(0)
        self._hide_preview_strip()
        self.lock_components_actions()
        self.actionPanel.set_state(ActionPanel.STATE_SCANNING)
        self.statusPanel.showScanning()
        threading.Thread(target=self._scan_worker).start()

    def _scan_worker(self):
        scan_result, scan_crashed, game_running = None, False, False
        try:
            scan_result = ScannerService.scanAll()
            # only asked when there is something to install (tasklist takes a moment)
            game_running = scan_result is not None and not scan_result.IsSyncUpToDate() and localService.isGameRunning()
        except Exception as e:
            loggingService.error(e)
            MessageBrocker.emitProgress(0)
            scan_crashed = True
        self.ui.call(self._on_scan_finished, scan_result, scan_crashed, game_running)

    def _on_scan_finished(self, scan_result, scan_crashed, game_running=False):
        self.currentScanResult = scan_result
        self.unlock_components_actions()
        self._refresh_action_state()
        if scan_crashed:
            self.statusPanel.showError("Scan failed")
        elif self.currentScanResult is None:
            self.statusPanel.showError(
                "IL-2 folder not found",
                "Click the path above and choose your IL-2 folder, or press Auto-detect.",
            )
        else:
            self._refresh_status_from_scan()
        self._show_scan_previews()
        self._retired_skins = scan_result.retiredSkins if scan_result is not None else []
        self.actionPanel.set_cleanup_count(len(self._retired_skins))
        # New or updated skins are synced silently, without waiting for "Update Now",
        # but not mid-flight: they wait until IL-2 closes ("Update Now" still works).
        if not scan_crashed and self._pendingSkinCount() > 0:
            if game_running:
                self.statusPanel.showWaitingForGame(skins=self._pendingSkinCount())
                self._wait_for_game_to_close()
            else:
                self.start_synchronization_async()

    def _wait_for_game_to_close(self):
        if self._waiting_for_game:
            return
        self._waiting_for_game = True

        def poll():
            while localService.isGameRunning():
                time.sleep(GAME_POLL_SECONDS)
            self.ui.call(self._on_game_closed)
        threading.Thread(target=poll, daemon=True).start()

    def _on_game_closed(self):
        self._waiting_for_game = False
        self.check_now()

    def remove_retired_skins(self):
        retired = self._retired_skins
        if not retired:
            return
        names = [f"{skin.name}  ({skin.game_asset_code})" for skin in retired]
        shown = "\n".join(names[:15]) + (f"\n\u2026and {len(names) - 15} more" if len(names) > 15 else "")
        if not messagebox.askyesno(
                "Remove old TBAS skins",
                f"These skins were installed by TBAS Sync but are no longer in their TBAS collection:\n\n{shown}\n\n"
                "Delete them from your IL-2 skins folder? This can't be undone.",
                icon="warning", default="no", parent=self.root):
            return
        if self.actionPanel._state not in (ActionPanel.STATE_UP_TO_DATE, ActionPanel.STATE_UPDATES):
            return
        for skin in retired:
            try:
                SynchronizerService.deleteSkinFromLocal(skin)
            except Exception as e:
                loggingService.error(e)
        self.start_scan_async()

    def start_synchronization_async(self):
        scan_result = self.currentScanResult
        if scan_result is None:
            loggingService.error("Sync launched with no scan result")
            return
        skins_to_update = self._pendingSkinCount()
        cockpit_to_update = self._pendingCockpitCount()
        il2_folder = getConf("IL2GBGameDirectory")
        needed = (sum(skin.size_in_b() for skin in scan_result.missingSkins + scan_result.toBeUpdatedSkins)
                  + sum(note["size"] for note in scan_result.toBeUpdatedCockpitNotes))
        free = shutil.disk_usage(il2_folder).free
        if free < needed + DISK_SPACE_MARGIN:
            drive = os.path.splitdrive(il2_folder)[0] or il2_folder
            self.statusPanel.showError(
                "Not enough disk space",
                f"Needs {ScannerService.bytesToString(needed)}, but {drive} has only "
                f"{ScannerService.bytesToString(free)} free. Free up space, then press \"Update Now\".",
            )
            if self._last_failure != "disk":
                self._notify(f"Not enough disk space to update {StatusPanel._format_counts(skins_to_update, cockpit_to_update)}.")
            self._last_failure = "disk"
            return
        self.lock_components_actions()
        self.actionPanel.set_state(ActionPanel.STATE_SYNCING)
        self.statusPanel.showSyncing(skins=skins_to_update, cockpit=cockpit_to_update)
        if skins_to_update > 0:
            self._sync_new_skin_ids = {skin.id() for skin in scan_result.missingSkins}
            # Queued before the worker starts, so it is applied before any skin event.
            self.previewStrip.start_sync()
            self._show_preview_strip()
        threading.Thread(target=self._sync_worker, args=(scan_result,)).start()

    def _sync_worker(self, scan_result):
        try:
            totals = SynchronizerService.updateAll(scan_result)
        except Exception as e:
            loggingService.error(e)
            self.ui.call(self._on_sync_crashed)
            return
        self.ui.call(self._on_sync_finished, *totals)

    def _on_sync_crashed(self):
        self.currentScanResult = None
        self.unlock_components_actions()
        self._refresh_action_state()
        self.statusPanel.showError(
            "Unexpected error during update",
            "See the log file for details.",
        )
        if self._last_failure != "crash":
            self._notify("Skin update failed. See the log file for details.")
        self._last_failure = "crash"
        if self._quit_after_sync:
            self.quit_app()

    def _on_sync_finished(self, skin_total, skin_success, cockpit_total, cockpit_success):
        self.currentScanResult = None
        self.unlock_components_actions()
        self._refresh_action_state()
        skin_failed = skin_total - skin_success
        cockpit_failed = cockpit_total - cockpit_success
        if skin_failed == 0 and cockpit_failed == 0:
            self.statusPanel.showSyncSuccess(skins=skin_success, cockpit=cockpit_success)
        else:
            self.statusPanel.showSyncPartialFailure(
                skin_failed=skin_failed,
                skin_total=skin_total,
                cockpit_failed=cockpit_failed,
                cockpit_total=cockpit_total,
            )
        if skin_failed:
            if self._last_failure != skin_failed:
                self._notify(f"{skin_failed} of {skin_total} skins failed to update. "
                             "See the log file for details.")
            self._last_failure = skin_failed
        else:
            self._last_failure = None
            if skin_success:
                self._notify(f"{StatusPanel._format_counts(skin_success, 0)} updated.")
        if self._quit_after_sync:
            self.quit_app()


# ── HELPERS ──────────────────────────────────────────────────────────────────

def open_link(link: str):
    webbrowser.open(link)

def open_link_HSDDocumentation():
    open_link("https://hsd-online.net")

def open_link_TBASDiscord():
    open_link("https://discord.gg/H38PyshRkN")


# ── ENTRY POINT ──────────────────────────────────────────────────────────────

def runMainGUI(check_for_update=False, force_update=False, prerelease=False, started_at_login=False):
    cleanTemporaryFolder()
    first_launch = not configurationFileExists()
    if first_launch:
        generateConfFile()
    root = tk.Tk()
    mainGUI = MainGUI(
        root,
        first_launch=first_launch,
        check_for_update=check_for_update,
        force_update=force_update,
        update_prerelease=prerelease,
        started_at_login=started_at_login,
    )
    root.mainloop()


def runMainGUIException(exception: Exception):
    root = tk.Tk()
    mainGUI = MainGUI(root, startup_exception=exception)
    root.mainloop()
