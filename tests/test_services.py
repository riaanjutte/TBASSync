"""Logic without a window: log rotation, version label, IL-2 detection, cockpit catalog check,
the one-line cockpit warning, and which skins count as old TBAS skins.
Usage: python tests/test_services.py"""
import logging
import os
import types

import harness
from harness import check
import requests
import Services.localService as localService
import Services.remoteService as remoteService
import Services.scannerService as scannerService
from Services.loggingService import LOG_MAX_BYTES, getLogFilePath
from Services.localService import LocalSkin
from Services.versionManager import currentVersion, getVersionLabel

# ── version label
check("version 16 shows as v1.6", getVersionLabel(16) == "v1.6")
check("version 20 shows as v2.0", getVersionLabel(20) == "v2.0")
check("default label is the current version", getVersionLabel() == getVersionLabel(currentVersion))

# ── IL-2 detection (this test itself runs as python.exe)
check("isGameRunning finds a running process", localService.isGameRunning("python.exe"))
check("isGameRunning is False for a missing process", not localService.isGameRunning("no-such-tbas-test.exe"))

# ── cockpit notes packs on HSD (requests stubbed: no network)
real_get = remoteService.requests.get
server = {}   # url -> (status, json), or an exception to raise


def fake_get(url, timeout):
    answer = server[url]
    if isinstance(answer, Exception):
        raise answer
    status, body = answer
    response = types.SimpleNamespace(status_code=status, json=lambda: body)
    response.raise_for_status = lambda: None if status == 200 else (_ for _ in ()).throw(requests.HTTPError(status))
    return response


remoteService.requests.get = fake_get
packs_url = "https://hsd-online.net/api/cockpitNotesPacks"
server[packs_url] = (200, {"packs": [{"id": 1, "state": "Approved", "game": "IL2GB"},
                                     {"id": 3, "state": "Pending", "game": "IL2GB"},
                                     {"id": 5, "state": "Approved", "game": "IL2GB"},
                                     {"id": 7, "state": "Approved", "game": "IL2KOREA"}]})
check("pack list: only approved Great Battles packs",
      [p["id"] for p in harness.real_getCockpitNotesPacks()] == [1, 5])
server[packs_url] = requests.ConnectionError("HSD down")
try:
    harness.real_getCockpitNotesPacks()
    check("pack list: HSD unreachable raises", False)
except requests.ConnectionError:
    check("pack list: HSD unreachable raises", True)

for saved, want in [("noSync", None), ("MetalheadNumbers", 1), ("originalPhotos", 4), (5, 5)]:
    harness.write_config(cockpitNotesMode=saved)
    check(f"saved choice {saved!r} is pack {want}", remoteService.selectedCockpitNotesPackId() == want)
server[f"{packs_url}/5"] = (200, {"id": 5, "state": "Approved", "notes": []})
check("a pack picked from the list (id 5) is read from HSD", remoteService.getCustomPhotosList() == [])

note = {"MD5": "D849097787E28CFE00A62FFA54750939", "size_in_b": 1398256, "path": "63?md5=d849",
        "game_asset": {"code_name": "A20B", "display_name": "A-20B", "game": "IL2GB"}}
server[f"{packs_url}/2"] = (200, {"id": 2, "state": "Approved", "notes": [note]})
harness.write_config(cockpitNotesMode="officialNumbers")
check("selected mode reads its HSD pack (pack 2)",
      remoteService.getCustomPhotosList() == [{"aircraft": "A20B", "md5": "d849097787e28cfe00a62ffa54750939",
                                               "size": 1398256, "path": "63?md5=d849"}])
server[f"{packs_url}/2"] = (200, {"id": 2, "state": "Pending", "notes": [note]})
try:
    remoteService.getCustomPhotosList()
    check("a pack taken offline raises", False)
except Exception as e:
    check("a pack taken offline raises", "not online" in str(e))
harness.write_config(cockpitNotesMode="noSync")
check("cockpit photos off: no request, empty list", remoteService.getCustomPhotosList() == [])
remoteService.requests.get = real_get

downloads = []
remoteService.downloadFile = lambda url, md5, destination_file_name=None: downloads.append((url, md5, destination_file_name))
remoteService.downloadCustomPhoto("officialNumbers", {"aircraft": "A20B", "md5": "abc", "size": 1, "path": "63?md5=abc"})
check("note downloads from HSD and is saved as custom_photo.dds",
      downloads == [("https://hsd-online.net/api/cockpitNotesPacks/notes/63?md5=abc", "abc", "custom_photo.dds")])

# ── a dead cockpit catalog is logged as one warning line, not a traceback
harness.write_config(cockpitNotesMode="officialNumbers")
scannerService.scanSkins = lambda: scannerService.ScanResult()
scannerService.scanCustomPhotos = lambda: (_ for _ in ()).throw(Exception("server response :404"))
log_before = open(getLogFilePath(), encoding="utf-8").read()
scannerService.scanAll()
logging.getLogger().handlers[0].flush()
new_log = open(getLogFilePath(), encoding="utf-8").read()[len(log_before):]
check("dead cockpit catalog: one WARNING line", new_log.count("WARNING - Cockpit notes catalog unavailable") == 1)
check("dead cockpit catalog: no traceback", "Traceback" not in new_log)

# ── old TBAS skins
skin = lambda code, name: types.SimpleNamespace(game_asset_code=lambda: code, name=lambda: name)
local = lambda code, name: LocalSkin(code, name, [])
collection = lambda cid, *skins, active=True: types.SimpleNamespace(id=cid, active=active, skins=list(skins),
                                                                    skins_count=len(skins))
fw, bf, own = local("Fw190A3", "TBAS Fw"), local("Bf109F4", "TBAS Bf"), local("Bf109F4", "My own skin")
names = lambda found: sorted(s.name for s in found)

installed = {}
found = scannerService.findRetiredSkins(installed, [fw, bf, own], [collection(5, skin("Fw190A3", "TBAS Fw"), skin("Bf109F4", "TBAS Bf"))])
check("first scan: nothing old, installed TBAS skins recorded",
      found == [] and installed == {"5": ["Bf109F4/TBAS Bf", "Fw190A3/TBAS Fw"]})

found = scannerService.findRetiredSkins(installed, [fw, bf, own], [collection(5, skin("Fw190A3", "TBAS Fw"))])
check("skin dropped from the collection: it is old", names(found) == ["TBAS Bf"])
check("the user's own skin is never old", own not in found)

for broken in (collection(None), collection(5)):   # 404 (no id) and an empty answer
    snapshot = {k: list(v) for k, v in installed.items()}
    check(f"collection that failed to load (id={broken.id}): nothing old, record kept",
          scannerService.findRetiredSkins(installed, [fw, bf], [broken]) == [] and installed == snapshot)

cut_off = collection(5, skin("Fw190A3", "TBAS Fw"))
cut_off.skins_count = 2   # the server said 2 skins, only 1 arrived
check("collection that arrived cut off: nothing old",
      scannerService.findRetiredSkins(dict(installed), [fw, bf], [cut_off]) == [])

check("collection switched off: its skins are not old",
      scannerService.findRetiredSkins(dict(installed), [fw, bf], [collection(5, active=False)]) == [])

found = scannerService.findRetiredSkins(dict(installed), [fw, bf], [collection(5, skin("Fw190A3", "TBAS Fw")),
                                                                     collection(91, skin("Bf109F4", "TBAS Bf"))])
check("dropped from one collection but still in another: not old", found == [])

found = scannerService.findRetiredSkins(installed, [fw], [collection(5, skin("Fw190A3", "TBAS Fw"))])
check("old skin deleted from disk: no longer offered, record forgets it",
      found == [] and installed == {"5": ["Fw190A3/TBAS Fw"]})

# ── log rotation (last: it floods the log)
for i in range(12_000):
    logging.info(f"filler line {i:05d} " + "x" * 80)
logging.getLogger().handlers[0].flush()
log = getLogFilePath()
check("log rotates into TBASSync.log.1", os.path.exists(log + ".1"))
check("no second backup is kept", not os.path.exists(log + ".2"))
check("each log file stays near the cap",
      os.path.getsize(log) <= LOG_MAX_BYTES and os.path.getsize(log + ".1") <= LOG_MAX_BYTES)

harness.finish()
