"""In the real window: the line about the selected cockpit notes pack, the Preview button and the
pack preview window. HSD is stubbed; any real network call fails the test.
Usage: python tests/test_cockpit_preview.py"""
import io
import tkinter as tk

import requests
from PIL import Image

import harness
from harness import check, mainGUI
import Services.remoteService as remoteService

requests.get = lambda *a, **kw: (_ for _ in ()).throw(AssertionError("the test used the network"))

PACKS = [{"id": 5, "title": "FTC Cockpit Notes", "description": " Engine settings and\nbreak altitudes. ",
          "creator": "Nerfection", "notes_count": 3},
         {"id": 4, "title": "IL2 original game photos", "description": "", "creator": "Fizz", "notes_count": 108}]


def note(code, name, md5):
    return {"game_asset": {"code_name": code, "display_name": name}, "MD5": md5,
            "path": f"{code}?md5={md5}", "thumbnail_path": f"{code}?md5={md5}&thumbnail=true"}


NOTES = [note("SpitfireMkVb", "Spitfire Mk.Vb", "AAA"), note("Bf109F4", "Bf 109 F-4", "bbb"),
         note("Bf109F2", "Bf 109 F-2", "bbb"), note("SpitfireMkVb", "Spitfire Mk.Vb", "AAA"),
         note("Yak1s69", "Yak-1 ser.69", "ccc")]   # its thumbnail fails to download
buffer = io.BytesIO()
Image.new("RGB", (70, 100), "red").save(buffer, "WEBP")   # HSD serves WebP thumbnails
detail_calls, downloads = [], []


def fake_pack(pack_id):
    detail_calls.append(pack_id)
    if pack_id == 4:
        raise requests.ConnectionError("HSD is down")
    return {"id": pack_id, "notes": NOTES}


def fake_thumbnail(path):
    downloads.append(path)
    if "ccc" in path:
        raise requests.HTTPError("404")
    return buffer.getvalue()


remoteService.getCockpitNotesPack = fake_pack
remoteService.downloadCockpitNoteThumbnail = fake_thumbnail

harness.write_config(trayMode=True, cockpitNotesMode=5)
root = tk.Tk()
gui = mainGUI.MainGUI(root, check_for_update=False)
root.geometry("+700+300")
root.deiconify()
panel = gui.parametersPanel
dropdown = panel.cokpitNote_dropdown
OFF = "No synchronization, keep current images"


def info():
    root.update_idletasks()
    return panel.cockpit_pack_info.cget("text")


def preview_enabled():
    return str(panel.cockpit_preview_btn.cget("state")) == "normal"


def pick(label):
    dropdown.set(label)
    panel.on_cokpitNote_dropdown_change(None)


def pack_dialogs(title="FTC Cockpit Notes"):
    return [w for w in root.winfo_children() if isinstance(w, tk.Toplevel) and w.title() == title]


def labels(widget):
    found = []
    for child in widget.winfo_children():
        if isinstance(child, tk.Label):
            found.append(child)
        found += labels(child)
    return found


def thumbnail_widths(dialog):
    # the stub thumbnail is 70 px wide, the placeholder 126
    return [int(root.tk.call("image", "width", label.cget("image"))) for label in labels(dialog) if str(label.cget("image"))]


def line_states():
    panel.set_cockpit_packs(None)
    check("while the packs load: empty line", info() == "")
    check("while the packs load: Preview disabled", not preview_enabled())

    panel.set_cockpit_packs(PACKS)
    check("selected pack: description, then author and aircraft count",
          info() == "Engine settings and break altitudes. — by Nerfection · 3 aircraft")
    check("selected pack: Preview enabled", preview_enabled())
    check("selected pack: the line takes its row", panel.cockpit_pack_info.winfo_manager() == "grid")

    pick("IL2 original game photos")
    check("pack without description: author and aircraft count only", info() == "By Fizz · 108 aircraft")

    long_packs = [dict(PACKS[0], description="Very long description. " * 60)] + PACKS[1:]
    pick("FTC Cockpit Notes")
    panel.set_cockpit_packs(long_packs)
    text = info()
    width = panel.cockpit_pack_info.winfo_width()
    check("long description: shortened to one line, author still shown",
          "..." in text and text.endswith("— by Nerfection · 3 aircraft")
          and panel._cockpit_info_font.measure(text) <= width)
    panel.set_cockpit_packs(PACKS)

    pick(OFF)
    check("No synchronization: empty line", info() == "")
    check("No synchronization: Preview disabled", not preview_enabled())
    check("No synchronization: the empty line takes no room", not panel.cockpit_pack_info.winfo_manager())

    harness.write_config(trayMode=True, cockpitNotesMode=7)
    panel.set_cockpit_packs(PACKS)
    check("unavailable pack: still listed as Unavailable", dropdown.get() == "Unavailable: Cockpit notes pack #7")
    check("unavailable pack: empty line", info() == "")
    check("unavailable pack: Preview disabled", not preview_enabled())
    panel.lock_actions()
    panel.unlock_actions()
    check("after a sync: Preview still disabled for an unavailable pack", not preview_enabled())
    panel.preview_cockpit_pack()
    check("unavailable pack: no preview window, nothing fetched", not pack_dialogs() and not detail_calls)

    pick("FTC Cockpit Notes")
    panel.lock_actions()
    check("during a sync: dropdown locked, Preview still usable",
          str(dropdown.cget("state")) == "disabled" and preview_enabled())
    panel.unlock_actions()
    check("after a sync: dropdown unlocked", str(dropdown.cget("state")) == "readonly")
    panel.cockpit_preview_btn.invoke()


def dialog_filled():
    dialogs = pack_dialogs()
    check("Preview opens one window", len(dialogs) == 1)
    texts = [label.cget("text") for label in labels(dialogs[0])]
    check("window shows title, author and description",
          "FTC Cockpit Notes" in texts and "by Nerfection · 3 aircraft" in texts
          and "Engine settings and break altitudes." in texts)
    aircraft = [t for t in texts if t in ("Spitfire Mk.Vb", "Bf 109 F-4", "Bf 109 F-2", "Yak-1 ser.69")]
    check("each aircraft listed once, A to Z", aircraft == ["Bf 109 F-2", "Bf 109 F-4", "Spitfire Mk.Vb", "Yak-1 ser.69"])
    check("every aircraft shows its thumbnail; a failed one keeps the grey placeholder",
          thumbnail_widths(dialogs[0]) == [70, 70, 70, 126])
    check("the pack is fetched once, each distinct image downloaded once",
          detail_calls == [5] and sorted(downloads) == ["Bf109F4?md5=bbb&thumbnail=true",
                                                         "SpitfireMkVb?md5=AAA&thumbnail=true",
                                                         "Yak1s69?md5=ccc&thumbnail=true"])
    before = info()
    panel.set_cockpit_packs(PACKS)   # the 10-minute reload of the pack list
    panel.set_cockpit_packs(PACKS)
    check("reloading the same packs: nothing downloaded again, window kept, line unchanged",
          len(downloads) == 3 and detail_calls == [5] and pack_dialogs() == dialogs and info() == before)
    dialogs[0].destroy()
    panel.cockpit_preview_btn.invoke()


def dialog_reopened():
    dialogs = pack_dialogs()
    check("reopening the window: thumbnails shown without downloading them again (the failed one is retried)",
          len(downloads) == 4 and downloads[-1] == "Yak1s69?md5=ccc&thumbnail=true"
          and thumbnail_widths(dialogs[0]) == [70, 70, 70, 126])
    dialogs[0].destroy()
    pick("IL2 original game photos")
    panel.cockpit_preview_btn.invoke()


def dialog_hsd_down():
    texts = [label.cget("text") for label in labels(pack_dialogs("IL2 original game photos")[0])]
    check("HSD unreachable: the window says so", "Could not load the notes from HSD. Try again later." in texts)
    gui.quit_app()


harness.run_steps(root, [line_states, dialog_filled, dialog_reopened, dialog_hsd_down])
root.mainloop()
harness.finish()
