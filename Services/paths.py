"""
Central path resolution for user-writable state.

When frozen (running as the PyInstaller exe), config / log / hashes / temp live
under %APPDATA%\\TBASSync so the app works correctly regardless of where the
exe was placed (including read-only locations like Program Files, or the
throwaway temp dir Windows uses when an exe is launched from inside a zip).

When running from source (dev mode), state stays next to the working directory
for backwards compatibility with existing dev workflows.

This module MUST NOT import any other project module — it is imported by
loggingService, which is imported by nearly everything else.
"""

import os
import shutil
import sys


APP_FOLDER_NAME = "TBASSync"

# File names of the legacy / canonical state files that live in the user data dir.
_LEGACY_STATE_FILES = (
    "TBASSync-config.json",
    "TBASSync.log",
    "TBASSync-hashes.json",
)


def isFrozen():
    """True when running inside the PyInstaller-packaged exe."""
    return getattr(sys, "frozen", False)


def getUserDataDir():
    """
    Return the directory used for user-writable state.

    Frozen: %APPDATA%\\TBASSync (falls back to %USERPROFILE%\\TBASSync).
    Dev:    the current working directory (previous behavior).
    """
    if isFrozen():
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = os.path.join(base, APP_FOLDER_NAME)
    else:
        path = os.path.abspath(os.curdir)

    os.makedirs(path, exist_ok=True)
    return path


def getUserDataFilePath(fileName):
    """Absolute path to a file inside the user data dir."""
    return os.path.join(getUserDataDir(), fileName)


def migrateLegacyStateFiles():
    """
    One-shot migration: if state files exist next to the exe (old layout) but
    not yet in the user data dir (new layout), move them.

    Safe to call on every startup: no-op when nothing to migrate.
    Only runs in frozen mode — dev mode keeps files in CWD anyway.
    """
    if not isFrozen():
        return

    exeDir = os.path.dirname(sys.executable)
    targetDir = getUserDataDir()

    # If the exe is already running from inside the user data dir, skip.
    try:
        if os.path.normcase(os.path.abspath(exeDir)) == os.path.normcase(
            os.path.abspath(targetDir)
        ):
            return
    except Exception:
        pass

    for fileName in _LEGACY_STATE_FILES:
        oldPath = os.path.join(exeDir, fileName)
        newPath = os.path.join(targetDir, fileName)
        if os.path.exists(oldPath) and not os.path.exists(newPath):
            try:
                shutil.move(oldPath, newPath)
            except Exception:
                # Best-effort; if the move fails (read-only dir, locked file,
                # etc.) the app will simply treat it as first-launch.
                pass
