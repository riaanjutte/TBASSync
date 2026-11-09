import ctypes
import threading
from ctypes import wintypes

import Services.loggingService as loggingService

# Launching the exe while TBAS Sync already runs (usually hidden in the tray) signals this
# event, and the running copy shows its window.
SHOW_EVENT_NAME = "Local\\TBASSync-show"
EVENT_MODIFY_STATE = 0x0002
INFINITE = 0xFFFFFFFF
WAIT_OBJECT_0 = 0
ASFW_ANY = -1

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateEventW.restype = wintypes.HANDLE
_kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
_kernel32.OpenEventW.restype = wintypes.HANDLE
_kernel32.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
_kernel32.SetEvent.argtypes = [wintypes.HANDLE]
_kernel32.WaitForSingleObject.restype = wintypes.DWORD
_kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def listenForShowRequests(on_show):
    """In the running copy: call on_show (from a background thread) each time the exe is launched again."""
    handle = _kernel32.CreateEventW(None, False, False, SHOW_EVENT_NAME)
    if not handle:
        loggingService.error(f"Cannot create the show event (error {ctypes.get_last_error()})")
        return

    def wait():
        while _kernel32.WaitForSingleObject(handle, INFINITE) == WAIT_OBJECT_0:
            on_show()

    threading.Thread(target=wait, name="show-requests", daemon=True).start()


def requestShow():
    """In a second launch: ask the running copy to show its window.
    False when nothing listens (an older version is running, or it is still starting)."""
    handle = _kernel32.OpenEventW(EVENT_MODIFY_STATE, False, SHOW_EVENT_NAME)
    if not handle:
        return False
    try:
        # the user just launched us, so we may hand the foreground to the running copy
        ctypes.windll.user32.AllowSetForegroundWindow(ASFW_ANY)
        return bool(_kernel32.SetEvent(handle))
    finally:
        _kernel32.CloseHandle(handle)
