TBAS Sync
=========

TBAS Sync downloads and installs IL-2: Great Battles skin packs from the HSD
website and keeps your local skins folder in sync with your subscribed
collections.


INSTALLATION
------------
1. Extract this zip to a folder of your choice (Desktop, Documents, a
   dedicated "Tools" folder, wherever you like).

   IMPORTANT: do NOT run TBASSync.exe directly from inside the zip. Windows
   will extract it to a throwaway temporary folder, your settings will not
   persist, and the app may not behave correctly.

2. Double-click TBASSync.exe.

3. On first launch the app tries to auto-detect your IL-2 installation. If
   it can't find it, you'll be asked to point it at the folder that contains
   bin\game\Il-2.exe.


RUNNING IN THE SYSTEM TRAY
--------------------------
TBAS Sync runs in the system tray (the icons next to the clock). It checks
for new or updated skins when it starts and every 10 minutes, installs them
without asking, and shows a Windows notification when it's done.

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
- Closing the window only hides it; TBAS Sync keeps running in the tray.
- Right-click > "Check for skin updates now" to check immediately.
- Right-click > "Quit" to stop it completely.


WHERE YOUR SETTINGS ARE STORED
------------------------------
TBAS Sync keeps its configuration, log file, and caches in:

    %APPDATA%\TBASSync\

Paste that path into the File Explorer address bar to open it. Inside
you'll find:

    TBASSync-config.json   - your configuration
    TBASSync.log           - log file (attach this when reporting issues)
    TBASSync-hashes.json   - cached file checksums (safe to delete)
    TBASSync-device.json   - anonymous usage ID (see USAGE STATISTICS)
    temp\                  - scratch downloads (safe to delete when closed)


UPGRADING FROM AN OLDER VERSION
-------------------------------
Just replace your old TBASSync.exe with the new one. The first time you run
the new build, any configuration file sitting next to the old exe will be
moved into %APPDATA%\TBASSync\ automatically — you don't have to redo your
first-launch setup.


UNINSTALLING
------------
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
      Controls the cockpit note / photo images:
        "noSync"             keep whatever is currently installed
        "originalPhotos"     restore the game's original photos
        "officialNumbers"    cockpit notes from IL-2 specifications
                             (by C6_lefuneste)
        "technochatNumbers"  cockpit notes from technochat measurements
                             (by C6_lefuneste)
        "MetalheadNumbers"   cockpit notes from Metalhead measurements

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
    Make sure you extracted the zip first — see INSTALLATION.

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
