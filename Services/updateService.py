import subprocess
import sys
import threading
import time
import os
import tkinter as tk

from packaging.version import Version

import Services.loggingService as loggingService
from Services.filesService import downloadFile, getTempFolderFullPath, copyFile
from Services.versionManager import getLastRelease, getCurrentVersion

exe_file_name = "TBASSync.exe"

# Set by main.py when the app is launched with `-target <path>`. The updater
# run uses this to know which exe on disk to overwrite with the downloaded
# build — we cannot infer it from sys.executable (that's the updater itself,
# which lives in the temp folder) or from CWD (unreliable once temp/ moved to
# APPDATA).
_target_exe_path = None


def setTargetExePath(path):
    global _target_exe_path
    _target_exe_path = path


def getTargetExePath():
    return _target_exe_path


def runNewIndependantProcess(args):
    loggingService.info(f"Running new independant command : {args}")
    subprocess.Popen(
        args,
        start_new_session=True,
    )


def checkForUpdate(prerelease=False, force=False):
    """Return the release_info dict if an update should be downloaded, else None.

    Single GitHub API hit (the old `isCurrentVersionUpToDate + getLastRelease`
    pattern did two). `force` bypasses the version comparison so -force-update
    always triggers a download when a release exists.
    """
    # Dev (non-frozen) runs must never trigger the updater: sys.executable is
    # python.exe, which we'd then hand to the updater child as -target and try
    # to overwrite with the downloaded build.
    if not getattr(sys, 'frozen', False):
        return None
    release_info = getLastRelease(prerelease=prerelease)
    if release_info is None:
        return None
    if force:
        return release_info
    remote_version = Version(release_info["tag_name"])
    current_version = Version(f"{getCurrentVersion()}")
    if remote_version <= current_version:
        return None
    return release_info


def downloadReleaseAsset(release_info, fileName, progress_callback=None):
    for asset in release_info["assets"]:
        if asset["name"] == fileName:
            return downloadFile(
                asset["browser_download_url"],
                progress_callback=progress_callback,
            )
    raise Exception(
        f"Cannot find {fileName} in release {release_info.get('tag_name')}"
    )


def handoffToUpdaterChild(new_exe_path, current_exe_path):
    """Launch the freshly-downloaded exe as an independent updater process.

    Runs before the current process exits; `start_new_session=True` detaches
    the child so it survives our shutdown.
    """
    runNewIndependantProcess(
        [new_exe_path, "-updater", "-target", current_exe_path]
    )


def _waitForTargetWritable(path, timeout_seconds=10):
    """Poll until `path` can be opened for write.

    Windows holds an image-section lock on a running exe; opening it 'r+b'
    raises PermissionError (ERROR_SHARING_VIOLATION / winerror 32) until the
    previous process exits and the kernel releases the image. Returns True on
    success, False on timeout.
    """
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with open(path, 'r+b'):
                return True
        except (PermissionError, OSError):
            time.sleep(0.2)
    return False


def _runUpdateTask():
    """The actual copy-and-relaunch work for Phase 2.

    Split from `runHeadlessUpdater` so the tiny "Updating…" window can drive
    this from a background thread while Tk's mainloop runs on the main thread.
    Every failure path falls back to launching *some* runnable exe so the user
    always ends up on a working app.
    """
    try:
        loggingService.info("Updater : start headless update")

        newExeFilePath = os.path.join(getTempFolderFullPath(), exe_file_name)
        if not os.path.exists(newExeFilePath):
            loggingService.warning(
                f"Updater : new exe missing at {newExeFilePath}, aborting update"
            )
            target = getTargetExePath()
            if target and os.path.exists(target):
                runNewIndependantProcess([target, "-no-update"])
            return

        targetPath = getTargetExePath()
        if not targetPath:
            loggingService.warning(
                "Updater : no -target supplied, falling back to CWD"
            )
            targetPath = os.path.join(os.path.curdir, exe_file_name)

        if os.path.exists(targetPath):
            if not _waitForTargetWritable(targetPath, timeout_seconds=10):
                # Target stayed locked — rather than loop downloading forever,
                # launch the temp-folder exe directly so the user still runs the
                # new build. The install path stays on the old version; next
                # launch will retry from there.
                loggingService.warning(
                    f"Updater : target {targetPath} still locked after 10s, "
                    f"launching temp exe directly"
                )
                runNewIndependantProcess([newExeFilePath])
                return

        try:
            copyFile(newExeFilePath, targetPath)
        except Exception as e:
            loggingService.error(e)
            loggingService.warning(
                f"Updater : copy to {targetPath} failed, launching temp exe"
            )
            runNewIndependantProcess([newExeFilePath])
            return

        runNewIndependantProcess([targetPath])
    except Exception as e:
        # Catch-all: under no circumstance should the updater crash into a Tk
        # crash dialog. main.py must not see an unhandled exception here.
        loggingService.error(e)
        try:
            temp_exe = os.path.join(getTempFolderFullPath(), exe_file_name)
            if os.path.exists(temp_exe):
                runNewIndependantProcess([temp_exe])
        except Exception as inner:
            loggingService.error(inner)


def runHeadlessUpdater():
    """Phase 2 of auto-update: copy the downloaded exe over the target and relaunch.

    Invoked by main.py when the freshly-downloaded exe is launched with
    `-updater -target <path>`. Shows a small 300×80 borderless "Updating…"
    label so the user has continuity while the old window is gone and the
    replaced exe is still starting up. If Tk can't initialise for any reason,
    we fall back to running the task with no UI.
    """
    try:
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes('-topmost', True)

        # Colors mirror TBASDarkTheme (BG_DARK, FG_PRIMARY, ACCENT_PRIMARY).
        # Hardcoded here to avoid pulling a GUI module into Services.
        bg = "#1c1c1c"
        fg = "#efefef"
        accent = "#e07820"
        root.configure(bg=bg)

        w, h = 300, 80
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        tk.Label(
            root,
            text="Updating TBAS Sync\u2026",
            font=("Bahnschrift Light Condensed", 14, "bold"),
            bg=bg,
            fg=fg,
        ).pack(expand=True, fill="both")
        tk.Frame(root, bg=accent, height=2).pack(side="bottom", fill="x")

        def worker():
            try:
                _runUpdateTask()
            finally:
                # Hand control back to the Tk thread to destroy the root —
                # calling destroy() from a worker thread isn't safe.
                try:
                    root.after(0, root.destroy)
                except tk.TclError:
                    pass

        threading.Thread(target=worker, daemon=True).start()
        root.mainloop()
    except Exception as e:
        # Tk init failed (e.g. no display). Run the task headlessly so the
        # update still completes.
        loggingService.error(e)
        _runUpdateTask()
