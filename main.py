import sys

# paths/migration must run before anything opens the log file or config file.
from Services.paths import migrateLegacyStateFiles
migrateLegacyStateFiles()

import Services.loggingService as loggingService
import Services.updateService as updateService

from GUI.mainGUI import runMainGUI, runMainGUIException

######### MAIN ###############
if __name__ == "__main__":

    force_update = False
    updater_mode = False
    no_update = False
    update_withPrerelease = False
    debug_mode = False

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
        try:
            runMainGUI(
                check_for_update=(not no_update),
                force_update=force_update,
                prerelease=update_withPrerelease,
            )
        except Exception as e:
            loggingService.error(e)
            runMainGUIException(exception=e)
