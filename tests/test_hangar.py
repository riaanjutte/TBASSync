"""The hangar (the squadron's skins in the main window) and the notification that names new skins.
Usage: python tests/test_hangar.py"""
import io
import os
import time
import tkinter as tk
import types

from PIL import Image

import harness
from harness import check, mainGUI
import GUI.hangarPanel as hangarPanel
import GUI.previewStrip as previewStrip
from GUI.hangarPanel import hangarSections
from Services.scannerService import ScanResult
from Services.versionManager import currentVersion

DAY = 86400
NOON = time.mktime((2026, 11, 14, 12, 0, 0, 0, 0, -1))


def skin(skin_id, title, aircraft="Bf 109 G-6", creator="Haluter"):
    return types.SimpleNamespace(
        id=lambda: skin_id, name=lambda: title, creator=lambda: creator, aircraft_name=lambda: aircraft,
        game_asset_code=lambda: aircraft.replace(" ", ""), size_in_b=lambda: 1000,
        page_URL=lambda: f"https://hsd-online.net/skins/{skin_id}", preview_image_path=lambda: f"{skin_id}?md5=abc",
        dds_files=lambda: [types.SimpleNamespace(destination_name=f"{title}.dds")])


A, B = skin(1, "TBAS Alpha"), skin(2, "TBAS Bravo", creator="MayheM-1")
C, D, E = skin(3, "TBAS Charlie", "P-51D-15"), skin(4, "TBAS Delta", "P-51D-15", creator=""), skin(5, "TBAS Echo", "P-51D-15")
SKINS = [E, D, C, B, A]

# ── what the hangar lists
times = {1: NOON - 40 * DAY, 2: NOON - 3 * DAY, 3: NOON - 2 * 3600, 4: NOON - 20 * DAY}   # 5 is not installed
sections = hangarSections(SKINS, times, NOON)
check("latest arrivals first, then every aircraft A to Z with its count",
      [heading for heading, _ in sections] == ["Latest arrivals", "Bf 109 G-6  ·  2", "P-51D-15  ·  3"])
check("latest arrivals: newest first, with the author and when it arrived",
      [(s.id(), subtitle) for s, subtitle, _ in sections[0][1]]
      == [(3, "by Haluter · today"), (2, "by MayheM-1 · 3 days ago")])
check("by aircraft: A to Z, author under the title, NEW on recent arrivals",
      [(s.id(), subtitle, new) for s, subtitle, new in sections[2][1]]
      == [(3, "by Haluter", True), (4, "", False), (5, "by Haluter", False)])
check("arrived the day before: 'yesterday'",
      hangarSections(SKINS, {2: NOON - DAY}, NOON)[0][1][0][1] == "by MayheM-1 · yesterday")
first_install = hangarSections(SKINS, {s.id(): NOON - 60 for s in SKINS}, NOON)
check("a first install (everything just arrived): no latest section and nothing marked NEW",
      [heading for heading, _ in first_install] == ["Bf 109 G-6  ·  2", "P-51D-15  ·  3"]
      and not any(new for _, cards in first_install for _, _, new in cards))
check("nothing arrived lately: no latest section",
      hangarSections(SKINS, {1: NOON - 40 * DAY}, NOON)[0][0] == "Bf 109 G-6  ·  2")
many = [skin(100 + i, f"TBAS {i:02}") for i in range(30)]
check("at most 8 latest arrivals",
      len(hangarSections(many, {100 + i: NOON - i * 3600 for i in range(12)}, NOON)[0][1]) == 8)

# ── the notification
check("one new skin: named with its author", mainGUI.arrivalMessage([B], []) == "New skin: TBAS Bravo by MayheM-1.")
check("a new skin without an author", mainGUI.arrivalMessage([D], []) == "New skin: TBAS Delta.")
check("several new skins: the first two are named",
      mainGUI.arrivalMessage([A, B, C, D], []) == "4 new skins: TBAS Alpha, TBAS Bravo and 2 more.")
check("updates only", mainGUI.arrivalMessage([], [A]) == "1 skin updated: TBAS Alpha.")
check("new and updated",
      mainGUI.arrivalMessage([A, B], [C, D, E]) == "2 new skins: TBAS Alpha, TBAS Bravo. 3 skins updated: TBAS Charlie, TBAS Delta and 1 more.")

# ── in the real window
downloads, opened = [], []


def fake_preview(preview_path):
    downloads.append(preview_path)
    buffer = io.BytesIO()
    Image.new("RGB", (960, 540), (40, 90, 140)).save(buffer, "JPEG")
    return buffer.getvalue()


previewStrip.downloadSkinPreview = fake_preview
hangarPanel.webbrowser.open = opened.append
mainGUI.SynchronizerService.updateAll = lambda scan_result: (1, 1, 0, 0)   # "installs" one skin


def install(skin_, age_days):
    folder = os.path.join(harness.IL2, "data", "graphics", "skins", skin_.game_asset_code())
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, skin_.dds_files()[0].destination_name)
    open(path, "wb").write(b"dds")
    when = time.time() - age_days * DAY
    os.utime(path, (when, when))


def scan_with(skins, missing=()):
    result = ScanResult()
    result.subscribedSkins = list(skins)
    result.missingSkins = list(missing)
    return result


def launch(started_at_login, steps):
    harness.write_config(trayMode=True, lastSeenVersion=currentVersion)
    root = tk.Tk()
    gui = mainGUI.MainGUI(root, check_for_update=False, started_at_login=started_at_login)
    harness.run_steps(root, [lambda s=s: s(root, gui) for s in steps] + [gui.quit_app], delay_ms=900)
    root.mainloop()


def cards(gui):
    return gui.hangar.canvas.find_withtag("card")


def collection_known(root, gui):
    for skin_, age in ((A, 40), (B, 3), (C, 0), (D, 20)):
        install(skin_, age)
    check("before the collection is known: no hangar", not gui.hangar.winfo_ismapped())
    gui._on_scan_finished(scan_with(SKINS), False)
    root.update_idletasks()
    check("collection known: the hangar is shown", gui.hangar.winfo_ismapped())
    check("the status is a compact line above it",
          not gui.statusPanel.icon_label.winfo_manager() and gui._status_container.winfo_y() < gui.hangar.winfo_y()
          and gui._status_container.winfo_height() < 90)
    check("one card per skin, plus the two latest arrivals", len(cards(gui)) == 5 + 2)


def previews_and_click(root, gui):
    check("each preview is downloaded once", sorted(downloads) == sorted(s.preview_image_path() for s in SKINS))
    check("thumbnails are kept on disk", len(os.listdir(os.path.join(harness.SANDBOX, "previews"))) == 5)
    items = gui.hangar.canvas.find_all()
    gui._on_scan_finished(scan_with(SKINS), False)
    check("the next check finds the same skins: nothing is redrawn", gui.hangar.canvas.find_all() == items)
    canvas = gui.hangar.canvas
    x, y = canvas.coords(cards(gui)[0])
    canvas.event_generate("<Motion>", x=x + 20, y=y + 20)
    canvas.event_generate("<Button-1>", x=x + 20, y=y + 20)
    check("clicking a card opens that skin on HSD", opened == ["https://hsd-online.net/skins/3"])
    root.geometry("970x600")   # too short for all the cards
    root.update()
    canvas.event_generate("<MouseWheel>", x=x + 20, y=y + 20, delta=-120)
    check("the mouse wheel scrolls the hangar", canvas.yview()[0] > 0)


def new_skin_arrives(root, gui):
    foxtrot = skin(6, "TBAS Foxtrot", creator="MayheM-1")
    gui._on_scan_finished(scan_with(SKINS + [foxtrot], missing=[foxtrot]), False)   # starts the sync


def after_sync(root, gui):
    check("the notification names the new skin", harness.notifications[-1] == "New skin: TBAS Foxtrot by MayheM-1.")
    check("the preview strip sits between the status line and the hangar",
          gui._status_container.winfo_y() < gui.previewStrip.winfo_y() < gui.hangar.winfo_y())
    check("the hangar gained the new skin", len(cards(gui)) == 6 + 2)
    gui._on_scan_finished(None, True)
    root.update_idletasks()
    check("a failed check keeps the hangar", gui.hangar.winfo_ismapped())
    gui._on_scan_finished(None, False)
    root.update_idletasks()
    check("no IL-2 folder: the hangar is hidden and the status takes the room again",
          not gui.hangar.winfo_ismapped() and gui.statusPanel.icon_label.winfo_manager() == "pack")


launch(False, [collection_known, previews_and_click, new_skin_arrives, after_sync])

# ── hidden in the tray: nothing is downloaded until the window is opened
NEW = [skin(10 + i, f"TBAS New {i}") for i in range(3)]


def hidden(root, gui):
    downloads.clear()
    gui._on_scan_finished(scan_with(NEW + [A]), False)


def still_hidden(root, gui):
    check("hidden in the tray: no previews are downloaded", downloads == [])
    gui.show_window()


def opened_from_tray(root, gui):
    check("window opened: the missing previews are downloaded, the ones on disk are not",
          sorted(downloads) == sorted(s.preview_image_path() for s in NEW))


launch(True, [hidden, still_hidden, opened_from_tray])

harness.finish()
