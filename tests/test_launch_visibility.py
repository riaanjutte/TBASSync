"""Launch rules: a user launch shows the window, the Windows sign-in launch (-autostart) stays in
the tray, and launching the exe again shows the running copy's window.
Usage: python tests/test_launch_visibility.py rules|signal
(each part needs its own process: a closed window's listener thread would eat the signal)"""
import contextlib
import subprocess
import sys
import time
import tkinter as tk
import types

import harness
from harness import check, mainGUI
import Services.autostartService as autostartService

PART = sys.argv[1]


def request_show_from_other_process():
    code = (f"import sys; sys.path.insert(0, {harness.REPO!r}); import Services.instanceService as s; "
            f"s.SHOW_EVENT_NAME = {harness.TEST_SHOW_EVENT!r}; print(s.requestShow())")
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30).stdout.strip()


def launch(tray_mode, started_at_login, steps):
    harness.write_config(trayMode=tray_mode)
    root = tk.Tk()
    gui = mainGUI.MainGUI(root, check_for_update=False, started_at_login=started_at_login)
    harness.run_steps(root, [lambda s=s: s(root) for s in steps] + [gui.quit_app], delay_ms=800)
    root.mainloop()
    time.sleep(0.5)


if PART == "rules":
    check("nothing running: requestShow() is False", request_show_from_other_process() == "False")

    written = []
    autostartService.winreg = types.SimpleNamespace(
        HKEY_CURRENT_USER=None, KEY_SET_VALUE=None, REG_SZ=1,
        OpenKey=lambda *a: contextlib.nullcontext(),
        SetValueEx=lambda key, name, reserved, kind, value: written.append(value))
    autostartService._register(r"C:\Games\TBASSync\TBASSync.exe")
    check("Run entry is '\"exe\" -autostart'", written == ['"C:\\Games\\TBASSync\\TBASSync.exe" -autostart'])

    for tray_mode, at_login, want in [(True, False, "normal"), (True, True, "withdrawn"),
                                      (False, True, "normal"), (False, False, "normal")]:
        label = f"tray {'on' if tray_mode else 'off'}, {'sign-in' if at_login else 'user'} launch: window {want}"
        launch(tray_mode, at_login, [lambda root, label=label, want=want: check(label, root.state() == want)])

elif PART == "signal":
    box = {}
    launch(True, True, [
        lambda root: (check("sign-in launch: hidden", root.state() == "withdrawn"),
                      box.__setitem__("ret", request_show_from_other_process())),
        lambda root: (check("second launch: requestShow() is True", box["ret"] == "True"),
                      check("second launch: running copy's window shown", root.state() == "normal"),
                      root.iconify()),
        lambda root: request_show_from_other_process(),
        lambda root: check("second launch while minimised: window restored", root.state() == "normal"),
    ])

harness.finish()
