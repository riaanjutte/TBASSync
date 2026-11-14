TBAS Sync
=========

TBAS Sync downloads and installs IL-2: Great Battles skin packs from the HSD
website and keeps your local skins folder in sync with your subscribed
collections.


INSTALLATION
------------
Recommended: the installer.

1. Download TBASSync-Setup.exe from the Releases page:
       https://github.com/riaanjutte/TBASSync/releases

2. Run it. It installs TBAS Sync for your Windows account only (no admin
   password needed) into %LOCALAPPDATA%\Programs\TBAS Sync and adds a Start
   Menu shortcut. Tick "Create a desktop shortcut" if you want one too.

   TBAS Sync isn't code-signed, so Windows may show a blue "Windows
   protected your PC" box. Click "More info", then "Run anyway".

3. Leave "Start TBAS Sync" ticked on the last page and click Finish.

4. On first launch the app tries to auto-detect your IL-2 installation. If
   it can't find it, you'll be asked to point it at the folder that contains
   bin\game\Il-2.exe.

Portable option: the zip (this file came in it).

1. Extract the zip to a folder of your choice (Desktop, Documents, a
   dedicated "Tools" folder, wherever you like).

   IMPORTANT: do NOT run TBASSync.exe directly from inside the zip. Windows
   will extract it to a throwaway temporary folder, your settings will not
   persist, and the app may not behave correctly.

2. Double-click TBASSync.exe. First launch works as in step 4 above.


RUNNING IN THE SYSTEM TRAY
--------------------------
TBAS Sync runs in the system tray (the icons next to the clock). It checks
for new or updated skins when it starts and every 10 minutes, installs them
without asking, and shows a Windows notification that names the new skins,
for example "New skin: TBAS Bf110-E2 by MayheM-1."

While IL-2 is running it doesn't install anything, so nothing downloads in
the middle of a flight. New skins wait until you quit the game. To install
them anyway, open the window and press "Update Now".

Hover over the tray icon to see what TBAS Sync is doing and when that last
changed, for example "Everything is up to date (10:42)".

It starts automatically when you sign in to Windows. To turn that off, open
Task Manager > Startup apps, select TBAS Sync and click Disable.

Prefer a normal window? Untick "Keep running in the background and start
with Windows" in the app. TBAS Sync then has no tray icon, quits when you
close the window, and no longer starts with Windows. It still checks for and
installs new skins while the window is open.

- When Windows starts it, it stays in the tray. When you start it yourself,
  its window opens.
- Click the tray icon (or right-click > "Open TBAS Sync"), or start TBAS
  Sync again, to open the window.
- Closing the window only hides it; TBAS Sync keeps running in the tray,
  and a notification tells you so.
- Right-click > "Check for skin updates now" to check immediately.
- Right-click > "Quit" to stop it completely.
- After TBAS Sync updates itself, it shows what changed, once.


THE HANGAR
----------
The window shows every skin of the TBAS collection as a picture card,
grouped by aircraft, with the name of whoever made it. Click a card to open
that skin on the HSD website.

Skins that arrived on your PC in the last 14 days are listed first, under
"Latest arrivals", and carry a NEW tag. Updated skins count too. Right
after a first install nothing is marked, because everything is new.

The pictures are downloaded the first time you open the window (about
12 MB) and then kept on your PC. Nothing is downloaded for the hangar while
TBAS Sync is hidden in the tray.


REMOVING OLD TBAS SKINS
-----------------------
When a skin is taken out of the TBAS collection, TBAS Sync shows a "Remove
old TBAS skins" button. It lists the skins and asks before deleting them.
It only ever offers skins that TBAS Sync installed itself: your own skins
and other squads' skins are never touched. Skins that left the collection
before you had this version of TBAS Sync are not detected.


WHERE YOUR SETTINGS ARE STORED
------------------------------
TBAS Sync keeps its configuration, log file, and caches in:

    %APPDATA%\TBASSync\

Paste that path into the File Explorer address bar to open it. Inside
you'll find:

    TBASSync-config.json   - your configuration
    TBASSync.log           - log file (attach this when reporting issues)
    TBASSync.log.1         - the previous log file (each one stops at 1 MB)
    TBASSync-installed.json - which skins TBAS Sync installed (used to
                             offer removing old TBAS skins)
    TBASSync-hashes.json   - cached file checksums (safe to delete)
    previews\              - small skin pictures for the hangar (safe to
                             delete)
    TBASSync-device.json   - anonymous usage ID (see USAGE STATISTICS)
    temp\                  - scratch downloads (safe to delete when closed)


UPGRADING FROM AN OLDER VERSION
-------------------------------
TBAS Sync updates itself when a new version comes out, whether you used
the installer or the zip. To update by hand, run the newest
TBASSync-Setup.exe (it installs over the old version), or with the zip
copy, replace your old TBASSync.exe with the new one.

Moving from the zip to the installer: run TBASSync-Setup.exe, then delete
your old TBASSync.exe. Setup closes a running TBAS Sync itself (after you
click Install), wherever its exe is. Your settings in
%APPDATA%\TBASSync\ are kept, and the installed copy takes over starting
with Windows the first time it runs.

Coming from a much older zip version: the first time you run the new
build, any configuration file sitting next to the old exe will be moved
into %APPDATA%\TBASSync\ automatically — you don't have to redo your
first-launch setup.


UNINSTALLING
------------
Installed with TBASSync-Setup.exe:
1. Open Windows Settings > Apps > Installed apps, find TBAS Sync, click
   the ... button and choose Uninstall. This closes TBAS Sync if it's
   running, then removes the app, its shortcuts and its "start with
   Windows" entry.
2. Your settings are kept. Delete the %APPDATA%\TBASSync\ folder too if
   you want to remove your settings, log, and caches.

Zip copy:
1. Quit TBAS Sync from its tray icon.
2. Remove it from Windows startup by running this in a Command Prompt:
       reg delete HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v TBASSync /f
3. Delete TBASSync.exe from wherever you put it.
4. Delete the %APPDATA%\TBASSync\ folder to remove your settings, log, and
   caches.


CONFIGURATION OPTIONS
---------------------
These live in TBASSync-config.json. You can edit most of them through the
app's parameters panel, or directly in the JSON file.

  IL2GBGameDirectory
      Path to your IL-2 install folder (the one that contains bin\game\).

  cockpitNotesMode
      Which cockpit notes / photos to install. The app's "Cockpit
      notes/photos" list offers every cockpit notes pack on HSD; pick one
      there. In the file it is "noSync" (keep whatever is installed) or the
      number of the HSD pack. Names saved by older versions still work:
        "originalPhotos"     HSD pack 4, the game's original photos
        "officialNumbers"    HSD pack 2, notes from IL-2 specifications
                             (by C6_lefuneste)
        "technochatNumbers"  HSD pack 3, notes from technochat measurements
                             (by C6_lefuneste)
        "MetalheadNumbers"   HSD pack 1, notes from Metalhead measurements
      If the chosen pack is offline, the app shows it as "Unavailable: ..."
      and skips cockpit photos until it is back.
      The line under the list describes the selected pack, and the
      "Preview" button shows its note for each aircraft.

  applyCensorship
      true/false. When true, skins that contain restricted symbols (such as
      swastikas) are replaced with neutral markings. Required in some
      countries. Controlled in the app by the "Restricted symbols" setting
      (Hide / Show originals).

  trayMode
      true/false (default true). When true, TBAS Sync runs in the system
      tray and starts with Windows. When false, it is a normal window that
      quits when closed, and it no longer starts with Windows. Controlled in
      the app by the "Keep running in the background and start with Windows"
      checkbox.


USAGE STATISTICS
----------------
To count how many people use TBAS Sync, the app sends a small anonymous
message when it starts and once a day while it runs. It contains only:

    - a random ID created on first launch (not linked to your PC, Windows
      account, Steam or HSD account)
    - the TBAS Sync version number
    - the date TBAS Sync was first started on this PC

Your IP address is not stored. To turn this off, open
%APPDATA%\TBASSync\TBASSync-device.json and change "usageTracking" to false.


TROUBLESHOOTING
---------------
- "The app didn't open / nothing happens"
    If you use the zip, make sure you extracted it first — see
    INSTALLATION. Or install with TBASSync-Setup.exe instead.

- "Windows protected your PC"
    TBAS Sync isn't code-signed. Click "More info", then "Run anyway".

- "It crashed"
    Open %APPDATA%\TBASSync\TBASSync.log — the last few lines usually say
    why. Include that file when you report the issue.

- "It's pointing at the wrong IL-2 install"
    Either open the parameters panel in the app and fix the path, or edit
    "IL2GBGameDirectory" in TBASSync-config.json, or delete the config file
    entirely to re-run first-launch detection.

- "I can't see my cockpit photos in-game"
    In the mission briefing, open Plane Settings, go to the photo tab and
    choose "Photo". The preview on that screen always shows the game's
    default photo — the synced one only appears in the cockpit once you're
    flying.

- "Not enough disk space"
    The skins to install need more room than is free on the drive that
    holds IL-2. Free up some space, then press "Update Now".

- "I want to start over"
    Quit the app from the tray icon, delete %APPDATA%\TBASSync\, and relaunch.
    If you turned tray mode off, close its window instead of using the tray.

- "It says TBAS Sync is already running"
    It is in the system tray. Click its tray icon to open the window. If the
    icon is hidden, click the ^ arrow next to the clock. If you turned tray
    mode off, look for its window on the taskbar instead.


CREDITS
-------
Authors: IRRE_Fizz, Haluter

TBAS Sync is a fork of the ISS program, adapted for HSD v2:
  https://github.com/RaphED/IL2GB-inter-squadrons-skins-synchronizer
