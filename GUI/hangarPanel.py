import queue
import threading
import time
import tkinter as tk
from datetime import date
from tkinter import ttk
from types import SimpleNamespace
import webbrowser

from PIL import ImageTk

import Services.loggingService as loggingService
from GUI.customTheme import TBASDarkTheme
from GUI.previewStrip import CARD_W, CARD_H, GAP, KIND_NEW, LOADER_THREADS, load_thumb, render_card

PAD = 14
HEADING_H = 30
RECENT_DAYS = 14
LATEST_MAX = 8


def _arrived(when, now):
    days = (date.fromtimestamp(now) - date.fromtimestamp(when)).days
    return "today" if days <= 0 else "yesterday" if days == 1 else f"{days} days ago"


def hangarSections(skins, installed_at, now=None):
    """What the hangar shows, top to bottom: [(heading, [(skin, subtitle, is_new)])].
    First the skins that arrived on this PC in the last RECENT_DAYS days, newest first, then every
    skin by aircraft. installed_at: skin id -> when its file was written (absent: not installed).
    HSD has no "added to the collection" date, and a skin's creation date is often years older."""
    now = now or time.time()
    recent = sorted((s for s in skins if now - installed_at.get(s.id(), 0) < RECENT_DAYS * 86400),
                    key=lambda s: installed_at[s.id()], reverse=True)
    if len(recent) > len(skins) / 2:
        recent = []   # a first install: everything just arrived, so nothing stands out
    new_ids = {s.id() for s in recent}

    def by(skin):
        return f"by {skin.creator()}" if skin.creator() else ""

    sections = []
    if recent:
        sections.append(("Latest arrivals", [
            (s, " · ".join(filter(None, [by(s), _arrived(installed_at[s.id()], now)])), True)
            for s in recent[:LATEST_MAX]]))
    by_aircraft = {}
    for skin in skins:
        by_aircraft.setdefault(skin.aircraft_name(), []).append(skin)
    for aircraft in sorted(by_aircraft, key=str.lower):
        cards = sorted(by_aircraft[aircraft], key=lambda s: s.name().lower())
        sections.append((f"{aircraft}  ·  {len(cards)}", [(s, by(s), s.id() in new_ids) for s in cards]))
    return sections


class HangarPanel(tk.Frame):
    """The squadron's skins as a scrollable grid of preview cards; a click opens the skin's HSD page.
    Previews are only fetched while the window is on screen: hidden in the tray it downloads nothing."""

    def __init__(self, master, ui):
        super().__init__(master, bg=TBASDarkTheme.BG_DARKER)
        self.ui = ui
        scrollbar = ttk.Scrollbar(self, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        # height=1: ask for no room, so the status line and the preview strip are placed first
        self.canvas = tk.Canvas(self, bg=TBASDarkTheme.BG_DARKER, highlightthickness=0, height=1,
                                yscrollincrement=(CARD_H + GAP) // 2, yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=self.canvas.yview)

        self._shown = None        # what set_skins last drew
        self._sections = []       # [(heading canvas item, [card])]
        self._cards = {}          # card's canvas item -> card
        self._thumbs = {}         # preview path -> thumbnail
        self._requested = set()   # preview paths asked for or loaded
        self._requests = queue.Queue()

        self.canvas.bind("<Configure>", lambda e: self._layout())
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        self.canvas.tag_bind("card", "<Button-1>", self._on_click)
        self.canvas.tag_bind("card", "<Enter>", lambda e: self.canvas.configure(cursor="hand2"))
        self.canvas.tag_bind("card", "<Leave>", lambda e: self.canvas.configure(cursor=""))
        self.bind("<Map>", lambda e: self.load_previews())
        for _ in range(LOADER_THREADS):
            threading.Thread(target=self._loader, daemon=True).start()

    def set_skins(self, skins, installed_at):
        sections = hangarSections(skins, installed_at)
        shown = [(heading, [(s.id(), s.name(), subtitle, is_new, s.preview_image_path()) for s, subtitle, is_new in cards])
                 for heading, cards in sections]
        if shown == self._shown:
            return   # called after every check: redrawing would flicker and lose the scroll position
        self._shown = shown
        self.canvas.delete("all")
        self._cards.clear()
        self._sections = []
        for heading, cards in sections:
            heading_item = self.canvas.create_text(0, 0, anchor="w", text=heading, fill=TBASDarkTheme.FG_SECONDARY,
                                                   font=("Bahnschrift Light Condensed", 13, "bold"))
            row = []
            for skin, subtitle, is_new in cards:
                card = SimpleNamespace(title=skin.name(), subtitle=subtitle, kind=KIND_NEW if is_new else None,
                                       preview_path=skin.preview_image_path(), page_URL=skin.page_URL(),
                                       item=self.canvas.create_image(0, 0, anchor="nw", tags=("card",)),
                                       photo=None)   # keep a reference or Tk drops the image
                self._draw(card)
                self._cards[card.item] = card
                row.append(card)
            self._sections.append((heading_item, row))
        self._layout()
        self.load_previews()

    def load_previews(self):
        """Fetch the thumbnails still missing, unless the window is hidden in the tray or minimised."""
        if not self.winfo_viewable():
            return
        for card in self._cards.values():
            if card.preview_path and card.preview_path not in self._requested:
                self._requested.add(card.preview_path)
                self._requests.put(card.preview_path)

    def _loader(self):
        # worker thread
        while True:
            preview_path = self._requests.get()
            try:
                thumb = load_thumb(preview_path)
            except Exception as e:
                loggingService.warning(f"Cannot load skin preview {preview_path}: {e}")
                thumb = None
            self.ui.call(self._on_thumb, preview_path, thumb)

    def _on_thumb(self, preview_path, thumb):
        if thumb is None:
            self._requested.discard(preview_path)   # retried the next time the window is opened
            return
        self._thumbs[preview_path] = thumb
        for card in self._cards.values():
            if card.preview_path == preview_path:
                self._draw(card)

    def _draw(self, card):
        card.photo = ImageTk.PhotoImage(render_card(self._thumbs.get(card.preview_path), card.title, card.kind,
                                                    subtitle=card.subtitle))
        self.canvas.itemconfigure(card.item, image=card.photo)

    def _layout(self):
        width = self.canvas.winfo_width()
        columns = max(1, (width - 2 * PAD + GAP) // (CARD_W + GAP))
        y = PAD // 2
        for heading_item, cards in self._sections:
            self.canvas.coords(heading_item, PAD, y + HEADING_H // 2)
            y += HEADING_H
            for i, card in enumerate(cards):
                self.canvas.coords(card.item, PAD + (i % columns) * (CARD_W + GAP), y + (i // columns) * (CARD_H + GAP))
            y += -(-len(cards) // columns) * (CARD_H + GAP)
        self.canvas.configure(scrollregion=(0, 0, width, y + PAD))

    def _on_click(self, _event):
        for item in self.canvas.find_withtag("current"):
            if item in self._cards:
                webbrowser.open(self._cards[item].page_URL)
