import requests
import json

from Services.configurationService import getConf
from Services.filesService import downloadFile, HTTP_TIMEOUT
from Services.messageBrocker import MessageBrocker

main_api_URL = "https://hsd-online.net/api"
collections_catalog_URL = f"{main_api_URL}/skinsCollections"
collection_brownser_URL = "https://hsd-online.net/collections/[collection_id]"
skins_download_URL = f"{main_api_URL}/skins/files/[path]"

class RemoteSkin:
    def __init__(self, json_raw_data: json) -> None:
        self._json_raw_data = json_raw_data

    #Translation of parameters from json
    def id(self):
        return self._json_raw_data["id"]
    def name(self):
        return self._json_raw_data["title"]
    def game_asset_code(self):
        return self._json_raw_data["game_asset"]["code_name"]
    def aircraft_name(self):
        return self._json_raw_data["game_asset"].get("display_name") or self.game_asset_code()
    def creator(self):
        return self._json_raw_data.get("creator") or ""
    def page_URL(self):
        return f"https://hsd-online.net/skins/{self.id()}"
    
    #get variant sub json data
    def unrestricted_variant_content(self) -> json:
        restricted_variant = self._json_raw_data.get("Restricted_Symbols")
        if restricted_variant is not None:
            return restricted_variant
        return self.restricted_variant_content()
    def restricted_variant_content(self) -> json:
        return self._json_raw_data.get("No_Restricted_Symbols")
    def get_variant_regarding_censorship_configuration(self) -> json:
        if getConf("applyCensorship"):
            return self.restricted_variant_content()
        else:
            return self.unrestricted_variant_content()

    class remoteDDSFileInfo:
        def __init__(self, destination_name: str, path: str, md5: str):
            self.destination_name = destination_name
            self.md5 = md5
            self.path = path
    
    def dds_files(self) -> list[remoteDDSFileInfo]:
        # no variant: the skin only exists with restricted symbols, and they are hidden
        variant = self.get_variant_regarding_censorship_configuration() or {}
        dds_files_info = []
        for file in variant.get("dds_files", []):
            dds_file = self.remoteDDSFileInfo(
                destination_name=file["destination_name"],
                path=file["path"],
                md5=file["MD5"]
            )
            dds_files_info.append(dds_file)
        
        return dds_files_info
    
    def size_in_b(self) -> int:
        if getConf("applyCensorship"):
            return self._json_raw_data["size_in_b_restricted_only"]
        else:
            return self._json_raw_data["size_in_b_unrestricted"]

    def preview_image_path(self) -> str | None:
        """HSD file path of the first preview image of the variant that will be installed."""
        variant = self.get_variant_regarding_censorship_configuration() or {}
        images = variant.get("preview_images") or []
        if not images:
            return None
        return images[0].get("path")

class RemoteCollection:
    def __init__(self, json_raw_data: json) -> None:
        self._json_raw_data = json_raw_data

    #Translation of parameters from json
    def id(self):
        return self._json_raw_data["id"]
    def name(self):
        return self._json_raw_data["name"]
    def description(self):
        return self._json_raw_data["description"]
    def creator_name(self):
        return self._json_raw_data["creator_name"]
    def skin_count(self) -> int:
        return self._json_raw_data["skins_count"]
    def size_in_b_unrestricted(self) -> int:
        return self._json_raw_data["size_in_b_unrestricted"]
    def size_in_b_restricted_only(self) -> int:
        return self._json_raw_data["size_in_b_restricted_only"]
    def browser_URL(self) -> str:
        return collection_brownser_URL.replace("[collection_id]", str(self.id()))
    def api_URL(self) -> str:
        return f"{main_api_URL}/skinsCollections/{self.id()}"
    
def downloadSkinPreview(preview_path: str) -> bytes:
    """Raw bytes of a skin preview image (HSD serves 960x540 JPEGs, ~160 KB)."""
    response = requests.get(skins_download_URL.replace("[path]", preview_path), timeout=HTTP_TIMEOUT)
    response.raise_for_status()
    return response.content

def getRemoteCollectionsCatalog() -> list[RemoteCollection]:
    try:
        response = requests.get(collections_catalog_URL, timeout=HTTP_TIMEOUT)

         # Check if the request was successful (status code 200)
        if response.status_code == 200:
            file_content = response.json()
            remote_collections = []
            for collection_json in file_content["collections"]:
                remote_collections.append(RemoteCollection(collection_json))
            return remote_collections
        else:
            raise Exception(f"Cannot retrieve collections catalog due to server response :{response.status_code}")
    except requests.ConnectionError as e:
        MessageBrocker.emitConsoleMessage("Cannot join server to retrieve collections catalog.")
        raise e
    except Exception as e:
        raise e


# Cockpit notes come from HSD's cockpit notes packs. The setting "cockpitNotesMode" holds the id of
# the chosen pack, or "noSync".
cockpit_notes_packs_URL = f"{main_api_URL}/cockpitNotesPacks"
cockpit_notes_download_URL = f"{main_api_URL}/cockpitNotesPacks/notes/[path]"
cockpit_notes_pack_page_URL = "https://hsd-online.net/cockpit-notes/[pack_id]"
# Choices saved before the app listed HSD's packs each named an IRRE catalog. Fizz moved those to
# these HSD packs in Oct 2026, when the IRRE server dropped them.
legacyCockpitNotesPackIds = {
    "originalPhotos": 4,      # "IL2 original game photos"
    "officialNumbers": 2,     # "Lefuneste IL2 specifications"
    "technochatNumbers": 3,   # "Lefuneste technochat measurements"
    "MetalheadNumbers": 1,    # "Metalhead measurements"
}
COCKPIT_NOTE_FILE_NAME = "custom_photo.dds"   # the file the game reads in planes/<aircraft>/Textures/


def selectedCockpitNotesPackId():
    """The HSD pack id of the saved choice; None when cockpit photos are off."""
    mode = getConf("cockpitNotesMode")
    if mode == "noSync":
        return None
    return legacyCockpitNotesPackIds.get(mode, mode)


def getCockpitNotesPacks():
    """The cockpit notes packs online on HSD for IL-2 Great Battles: [{"id", "title", ...}]."""
    # short timeout: the window waits for this list to fill the dropdown
    response = requests.get(cockpit_notes_packs_URL, timeout=10)
    response.raise_for_status()
    return [pack for pack in response.json()["packs"] if pack.get("state") == "Approved" and pack.get("game") == "IL2GB"]


def getCockpitNotesPack(pack_id):
    """One pack with its notes: {..., "notes": [{"game_asset": {"code_name", "display_name"}, "MD5", "thumbnail_path", ...}]}."""
    response = requests.get(f"{cockpit_notes_packs_URL}/{pack_id}", timeout=HTTP_TIMEOUT)
    response.raise_for_status()
    return response.json()


def downloadCockpitNoteThumbnail(thumbnail_path) -> bytes:
    """Raw bytes of a note's thumbnail (HSD serves WebP, about 717x1024 and 90 KB)."""
    response = requests.get(cockpit_notes_download_URL.replace("[path]", thumbnail_path), timeout=HTTP_TIMEOUT)
    response.raise_for_status()
    return response.content


def getCustomPhotosList():
    """The notes of the selected pack, as [{"aircraft", "md5", "size", "path"}]; [] when cockpit photos are off."""
    pack_id = selectedCockpitNotesPackId()
    if pack_id is None:
        return []

    try:
        response = requests.get(f"{cockpit_notes_packs_URL}/{pack_id}", timeout=HTTP_TIMEOUT)
    except requests.ConnectionError as e:
        MessageBrocker.emitConsoleMessage("Cannot join server to retrieve cockpit notes. Consider deactivating its synchronization.")
        raise e
    if response.status_code != 200:
        raise Exception(f"Cannot retrieve cockpit notes pack {pack_id} due to server response :{response.status_code}")
    pack = response.json()
    if pack.get("state") != "Approved":
        raise Exception(f"Cockpit notes pack {pack_id} is not online ({pack.get('state')})")
    return [{
        "aircraft": note["game_asset"]["code_name"],
        "md5": note["MD5"].lower(),
        "size": note["size_in_b"],
        "path": note["path"],
    } for note in pack.get("notes", [])]

def downloadCustomPhoto(cockpitNotesMode, cockpitNote):
    # HSD serves the file under another name; the game only reads custom_photo.dds
    return downloadFile(cockpit_notes_download_URL.replace("[path]", cockpitNote["path"]), cockpitNote["md5"],
                        destination_file_name=COCKPIT_NOTE_FILE_NAME)
