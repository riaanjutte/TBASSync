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


WHERE YOUR SETTINGS ARE STORED
------------------------------
TBAS Sync keeps its configuration, log file, and caches in:

    %APPDATA%\TBASSync\

Paste that path into the File Explorer address bar to open it. Inside
you'll find:

    TBASSync-config.json   - your configuration
    TBASSync.log           - log file (attach this when reporting issues)
    TBASSync-hashes.json   - cached file checksums (safe to delete)
    temp\                  - scratch downloads (safe to delete when closed)


UPGRADING FROM AN OLDER VERSION
-------------------------------
Just replace your old TBASSync.exe with the new one. The first time you run
the new build, any configuration file sitting next to the old exe will be
moved into %APPDATA%\TBASSync\ automatically — you don't have to redo your
first-launch setup.


UNINSTALLING
------------
1. Delete TBASSync.exe from wherever you put it.
2. Delete the %APPDATA%\TBASSync\ folder to remove your settings, log, and
   caches.


CONFIGURATION OPTIONS
---------------------
These live in TBASSync-config.json. You can edit them through the app's
parameters panel, or directly in the JSON file.

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

- "I want to start over"
    Close the app, delete %APPDATA%\TBASSync\, and relaunch.


CREDITS
-------
Authors: IRRE_Fizz, Haluter

TBAS Sync is a fork of the ISS program, adapted for HSD v2:
  https://github.com/RaphED/IL2GB-inter-squadrons-skins-synchronizer
