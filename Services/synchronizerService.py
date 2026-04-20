import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.exceptions import HTTPError

import Services.localService as localService
import Services.remoteService as remoteService
import Services.filesService as filesService
from Services.messageBrocker import MessageBrocker
from Services.configurationService import getConf, customPhotoSyncIsActive
from Services.scannerService import ScanResult
import Services.loggingService as loggingService

DOWNLOAD_WORKERS = 4

def updateRegisteredSkins(scanResult: ScanResult, progress_base: float = 0.0) -> tuple[int, int]:

    progress_span = 1.0 - progress_base
    MessageBrocker.emitProgress(progress_base)

    skinsToSync = list(scanResult.missingSkins) + list(scanResult.toBeUpdatedSkins)
    totalSkins = len(skinsToSync)

    # Flatten to (skin, dds_file) tasks so we can pool across all files.
    tasks = []
    for skin in skinsToSync:
        for dds in skin.dds_files():
            tasks.append((skin, dds))
    totalFiles = len(tasks)

    if totalFiles == 0:
        MessageBrocker.emitProgress(1.0)
        return totalSkins, totalSkins

    file_fractions = [0.0] * totalFiles
    skin_failed: dict = {skin: False for skin in skinsToSync}
    skin_pending: dict = {skin: 0 for skin in skinsToSync}
    skin_temp_paths: dict = {skin: [] for skin in skinsToSync}
    for skin, _ in tasks:
        skin_pending[skin] += 1
    lock = threading.Lock()

    def update_total_bar():
        total = sum(file_fractions) / totalFiles
        MessageBrocker.emitProgress(progress_base + total * progress_span)

    def make_byte_callback(file_index):
        def cb(byte_fraction):
            file_fractions[file_index] = byte_fraction
            update_total_bar()
        return cb

    def download_one(file_index, skin, dds):
        url = remoteService.skins_download_URL.replace("[path]", dds.path)
        # Each download gets its own temp subdir so parallel writes can't collide
        # when two skins share a destination_name.
        subdir = f"{skin.game_asset_code()}_{uuid.uuid4().hex}"
        return filesService.downloadFile(
            url=url,
            destination_file_name=dds.destination_name,
            expectedMD5=dds.md5,
            progress_callback=make_byte_callback(file_index),
            temp_subdir=subdir,
        )

    MessageBrocker.emitConsoleMessage(
        f"<blue>Downloading {totalFiles} file(s) across {totalSkins} skin(s) "
        f"with {DOWNLOAD_WORKERS} workers...</blue>"
    )

    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as executor:
        futures = {
            executor.submit(download_one, idx, skin, dds): (idx, skin, dds)
            for idx, (skin, dds) in enumerate(tasks)
        }
        for future in as_completed(futures):
            idx, skin, dds = futures[future]
            ok, temp_path = False, None
            try:
                temp_path = future.result()
                ok = True
            except Exception as e:
                MessageBrocker.emitConsoleMessage(
                    f"<red>Technical error : cannot sync {skin.name()} ({dds.destination_name})</red>"
                )
                loggingService.error(e)
                # Force this file's slot to "complete" so the total bar doesn't stick.
                file_fractions[idx] = 1.0
                update_total_bar()

            with lock:
                if ok:
                    skin_temp_paths[skin].append(temp_path)
                else:
                    skin_failed[skin] = True
                skin_pending[skin] -= 1
                skin_done = skin_pending[skin] == 0
                ready_to_move = skin_done and not skin_failed[skin]
                paths_to_move = list(skin_temp_paths[skin]) if ready_to_move else []

            if skin_done:
                if ready_to_move:
                    for path in paths_to_move:
                        final_path = localService.moveSkinFromPathToDestination(path, skin.game_asset_code())
                        MessageBrocker.emitConsoleMessage(f"Downloaded {skin.name()} -> {final_path}")
                else:
                    MessageBrocker.emitConsoleMessage(
                        f"<red>Skipping {skin.name()} install — some files failed to download</red>"
                    )

    successUpdates = sum(1 for skin in skinsToSync if not skin_failed[skin])
    return totalSkins, successUpdates


def deleteUnregisteredSkins(scanResult: ScanResult):
    for skin in scanResult.toBeRemovedSkins:
        deleteSkinFromLocal(skin)

def deleteSkinFromLocal(localSkinInfo: localService.LocalSkin):
    localService.removeSkin(localSkinInfo)
    MessageBrocker.emitConsoleMessage(f"<chocolate>Deleted skin : {localSkinInfo.name}</chocolate>")


def updateCustomPhotos(toBeUpdatedPhotos, progress_budget: float = 0.2) -> tuple[int, int]:
    cockpitMode = getConf("cockpitNotesMode")
    MessageBrocker.emitProgress(0)
    totalUpdates = len(toBeUpdatedPhotos)
    if totalUpdates == 0:
        return 0, 0

    _progress_step = progress_budget / totalUpdates
    _progress = 0.0
    successUpdates = 0

    for customPhoto in toBeUpdatedPhotos:
        try:
            downloadedFile = remoteService.downloadCustomPhoto(cockpitMode, customPhoto)
            localService.moveCustomPhotoFromPathToDestination(downloadedFile, customPhoto["aircraft"])
            successUpdates += 1
        except HTTPError as httpError:
            loggingService.error(f"Cockpit photo download failed: {customPhoto.get('aircraft')} — {httpError}")
        except Exception as e:
            loggingService.error(e)

        _progress += _progress_step
        MessageBrocker.emitProgress(_progress)

    return totalUpdates, successUpdates

def updateAll(scanResult: ScanResult) -> tuple[int, int, int, int]:
    MessageBrocker.emitProgress(0)
    loggingService.info("START SYNC")

    cockpitItems = scanResult.toBeUpdatedCockpitNotes if customPhotoSyncIsActive() else []
    cockpitBudget = 0.2 if len(cockpitItems) > 0 else 0.0

    cockpitTotal, cockpitSuccess = 0, 0
    if cockpitBudget > 0:
        try:
            cockpitTotal, cockpitSuccess = updateCustomPhotos(cockpitItems, progress_budget=cockpitBudget)
        except Exception as e:
            loggingService.error(f"Cockpit photo sync crashed: {e}")
            cockpitTotal = len(cockpitItems)
            cockpitSuccess = 0

    skinsPlanned = len(scanResult.missingSkins) + len(scanResult.toBeUpdatedSkins)
    skinTotal, skinSuccess = 0, 0
    try:
        skinTotal, skinSuccess = updateRegisteredSkins(scanResult, progress_base=cockpitBudget)
    except Exception as e:
        loggingService.error(f"Skin sync crashed: {e}")
        skinTotal = skinsPlanned
        skinSuccess = 0

    loggingService.info(
        f"END SYNC skins={skinSuccess}/{skinTotal} cockpit={cockpitSuccess}/{cockpitTotal}"
    )
    MessageBrocker.emitProgress(1)
    if skinTotal == skinSuccess and cockpitTotal == cockpitSuccess:
        MessageBrocker.emitProgressSuccess()

    return skinTotal, skinSuccess, cockpitTotal, cockpitSuccess
