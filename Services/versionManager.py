import requests
from packaging.version import Version


#This is THE reference for the current version
#Change version here when preparing a new release
currentVersion = 11

GITHUB_REPO_URL = "https://api.github.com/repos/riaanjutte/TBASSync"

def getCurrentVersion():
    return currentVersion

def getReleases():
    response = requests.get(f"{GITHUB_REPO_URL}/releases")
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception ("Cannot get current version information")
    
def getLastRelease(draft = False, prerelease = False):
    lastRelease = None
    for release in getReleases():
        if release["draft"] and not draft:
            continue
        if release["prerelease"] and not prerelease:
            continue
        if lastRelease is None:
            lastRelease = release
        else:
            if Version(release["tag_name"]) > Version(lastRelease["tag_name"]):
                lastRelease = release

    return lastRelease

#Direct access to provide the current version when calling directly that file (used for the build script)
if __name__ == "__main__":
    print(getCurrentVersion())