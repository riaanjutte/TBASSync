import sys

# paths/migration must run before anything opens the log file or config file.
from Services.paths import migrateLegacyStateFiles
migrateLegacyStateFiles()

import Services.loggingService as loggingService

from GUI.mainGUI import runMainGUI, runMainGUIException
from GUI.updaterGUI import runUpdaterGUI
from Services.updateService import setTargetExePath

######### MAIN ###############
if __name__ == "__main__":

    updater_mode = False
    debug_mode = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '-updater':
            updater_mode = True
        elif arg == '-debug':
            debug_mode = True
        elif arg == '-target' and i + 1 < len(args):
            # Path of the exe on disk that should be overwritten by the updater.
            setTargetExePath(args[i + 1])
            i += 1
        i += 1

    #INITIALISE LOGS
    loggingService.initialise_logger(debug_mode=debug_mode)

    try:
        #UPDATER MODE (invoked by an older self-updating version handing off to this build)
        if updater_mode:
            runUpdaterGUI(False)
        #NORMAL MODE
        else:
            runMainGUI()
    except Exception as e:
        loggingService.error(e)
        runMainGUIException(exception=e)
