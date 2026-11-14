import io
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk

from PIL import Image, ImageTk

import Services.loggingService as loggingService
import Services.remoteService as remoteService
from GUI.customTheme import TBASDarkTheme

THUMB_W, THUMB_H = 126, 180   # HSD's note thumbnails are portrait, about 717x1024
CELL_W = THUMB_W + 12
FONT = "Bahnschrift Light Condensed"
_thumbnails = {}   # md5 -> resized image, kept while the app runs so reopening a pack downloads nothing


def packCredit(pack):
    """"by <author> · <n> aircraft" for a pack from remoteService.getCockpitNotesPacks."""
    return f"by {pack.get('creator') or 'unknown author'} · {pack.get('notes_count', 0)} aircraft"


def showCockpitPack(root, pack, ui):
    """A window showing a cockpit notes pack: title, author, description and a thumbnail per aircraft.
    The notes and thumbnails load on worker threads; ui is the app's UiDispatcher."""
    dialog = tk.Toplevel(root, bg=TBASDarkTheme.BG_DARK)
    dialog.title(pack["title"])
    dialog.transient(root)
    dialog.geometry("760x560")
    dialog.minsize(420, 320)
    closed = threading.Event()
    dialog.bind("<Destroy>", lambda e: closed.set() if e.widget is dialog else None)

    buttons = ttk.Frame(dialog, padding=(16, 0, 16, 16))
    buttons.pack(side="bottom", fill="x")
    close = ttk.Button(buttons, text="Close", style="Accent.TButton", command=dialog.destroy)
    close.pack(side="right")
    link = tk.Label(buttons, text="Open this pack on hsd-online.net", cursor="hand2",
                    fg=TBASDarkTheme.ACCENT_PRIMARY, font=(FONT, 12, "underline"))
    link.pack(side="left")
    link.bind("<Button-1>", lambda e: webbrowser.open(remoteService.cockpit_notes_pack_page_URL.replace("[pack_id]", str(pack["id"]))))

    header = tk.Frame(dialog)
    header.pack(fill="x", padx=16, pady=(12, 8))
    tk.Label(header, text=pack["title"], fg=TBASDarkTheme.ACCENT_PRIMARY, font=(FONT, 18, "bold"), anchor="w").pack(fill="x")
    tk.Label(header, text=packCredit(pack), fg=TBASDarkTheme.FG_SECONDARY, font=(FONT, 12), anchor="w").pack(fill="x")
    description = " ".join((pack.get("description") or "").split())
    if description:
        about = tk.Label(header, text=description, font=(FONT, 12), anchor="w", justify="left")
        about.pack(fill="x", pady=(4, 0))
        about.bind("<Configure>", lambda e: about.configure(wraplength=e.width))

    frame = tk.Frame(dialog)
    frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))
    scrollbar = ttk.Scrollbar(frame, orient="vertical")
    scrollbar.pack(side="right", fill="y")
    canvas = tk.Canvas(frame, bg=TBASDarkTheme.BG_DARK, highlightthickness=0, yscrollincrement=60, yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.configure(command=canvas.yview)
    grid = tk.Frame(canvas)
    canvas.create_window(0, 0, window=grid, anchor="nw")
    grid.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    dialog.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
    status = tk.Label(grid, text="Loading the notes from HSD...", fg=TBASDarkTheme.FG_SECONDARY, font=(FONT, 12))
    status.grid(row=0, column=0, sticky="w")

    placeholder = tk.PhotoImage(master=dialog, width=THUMB_W, height=THUMB_H)
    photos = {}    # md5 -> PhotoImage
    dialog.photos = (placeholder, photos)   # Tk drops an image once Python no longer references it
    images = {}    # md5 -> the labels showing it (several aircraft can share one note)
    cells = []
    columns = [0]

    def layout(event=None):
        count = max(1, canvas.winfo_width() // CELL_W)
        if count != columns[0]:
            columns[0] = count
            for i, cell in enumerate(cells):
                cell.grid(row=i // count, column=i % count, padx=6, pady=6, sticky="n")

    def show_notes(notes):
        if closed.is_set():
            return
        status.destroy()
        for note in notes:
            cell = tk.Frame(grid)
            image = tk.Label(cell, image=placeholder, width=THUMB_W, height=THUMB_H, bg=TBASDarkTheme.BG_LIGHT)
            image.pack()
            tk.Label(cell, text=note["game_asset"]["display_name"], wraplength=THUMB_W, font=(FONT, 12)).pack()
            images.setdefault(note["MD5"].lower(), []).append(image)
            cells.append(cell)
        canvas.bind("<Configure>", layout)
        layout()
        for md5 in images:
            if md5 in _thumbnails:
                show_thumbnail(md5)

    def show_thumbnail(md5):
        if closed.is_set():
            return
        photos[md5] = ImageTk.PhotoImage(_thumbnails[md5], master=dialog)
        for image in images[md5]:
            image.configure(image=photos[md5])

    def show_error():
        if not closed.is_set():
            status.configure(text="Could not load the notes from HSD. Try again later.")

    def load_thumbnails(todo):
        # worker thread: only PIL here, the PhotoImage is made on the Tk thread
        while not closed.is_set():
            try:
                md5, path = todo.get_nowait()
            except queue.Empty:
                return
            try:
                image = Image.open(io.BytesIO(remoteService.downloadCockpitNoteThumbnail(path))).convert("RGB")
                image.thumbnail((THUMB_W, THUMB_H), Image.Resampling.LANCZOS)
            except Exception as e:
                loggingService.warning(f"Cannot load the cockpit note thumbnail {path}: {e}")
                continue
            _thumbnails[md5] = image
            ui.call(show_thumbnail, md5)

    def load():
        try:
            notes = remoteService.getCockpitNotesPack(pack["id"])["notes"]
        except Exception as e:
            loggingService.warning(f"Cannot load cockpit notes pack {pack['id']}: {e}")
            ui.call(show_error)
            return
        notes = sorted({note["game_asset"]["code_name"]: note for note in notes}.values(),
                       key=lambda note: note["game_asset"]["display_name"].lower())
        ui.call(show_notes, notes)
        todo = queue.SimpleQueue()
        for md5, path in {note["MD5"].lower(): note.get("thumbnail_path") for note in notes}.items():
            if path and md5 not in _thumbnails:
                todo.put((md5, path))
        for _ in range(4):   # daemon threads: quitting the app never waits for a slow download
            threading.Thread(target=load_thumbnails, args=(todo,), daemon=True).start()

    threading.Thread(target=load, daemon=True).start()

    dialog.update_idletasks()
    x = root.winfo_rootx() + (root.winfo_width() - dialog.winfo_width()) // 2
    y = root.winfo_rooty() + (root.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")
    close.focus_set()
    return dialog
