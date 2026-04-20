import subprocess
import sys
import time
import os

import Services.loggingService as loggingService
from Services.filesService import downloadFile, getTempFolderFullPath, copyFile
from Services.versionManager import getLastRelease

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


def downloadLastReleaseFile(fileName, prerelease = False):
    release_info = getLastRelease(prerelease = prerelease)
    for asset in release_info["assets"]:
        if asset["name"] == fileName:
            return downloadFile(asset["browser_download_url"])

    #file not found
    raise Exception(f"Cannot find {fileName} in last release")


def runNewIndependantProcess(args):
    loggingService.info(f"Running new independant command : {args}")
    subprocess.Popen(
        args,  # Arguments to the updater
        start_new_session=True
    )


def downloadAndRunUpdater(prerelease = False):

    loggingService.info("Updater : Start download And Run updater")
    #download the last EXE
    newExePath = downloadLastReleaseFile(exe_file_name, prerelease = prerelease)

    # Pass the path of THIS exe so the updater knows which file to replace.
    # sys.executable is reliable here (we're in the currently-running exe, not
    # yet in the downloaded updater).
    currentExePath = os.path.abspath(sys.executable)

    #run the last updater in an independant process
    runNewIndependantProcess([newExePath, "-updater", "-target", currentExePath])

def replaceAndLaunchMainExe(prerelease = False):
    loggingService.info("Updater : Replace and Launch Main Exe")

    newExeFilePath = os.path.join(getTempFolderFullPath(), exe_file_name)
    #HACK : if the new exe is not there, rerun the download
    if not os.path.exists(newExeFilePath):
        loggingService.warning(f"Autoupdater Cannot find the last exe file at {newExeFilePath}")
        return downloadAndRunUpdater(prerelease = prerelease)

    #add a timer to make sure previous main exe is stopped
    #TODO : perform a while checker
    time.sleep(5)

    # Destination is the original exe passed through `-target`. Fall back to
    # CWD/exe_file_name to preserve old behavior if -target wasn't supplied
    # (e.g., an older build handed off to this updater).
    mainExeFilePath = getTargetExePath()
    if not mainExeFilePath:
        loggingService.warning(
            "Updater : no -target path supplied, falling back to CWD"
        )
        mainExeFilePath = os.path.join(os.path.curdir, exe_file_name)

    copyFile(newExeFilePath, mainExeFilePath)

    #then run !
    runNewIndependantProcess([mainExeFilePath])
