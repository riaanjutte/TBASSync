import sys

# paths/migration must run before anything opens the log file or config file.
from Services.paths import migrateLegacyStateFiles
migrateLegacyStateFiles()

import Services.loggingService as loggingService
import Services.updateService as updateService
import Services.instanceService as instanceService

from GUI.mainGUI import runMainGUI, runMainGUIException


def acquireSingleInstance():
    """Named mutex so only one TBAS Sync (tray app) syncs into the skins folder.
    Returns the handle (keep it alive for the process lifetime), or None if another instance runs."""
    import ctypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel32.CreateMutexW(None, False, "Local\\TBASSync")
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        return None
    return handle


######### MAIN ###############
if __name__ == "__main__":

    force_update = False
    updater_mode = False
    no_update = False
    update_withPrerelease = False
    debug_mode = False
    started_at_login = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '-updater':
            updater_mode = True
        elif arg == '-no-update':
            no_update = True
        elif arg == '-force-update':
            force_update = True
        elif arg == '-prerelease':
            update_withPrerelease = True
        elif arg == '-debug':
            debug_mode = True
        elif arg == '-autostart':
            # Launched by Windows at sign-in (the Run entry), not by the user.
            started_at_login = True
        elif arg == '-target' and i + 1 < len(args):
            # Path of the exe on disk that should be overwritten by the updater.
            updateService.setTargetExePath(args[i + 1])
            i += 1
        i += 1

    #INITIALISE LOGS
    loggingService.initialise_logger(debug_mode=debug_mode)

    #UPDATER MODE — headless Phase 2 of auto-update. Self-contained error
    #handling; must NOT propagate to runMainGUIException (no Tk in this path).
    if updater_mode:
        updateService.runHeadlessUpdater()
    #NORMAL MODE — mainGUI runs the update check/download in-window.
    else:
        instance_mutex = acquireSingleInstance()
        if instance_mutex is None:
            if not instanceService.requestShow():
                import ctypes
                ctypes.windll.user32.MessageBoxW(None, "TBAS Sync is already running.", "TBAS Sync", 0x40)
            sys.exit(0)
        try:
            runMainGUI(
                check_for_update=(not no_update),
                force_update=force_update,
                prerelease=update_withPrerelease,
                started_at_login=started_at_login,
            )
        except Exception as e:
            loggingService.error(e)
            runMainGUIException(exception=e)
