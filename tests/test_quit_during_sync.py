"""Quitting while a sync runs: the app stays alive until the sync ends, then quits.
Usage: python tests/test_quit_during_sync.py on|off   (tray mode)"""
import sys
import tkinter as tk

import harness
from harness import check, mainGUI, wm_close
from GUI.actionsPanel import ActionPanel

MODE = sys.argv[1]
harness.write_config(trayMode=MODE == "on")
root = tk.Tk()
gui = mainGUI.MainGUI(root, check_for_update=False)


def quit_during_sync():
    root.deiconify()
    gui.actionPanel._state = ActionPanel.STATE_SYNCING
    if MODE == "on":
        gui.ui.call(gui.quit_app)   # tray menu "Quit" (in tray mode X only hides the window)
    else:
        wm_close(root)


def after_quit():
    # tray mode hides the window (the tray icon stays); without it, a taskbar entry must stay
    want = "withdrawn" if MODE == "on" else "iconic"
    check(f"{MODE}: quit during sync -> window {want}", root.state() == want)
    check(f"{MODE}: app still running during sync", root.winfo_exists())
    gui._on_sync_finished(0, 0, 0, 0)   # the sync ends: the app must now quit


harness.run_steps(root, [quit_during_sync, after_quit])
root.mainloop()
check(f"{MODE}: app quit after the sync finished", True)
check(f"{MODE}: quitting showed no 'still running' notification",
      not any("still running in the background" in n for n in harness.notifications))
harness.finish()
