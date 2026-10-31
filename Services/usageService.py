import json
import os
import sys
import threading
import time
import uuid

import requests

import Services.loggingService as loggingService
from Services.configurationService import config_file_path
from Services.paths import getUserDataFilePath
from Services.versionManager import getCurrentVersion

# Anonymous usage counter (see "USAGE STATISTICS" in releaseAssets/README.txt).
USAGE_URL = "https://vps-d09f8586.taild29594.ts.net/tbassync/ping"
DEVICE_FILE = "TBASSync-device.json"


def _device():
    """Random device ID + first-run time, created once. Set "usageTracking": false in the file to opt out."""
    path = getUserDataFilePath(DEVICE_FILE)
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        # existing users: the config file was created when they first set TBAS Sync up
        config = config_file_path()
        installed = int(os.path.getctime(config)) if os.path.exists(config) else int(time.time())
        device = {"id": uuid.uuid4().hex, "installed": installed, "usageTracking": True}
        with open(path, "w") as f:
            json.dump(device, f, indent=4)
        return device


def ping(event):
    """Fire-and-forget: never blocks the UI and never raises."""
    if not getattr(sys, "frozen", False):
        return   # source and test runs must not count as devices
    def send():
        try:
            device = _device()
            if device.get("usageTracking") is False:
                return
            requests.post(USAGE_URL, timeout=(5, 10), json={
                "id": device["id"], "version": getCurrentVersion(),
                "event": event, "installed": device.get("installed")})
        except Exception as e:
            loggingService.info(f"Usage ping skipped: {e}")
    threading.Thread(target=send, daemon=True).start()
