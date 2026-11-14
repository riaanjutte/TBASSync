import Services.loggingService as loggingService
from Services.configurationService import customPhotoSyncIsActive, checkIL2InstallPath
import Services.localService as localService
import Services.remoteService as remoteService
from Services.subscriptionsService import getAllSubcriptions
from Services.messageBrocker import MessageBrocker

class ScanResult:
    def __init__(self):
        self.subscribedSkins = list[remoteService.RemoteSkin]()
        self.missingSkins = list[remoteService.RemoteSkin]()
        self.toBeUpdatedSkins = list[remoteService.RemoteSkin]()
        self.toBeRemovedSkins= list[localService.LocalSkin]()
        self.previouslyInstalledSkins = list[localService.LocalSkin]()
        self.toBeUpdatedCockpitNotes = list()
        self.retiredSkins = list[localService.LocalSkin]()   # installed by TBAS Sync, since dropped from their collection
        
    def IsSyncUpToDate(self):
        if len(self.missingSkins) != 0:
            return False
        if len(self.toBeUpdatedSkins) != 0:
            return False
        return True

def bytesToString(bytesSize: int, forceSign: bool = False):
    
    file_size_bytes = abs(bytesSize)
    sign = "" 
    if bytesSize < 0:
        sign = "-"
    elif bytesSize > 0 and forceSign:
        sign = "+"

    file_size_kb = file_size_bytes / 1024

    if file_size_kb < 1:
        return f"{sign}{file_size_bytes} B"

    file_size_mb = file_size_kb / 1024

    if file_size_mb < 1:
        return f"{sign}{file_size_kb:.2f} KB"
    
    file_size_gb = file_size_mb / 1024

    if file_size_gb < 1:
        return f"{sign}{file_size_mb:.2f} MB"
    
    return f"{sign}{file_size_gb:.2f} GB"

def scanSkins():
    loggingService.info("START SCAN")
    scanResult = ScanResult()

    #get the local skins list in memory
    scanResult.previouslyInstalledSkins = localService.getSkinsList()
    
    #load all subscriptions and merge all skins in one list
    subscribedCollectionList = getAllSubcriptions()
    skins_ids = []
    for collection in subscribedCollectionList:
        if not collection.active:
            loggingService.info(f"Unactive subscribed collection : {collection.name}")
            continue    
        
        loggingService.info(f"Subscribed collection : {collection.name}")
        for skin in collection.skins:
            #do not load the same skin twice, and skip a skin with nothing to install for this member
            #(it only exists with restricted symbols, which are hidden): it would be "missing" on every check
            if skin.id() not in skins_ids and skin.dds_files():
                scanResult.subscribedSkins.append(skin)
                skins_ids.append(skin.id())
    
    #then check if we can find the remote skin matching with the local skin
    
    #initialise result collections
    scanResult.missingSkins = list[remoteService.RemoteSkin]()
    scanResult.toBeUpdatedSkins = list[remoteService.RemoteSkin]()

    for remoteSkin in scanResult.subscribedSkins:
        foundLocalSkin = None
        for localSkin in scanResult.previouslyInstalledSkins:
            #not the same A/C, no match
            if remoteSkin.game_asset_code() != localSkin.game_asset_code:
                continue
            
            #not the same skin name, no match
            if remoteSkin.name() != localSkin.name:
                continue
            
            #there is a match !
            foundLocalSkin = localSkin
                            
            #the skins is already there. Up to date ? 
            skinAsToBeUpdated = False

            for dds_file in remoteSkin.dds_files():
                #search the corresponding local file and if any difference is identified, then mark the skin as to be updated
                matching_local_file = None
                for local_dds_file in localSkin.dds_files:
                    if local_dds_file.fileName == dds_file.destination_name:
                        matching_local_file = local_dds_file
                        break
                
                if matching_local_file is None:
                    skinAsToBeUpdated = True
                    break
                
                if matching_local_file.fileMd5 != dds_file.md5:
                    skinAsToBeUpdated = True
                    break
            
            #if any modification has to be made, put the skin in the list to be updated
            if skinAsToBeUpdated:
                scanResult.toBeUpdatedSkins.append(remoteSkin)

            #and then no need to pursue the research as if we are there, we have found a match
            break
        
        if not foundLocalSkin:
            scanResult.missingSkins.append(remoteSkin)

    #Then list all local skins not present in the remote skins
    for localSkin in scanResult.previouslyInstalledSkins:
        foundRemoteSkin = None

        for remoteSkin in scanResult.subscribedSkins:
            if remoteSkin.game_asset_code() == localSkin.game_asset_code: #prefiltering to optimize search
                #TODO: Manage orphans skins
                if remoteSkin.name() == localSkin.name:
                    foundRemoteSkin = remoteSkin
                    break

        #the skin cannot be found
        if foundRemoteSkin is None:
            scanResult.toBeRemovedSkins.append(localSkin)

    try:
        installed = localService.loadInstalledSkins()
        scanResult.retiredSkins = findRetiredSkins(installed, scanResult.previouslyInstalledSkins, subscribedCollectionList)
        localService.saveInstalledSkins(installed)
    except Exception as e:  # the cleanup offer must never block the skin sync
        loggingService.warning(f"Cannot check for old TBAS skins: {e}")

    loggingService.info("END SCAN")
    return scanResult


def skinKey(game_asset_code, name):
    return f"{game_asset_code}/{name}"


def findRetiredSkins(installed: dict, localSkins, collections) -> list:
    """Skins TBAS Sync installed that their collection no longer offers, and that are still on disk.
    Updates `installed` (collection id -> skin keys) with that collection's skins on disk now.
    Only collections that loaded completely count: after a failed or cut-off download every missing
    skin would look retired."""
    local = {skinKey(skin.game_asset_code, skin.name): skin for skin in localSkins}
    loaded = {str(c.id): {skinKey(s.game_asset_code(), s.name()) for s in c.skins}
              for c in collections if c.active and c.id is not None and c.skins and len(c.skins) == c.skins_count}
    still_offered = set().union(*loaded.values())
    retired = {}
    for collection_id, offered in loaded.items():
        recorded = set(installed.get(collection_id, [])) & local.keys()   # forget skins gone from disk
        for key in recorded - still_offered:
            retired[key] = local[key]
        installed[collection_id] = sorted(recorded | (offered & local.keys()))
    return list(retired.values())


def scanCustomPhotos():
    
    localCustomPhotos = localService.getCustomPhotosList()
    remoteCustomPhotos = remoteService.getCustomPhotosList()

    toBeUpdatedPhotos = []

    for remotePhoto in remoteCustomPhotos:
        match = False
        for localPhoto in localCustomPhotos:
            if remotePhoto["aircraft"].lower() == localPhoto["aircraft"].lower():
                #we have a match
                if remotePhoto["md5"] != localPhoto["md5"]:
                    #photo has to be updated
                    toBeUpdatedPhotos.append(remotePhoto)
                match = True
                break
        
        if not match:
            toBeUpdatedPhotos.append(remotePhoto)

    return toBeUpdatedPhotos

def scanAll():
    #check conf is proper
    if not checkIL2InstallPath():
        MessageBrocker.emitConsoleMessage("!!! INVALID IL2 path !!!\nPlease modify the path from the parameters panel\nThis path should point to the IL2 root folder containing the 'bin' and 'data' folders")
        MessageBrocker.emitConsoleMessage("SCAN Cancelled")
        return None


    MessageBrocker.emitConsoleMessage("SCAN BEGINS...")
    MessageBrocker.emitProgress(0) #TEMP PROGRESS
    
    scanResult = scanSkins()
    if customPhotoSyncIsActive():
        # A broken cockpit-photo source must not block skin sync (the IRRE catalogs went 404 in Oct 2026).
        try:
            scanResult.toBeUpdatedCockpitNotes = scanCustomPhotos()
        except Exception as e:
            # one line, not a traceback: this repeats on every scan while the catalog is down
            loggingService.warning(f"Cockpit notes catalog unavailable, skipping cockpit photos: {e}")
            MessageBrocker.emitConsoleMessage("Cockpit notes catalog unavailable, skipping cockpit photos.")
    MessageBrocker.emitProgress(0)
    MessageBrocker.emitConsoleMessage("SCAN FINISHED")
    return scanResult