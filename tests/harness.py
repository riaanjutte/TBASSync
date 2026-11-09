"""Shared setup for the GUI tests.

Import this before anything from GUI/ or Services/. It makes a throwaway sandbox (a fake IL-2
install, also the dev-mode user data dir), loads resources from the repo, stubs the collection
download (no skins are fetched) and records autostart calls instead of writing the registry.
The show-window signal uses a test name, so a real running TBAS Sync is never touched.
"""
import ctypes
import json
import logging
import os
import shutil
import sys
import tempfile
import threading

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

SANDBOX = tempfile.mkdtemp(prefix="tbassync-test-")
IL2 = os.path.join(SANDBOX, "IL2")
os.makedirs(os.path.join(IL2, "bin", "game"))
open(os.path.join(IL2, "bin", "game", "Il-2.exe"), "wb").close()
os.chdir(SANDBOX)

import Services.filesService as filesService  # noqa: E402
filesService.getRessourcePath = lambda rel: os.path.join(REPO, "Resources", rel)
import Services.configurationService as configurationService  # noqa: E402
import Services.instanceService as instanceService  # noqa: E402
import Services.loggingService as loggingService  # noqa: E402
import GUI.mainGUI as mainGUI  # noqa: E402

TEST_SHOW_EVENT = "Local\\TBASSync-show-TEST"
instanceService.SHOW_EVENT_NAME = TEST_SHOW_EVENT
autostart_calls = []
mainGUI.autostartService.setAutostart = autostart_calls.append
mainGUI.MainGUI.load_collections_async = lambda self: None
real_getCockpitNotesPacks = mainGUI.remoteService.getCockpitNotesPacks
mainGUI.remoteService.getCockpitNotesPacks = lambda: []   # no network at window start
notifications = []   # Windows notifications the tray icon would have shown
mainGUI.TrayIcon.notify = lambda self, title, message: notifications.append(message)
loggingService.initialise_logger()

results = []


def write_config(**values):
    """Write the sandbox config (None removes a key) and make the app re-read it."""
    config = {"IL2GBGameDirectory": IL2, "cockpitNotesMode": "noSync", "applyCensorship": False,
              "autoRemoveUnregisteredSkins": False, "syncFriendsOfTBAS": False}
    config.update(values)
    json.dump({k: v for k, v in config.items() if v is not None}, open("TBASSync-config.json", "w"))
    configurationService.current_config = None


def saved_config():
    return json.load(open("TBASSync-config.json"))


def check(label, ok):
    results.append((label, bool(ok)))
    print(("PASS " if ok else "FAIL ") + label, flush=True)


def tray_threads():
    return [t for t in threading.enumerate() if t.is_alive() and "run" in repr(getattr(t, "_target", None))]


def wm_close(root):
    """Same message the window's X button sends."""
    ctypes.windll.user32.PostMessageW(int(root.wm_frame(), 16), 0x0010, 0, 0)


def run_steps(root, steps, delay_ms=700):
    """Run each step on the Tk thread, delay_ms apart, while root.mainloop() runs."""
    def run(i=0):
        if i < len(steps):
            steps[i]()
            root.after(delay_ms, run, i + 1)
    root.after(delay_ms, run)


def finish():
    logging.shutdown()
    os.chdir(REPO)
    shutil.rmtree(SANDBOX, ignore_errors=True)
    failed = [label for label, ok in results if not ok]
    print("RESULT:", "ALL PASS" if not failed else f"{len(failed)} FAILED: {failed}", flush=True)
    sys.exit(1 if failed else 0)
