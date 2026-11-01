import os
import sys
import tempfile
import winreg

import Services.loggingService as loggingService
from Services.filesService import getTempFolderFullPath
from Services.paths import isFrozen

AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_VALUE = "TBASSync"


def setAutostart(enabled):
    """Start TBAS Sync with Windows (tray mode) via the per-user Run key, or remove that entry.
    Rewritten on every launch so it follows the exe if it is moved; the user can still disable
    it in Task Manager > Startup apps."""
    if not isFrozen():  # dev runs would register python.exe
        return
    try:
        if enabled:
            _register(sys.executable)
        else:
            _unregister()
    except Exception as e:
        loggingService.error(e)


def _register(exe_path):
    exe = os.path.normcase(os.path.abspath(exe_path))
    for scratch in (tempfile.gettempdir(), getTempFolderFullPath()):
        if exe.startswith(os.path.normcase(os.path.abspath(scratch)) + os.sep):
            return  # throwaway copy (run from inside a zip, or the updater's temp exe)
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, AUTOSTART_VALUE, 0, winreg.REG_SZ, f'"{os.path.abspath(exe_path)}"')


def _unregister():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE) as key:
        try:
            winreg.DeleteValue(key, AUTOSTART_VALUE)
        except FileNotFoundError:
            pass
