"""The "Keep running in the background" checkbox, in the real window with a real tray icon.
Usage: python tests/test_background_checkbox.py on|off|fresh
  on    - config has no trayMode key, so the default applies
  off   - "trayMode": false
  fresh - no config file yet (first launch)"""
import sys
import time
import tkinter as tk

import harness
from harness import check, mainGUI, tray_threads, wm_close

MODE = sys.argv[1]
if MODE == "fresh":
    from Services.configurationService import generateConfFile
    generateConfFile()   # what runMainGUI does on first launch
else:
    harness.write_config(trayMode=False if MODE == "off" else None)

root = tk.Tk()
gui = mainGUI.MainGUI(root, check_for_update=False)
panel = gui.parametersPanel
calls = harness.autostart_calls

if MODE == "off":
    steps = [
        lambda: (check("off: checkbox unticked", panel.background_var.get() is False),
                 check("off: window visible at launch", root.state() == "normal"),
                 check("off: no tray icon", gui.tray is None and not tray_threads()),
                 check("off: autostart removed", calls == [False]),
                 panel.background_check.invoke()),
        lambda: (check("tick: tray icon starts", gui.tray is not None and len(tray_threads()) == 1),
                 check("tick: saved true", harness.saved_config()["trayMode"] is True),
                 check("tick: autostart registered", calls[-1] is True),
                 wm_close(root)),
        lambda: (check("tick: X hides the window", root.state() == "withdrawn"),
                 check("tick: X says the app keeps running in the background",
                       len(harness.notifications) == 1
                       and harness.notifications[0].startswith("TBAS Sync is still running in the background")),
                 root.deiconify(), panel.background_check.invoke()),
        lambda: (check("untick again: tray icon stopped", gui.tray is None and not tray_threads()),
                 check("untick again: saved false", harness.saved_config()["trayMode"] is False),
                 wm_close(root)),   # X must now quit: mainloop ends
    ]
else:
    steps = [
        lambda: (check(f"{MODE}: checkbox ticked by default", panel.background_var.get() is True),
                 check(f"{MODE}: tray icon running", gui.tray is not None and len(tray_threads()) == 1),
                 check(f"{MODE}: autostart registered", calls == [True]),
                 panel.background_check.invoke()),
        lambda: (check("untick: tray icon stopped", gui.tray is None and not tray_threads()),
                 check("untick: saved false", harness.saved_config()["trayMode"] is False),
                 check("untick: autostart removed", calls[-1] is False),
                 gui._notify("must not raise without a tray icon"),
                 wm_close(root)),   # X must quit: mainloop ends
    ]

harness.run_steps(root, steps)
root.mainloop()
time.sleep(1)
check("app quit and no tray icon left", not tray_threads())
check("quitting showed no 'still running' notification",
      sum("still running in the background" in n for n in harness.notifications) == (1 if MODE == "off" else 0))
harness.finish()
