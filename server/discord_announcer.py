"""TBAS Sync Discord announcer (stdlib only, Python 3.9+).

    python3 discord_announcer.py    # one pass; run by tbassync-discord.timer every 10 minutes

Posts every skin that joined the TBAS collection on HSD since the last pass to a Discord webhook:
title (linking to the skin's page), author, aircraft and the No_Restricted_Symbols preview. The
Restricted_Symbols preview is never used. "New" means an id not in the state file, never a date:
creation_date is when a skin was made, not when it joined the collection. The first pass, with
no state file, records every current skin and posts nothing.

Environment:
    DISCORD_WEBHOOK_URL          required; never logged
    TBASSYNC_DISCORD_STATE       seen-ids file (default /var/lib/tbassync-discord/seen.json)
    TBASSYNC_DISCORD_COLLECTION  collection API URL (default https://hsd-online.net/api/skinsCollections/5)

Deploy (as root on the VPS, from a checkout of this repo):
    1. In Discord: channel settings > Integrations > Webhooks > New Webhook, name it, Copy Webhook URL.
    2. install -m 600 /dev/null /etc/tbassync-discord.env
       then put one line in it with `sudoedit /etc/tbassync-discord.env`:
           DISCORD_WEBHOOK_URL=<webhook URL>
    3. install -D -m 644 server/discord_announcer.py /opt/tbassync-discord/discord_announcer.py
       install -m 644 server/tbassync-discord.service server/tbassync-discord.timer /etc/systemd/system/
       systemctl daemon-reload
    4. systemctl start tbassync-discord.service       # first pass: records the current skins, posts nothing
       journalctl -u tbassync-discord -n 20           # expect "first run: recorded N skins"
    5. systemctl enable --now tbassync-discord.timer
"""
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
STATE_PATH = os.environ.get("TBASSYNC_DISCORD_STATE", "/var/lib/tbassync-discord/seen.json")
COLLECTION_URL = os.environ.get("TBASSYNC_DISCORD_COLLECTION", "https://hsd-online.net/api/skinsCollections/5")
SITE = "https://hsd-online.net"   # embed links stay on the real site even when the collection URL is overridden
USER_AGENT = "TBASSync-DiscordAnnouncer/1.0"   # Discord rejects the default Python-urllib agent
SAFE_VARIANT = "No_Restricted_Symbols"   # the other variant can show swastikas: never post it
MAX_EMBEDS = 10   # Discord's limit per message
MAX_RETRY_AFTER = 60


def fetch_skins():
    """The collection's skins, or None if the response is unusable or cut off."""
    req = urllib.request.Request(COLLECTION_URL, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        skins = data["skins"]
    except Exception as e:
        print(f"collection fetch failed: {type(e).__name__}: {e}", file=sys.stderr)
        return None
    if not (isinstance(skins, list) and len(skins) == data.get("skins_count")
            and all(isinstance(s, dict) and isinstance(s.get("id"), int) for s in skins)):
        print(f"collection incomplete: {len(skins) if isinstance(skins, list) else '?'} skins, "
              f"skins_count {data.get('skins_count')!r}; nothing posted", file=sys.stderr)
        return None
    return skins


def load_seen():
    """Set of seen ids, or None when there is no state file yet. A corrupt file raises: never treat it as empty."""
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return None


def save_seen(ids):
    directory = os.path.dirname(os.path.abspath(STATE_PATH))
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".seen-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(sorted(ids), f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, STATE_PATH)
    except BaseException:
        os.unlink(tmp)
        raise


def embed(skin):
    e = {"title": str(skin.get("title") or f"Skin {skin['id']}")[:256],
         "url": f"{SITE}/skins/{skin['id']}",
         "author": {"name": str(skin.get("creator") or "unknown")[:256]}}
    aircraft = (skin.get("game_asset") or {}).get("display_name")
    if aircraft:
        e["fields"] = [{"name": "Aircraft", "value": str(aircraft)[:1024], "inline": True}]
    previews = (skin.get(SAFE_VARIANT) or {}).get("preview_images") or []
    if previews and isinstance(previews[0], dict) and previews[0].get("path"):
        e["image"] = {"url": f"{SITE}/api/skins/files/{previews[0]['path']}"}
    return e


def post(payload):
    """True if Discord answered 2xx. Logs status codes and exception class names only: never the URL."""
    for attempt in (1, 2):
        try:   # Request() itself raises with the full URL in the message on a malformed URL
            req = urllib.request.Request(WEBHOOK_URL, json.dumps(payload).encode(), method="POST",
                                         headers={"Content-Type": "application/json", "User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30):
                return True
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 1:
                try:
                    wait = min(max(float(e.headers.get("Retry-After") or 1), 0), MAX_RETRY_AFTER)
                except ValueError:
                    wait = 1
                print(f"Discord rate limit, retrying in {wait:g}s")
                time.sleep(wait)
                continue
            print(f"Discord answered {e.code}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Discord post failed: {type(e).__name__}", file=sys.stderr)
            return False
    return False


def main():
    if not WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL is not set", file=sys.stderr)
        return 2
    skins = fetch_skins()
    if skins is None:
        return 1
    seen = load_seen()
    if seen is None:
        if not skins:
            print("first run sees an empty collection; not seeding, or the next run would post everything",
                  file=sys.stderr)
            return 1
        save_seen({s["id"] for s in skins})
        print(f"first run: recorded {len(skins)} skins, posted nothing")
        return 0
    new = sorted((s for s in skins if s["id"] not in seen), key=lambda s: s["id"])
    posted = 0
    for i in range(0, len(new), MAX_EMBEDS):
        batch = new[i:i + MAX_EMBEDS]
        if not post({"embeds": [embed(s) for s in batch]}):
            print(f"posted {posted} of {len(new)} new skins; the rest retry next run", file=sys.stderr)
            return 1
        seen.update(s["id"] for s in batch)   # ids are only ever added, so a skin that leaves and returns stays quiet
        save_seen(seen)
        posted += len(batch)
        for s in batch:
            print(f"posted skin {s['id']}: {s.get('title')}")
    print(f"{len(skins)} skins, {posted} new posted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
