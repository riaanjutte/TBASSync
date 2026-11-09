"""In the real window: waiting for IL-2 to close, the disk space check, the cleanup button, the
cockpit "Unavailable:" labels, the tray tooltip and the window title.
Usage: python tests/test_sync_guards.py"""
import os
import time
import tkinter as tk
import types

import harness
from harness import check, mainGUI
import Services.localService as localService
from GUI.actionsPanel import ActionPanel
from Services.scannerService import ScanResult
from Services.versionManager import getVersionLabel

harness.write_config(trayMode=True)
root = tk.Tk()
gui = mainGUI.MainGUI(root, check_for_update=False)
root.deiconify()

calls = {"scan": 0, "sync": 0, "notify": []}
gui.start_scan_async = lambda: calls.__setitem__("scan", calls["scan"] + 1)
gui._show_scan_previews = lambda: None   # previews download images
real_sync = gui.start_synchronization_async
gui.start_synchronization_async = lambda: calls.__setitem__("sync", calls["sync"] + 1)
gui._notify = lambda message: calls["notify"].append(message)


def remote_skin(size=1000):
    return types.SimpleNamespace(id=lambda: 1, name=lambda: "TBAS Test", size_in_b=lambda: size,
                                 game_asset_code=lambda: "Fw190A3")


def scan_with(missing=(), retired=()):
    result = ScanResult()
    result.missingSkins = list(missing)
    result.retiredSkins = list(retired)
    return result


def tooltip():
    return gui.tray._icon.title


def title():
    return gui.statusPanel.title_label.cget("text")


# ── waiting for IL-2: game "runs" for two polls, then closes
game_polls = iter([True, True, False])
localService.isGameRunning = lambda: next(game_polls, False)
mainGUI.GAME_POLL_SECONDS = 0.2


def waiting_for_game():
    gui._on_scan_finished(scan_with([remote_skin()]), False, game_running=True)
    check("IL-2 running: no automatic sync", calls["sync"] == 0)
    check("IL-2 running: status says it waits", title() == "1 skin waiting for IL-2 to close")
    check("IL-2 running: Update Now still available", gui.actionPanel._state == ActionPanel.STATE_UPDATES)
    check("IL-2 running: tray tooltip says it waits", "waiting for IL-2 to close" in tooltip())
    gui._on_scan_finished(scan_with([remote_skin()]), False, game_running=True)   # next 10-minute check
    check("second check while waiting: still no sync", calls["sync"] == 0)


def game_closed():
    check("IL-2 closed: a new check starts (and syncs from there)", calls["scan"] == 1 and not gui._waiting_for_game)


# ── disk space
def not_enough_space():
    gui.currentScanResult = scan_with([remote_skin(size=10 ** 15)])   # 1 PB
    gui.actionPanel.set_state(ActionPanel.STATE_UPDATES)
    real_sync()
    check("not enough space: sync does not start", gui.actionPanel._state == ActionPanel.STATE_UPDATES)
    check("not enough space: status says so", title() == "Not enough disk space")
    detail = gui.statusPanel.detail_label.cget("text")
    check("not enough space: detail names the sizes and drive",
          detail.startswith("Needs 931322.57 GB, but ") and " free." in detail)
    check("not enough space: one notification", len(calls["notify"]) == 1)
    real_sync()
    check("not enough space again: no second notification", len(calls["notify"]) == 1)


# ── cleanup button
skin_dir = os.path.join(harness.IL2, "data", "graphics", "skins", "Bf109F4")
os.makedirs(skin_dir)
old_file = os.path.join(skin_dir, "TBAS Old.dds")
open(old_file, "wb").write(b"dds")
old_skin = localService.LocalSkin("Bf109F4", "TBAS Old", [localService.ddsFile("TBAS Old.dds", 3, "md5")])
answers = iter([False, True, False])
asked = []
mainGUI.messagebox.askyesno = lambda title_, message, **kw: (asked.append(message), next(answers))[1]


def cleanup_offered():
    gui._on_scan_finished(scan_with(retired=[old_skin]), False)
    button = gui.actionPanel.cleanupButton
    root.update_idletasks()
    check("old skin found: cleanup button shown", button.winfo_ismapped() and button.cget("text") == "Remove 1 old TBAS skin")
    button.invoke()
    check("cleanup asks first and lists the skin", len(asked) == 1 and "TBAS Old  (Bf109F4)" in asked[0])
    check("answer No: nothing deleted", os.path.exists(old_file))
    button.invoke()
    check("answer Yes: skin file deleted", not os.path.exists(old_file))
    check("after deleting: a new check starts", calls["scan"] == 2)
    gui.actionPanel.set_state(ActionPanel.STATE_SYNCING)
    check("cleanup button disabled while syncing", str(button.cget("state")) == "disabled")
    gui._on_scan_finished(scan_with(retired=[old_skin]), False)   # found again, then an auto-sync runs
    gui._on_sync_finished(0, 0, 0, 0)                            # ...which clears currentScanResult
    button.invoke()
    check("cleanup still works after a sync finished", len(asked) == 3)

    # while the question is open, the 10-minute check starts a sync; then the user answers Yes
    open(old_file, "wb").write(b"dds")
    gui._on_scan_finished(scan_with(retired=[old_skin]), False)
    scans_before = calls["scan"]
    mainGUI.messagebox.askyesno = lambda *a, **kw: (gui.actionPanel.set_state(ActionPanel.STATE_SYNCING), True)[1]
    gui.remove_retired_skins()
    check("Yes while a sync runs: nothing deleted", os.path.exists(old_file))
    check("Yes while a sync runs: no second scan", calls["scan"] == scans_before)
    gui.actionPanel.set_state(ActionPanel.STATE_UP_TO_DATE)

    loads = []
    gui._load_cockpit_packs = lambda: loads.append(1)
    gui._periodic_check()
    time.sleep(0.3)   # the reload runs on a worker thread
    check("the 10-minute check reloads the cockpit pack list", loads == [1])

    gui._on_scan_finished(scan_with(), False)
    root.update_idletasks()
    check("no old skins: cleanup button hidden", not button.winfo_ismapped())


# ── cockpit labels, tooltip, title
def labels_and_title():
    panel = gui.parametersPanel
    dropdown = panel.cokpitNote_dropdown
    packs = [{"id": 1, "title": "Metalhead measurements"}, {"id": 2, "title": "Lefuneste IL2 specifications"},
             {"id": 5, "title": "FTC Cockpit Notes"}]
    off = "No synchronization, keep current images"

    def pick(label):
        dropdown.set(label)
        panel.on_cokpitNote_dropdown_change(None)
        return harness.saved_config()["cockpitNotesMode"]

    harness.write_config(trayMode=True, cockpitNotesMode="officialNumbers")   # saved by an older version
    panel.set_cockpit_packs(packs)
    check("every HSD pack is offered, A to Z, after 'off'",
          list(dropdown.cget("values")) == [off, "FTC Cockpit Notes", "Lefuneste IL2 specifications", "Metalhead measurements"])
    check("an old saved choice shows as its HSD pack", dropdown.get() == "Lefuneste IL2 specifications")
    check("picking a new pack saves its id", pick("FTC Cockpit Notes") == 5)

    panel.set_cockpit_packs(packs[:2])   # pack 5 taken offline
    check("saved pack not online: listed as Unavailable", dropdown.get() == "Unavailable: Cockpit notes pack #5")

    harness.write_config(trayMode=True, cockpitNotesMode="MetalheadNumbers")
    panel.set_cockpit_packs(None)
    check("while the packs load: the saved choice shows without 'Unavailable'",
          dropdown.get() == "Cockpit notes from Metalhead measurements")
    panel.set_cockpit_packs([])
    check("HSD unreachable: the saved choice shows as Unavailable",
          dropdown.get() == "Unavailable: Cockpit notes from Metalhead measurements")
    check("turning cockpit photos off saves noSync", pick(off) == "noSync")
    gui.statusPanel.showUpToDate()
    check("tray tooltip mirrors the status with a time",
          tooltip().startswith("TBAS Sync: Everything is up to date (") and tooltip().endswith(")"))
    check("window title shows the version", root.title() == f"TBAS Sync {getVersionLabel()}")
    gui.quit_app()


harness.run_steps(root, [waiting_for_game, lambda: None, lambda: None, game_closed,
                         not_enough_space, cleanup_offered, labels_and_title])
root.mainloop()
harness.finish()
