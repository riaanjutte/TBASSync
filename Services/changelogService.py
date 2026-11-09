import re

import Services.loggingService as loggingService
from Services.configurationService import getConf, update_config_param
from Services.filesService import getRessourcePath
from Services.versionManager import currentVersion

# Bundled into the exe by TBASSync.spec.
CHANGELOG_FILE = "CHANGELOG.md"


def changesSince(changelog_text, last_seen, current=currentVersion):
    """The released sections newer than last_seen, up to current, newest first:
    [(version, date, [lines])]. "## [Unreleased]" is never shown."""
    sections = []
    for match in re.finditer(r"^## \[(\d+)\][ -]*(.*?)\s*$(.*?)(?=^## |\Z)", changelog_text, re.M | re.S):
        version = int(match.group(1))
        if last_seen < version <= current:
            lines = [line.rstrip() for line in match.group(3).strip().splitlines()]
            sections.append((version, match.group(2), lines))
    return sections


def pendingChangelog(first_launch):
    """What changed since the version the user last saw, or [] when there is nothing to show.
    A fresh install shows nothing: it has nothing to compare with."""
    if first_launch:
        markChangelogSeen()
        return []
    if getConf("lastSeenVersion") >= currentVersion:
        return []
    try:
        with open(getRessourcePath(CHANGELOG_FILE), encoding="utf-8") as f:
            return changesSince(f.read(), getConf("lastSeenVersion"))
    except OSError as e:   # dev runs have no bundled copy
        loggingService.warning(f"Cannot read the changelog: {e}")
        return []


def markChangelogSeen():
    update_config_param("lastSeenVersion", currentVersion)
