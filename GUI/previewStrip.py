import io
import math
import queue
import threading
import time
import tkinter as tk

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps, ImageTk

import Services.loggingService as loggingService
from Services.remoteService import downloadSkinPreview
from GUI.customTheme import TBASDarkTheme


CARD_W, CARD_H = 176, 99          # 16:9, matches HSD's 960x540 previews
GAP = 10
PAD_X, PAD_Y = 14, 9
STRIP_H = CARD_H + PAD_Y * 2
FADE_W = 36
SETTLE_RATE = 9.0                 # ease-out speed of conveyor slides (higher = snappier)
TICKER_SPEED = 38.0               # px/s of the after-scan ticker
FRAME_MS = 8                      # ask often; motion is time-based, Tk caps the real rate
PUMP_MS = 30                      # how often queued commands are applied on the Tk thread
LOADER_THREADS = 3

KIND_NEW = "new"
KIND_UPDATE = "update"


def _font(size, weight=None):
    try:
        font = ImageFont.truetype("bahnschrift.ttf", size)
    except OSError:
        return ImageFont.load_default(size)
    if weight:
        try:
            font.set_variation_by_name(weight)
        except Exception:
            pass
    return font


def _rgb(hex_color):
    return tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))


def _render_card(thumb, title, kind, dim):
    """Bake thumbnail (or placeholder) + caption + NEW/UPDATE tag + rounded corners into one image.

    Canvas images are rectangular, so the rounded corners are composited onto the
    strip background colour.
    """
    if thumb is None:
        img = Image.new("RGB", (CARD_W, CARD_H), _rgb(TBASDarkTheme.BG_LIGHT))
    else:
        img = thumb
        if dim:
            img = ImageEnhance.Color(img).enhance(0.25)
            img = ImageEnhance.Brightness(img).enhance(0.55)
    img = img.convert("RGBA")

    # bottom gradient keeps the caption readable on bright previews
    gradient = Image.new("RGBA", (CARD_W, 34), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    for y in range(34):
        draw.line([(0, y), (CARD_W, y)], fill=(0, 0, 0, int(215 * (y / 33) ** 1.4)))
    img.alpha_composite(gradient, (0, CARD_H - 34))

    draw = ImageDraw.Draw(img)
    caption_font = _font(13, "SemiBold")
    text = title
    while draw.textlength(text, font=caption_font) > CARD_W - 14 and len(text) > 4:
        text = text[:-2]
    if text != title:
        text = text.rstrip() + "…"
    draw.text((7, CARD_H - 19), text, font=caption_font, fill=(239, 239, 239, 255))

    tag_text, tag_color = ("NEW", TBASDarkTheme.INFO) if kind == KIND_NEW else ("UPDATE", TBASDarkTheme.ACCENT_PRIMARY)
    tag_font = _font(10, "Bold")
    tag_w = draw.textlength(tag_text, font=tag_font)
    draw.rounded_rectangle([6, 6, 6 + tag_w + 10, 6 + 15], radius=3, fill=_rgb(tag_color) + (235,))
    draw.text((11, 7), tag_text, font=tag_font, fill=(255, 255, 255, 255))

    mask = Image.new("L", (CARD_W, CARD_H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, CARD_W - 1, CARD_H - 1], radius=6, fill=255)
    card = Image.new("RGB", (CARD_W, CARD_H), _rgb(TBASDarkTheme.BG_DARKER))
    card.paste(img, (0, 0), mask)
    ImageDraw.Draw(card).rounded_rectangle([0, 0, CARD_W - 1, CARD_H - 1], radius=6,
                                           outline=_rgb(TBASDarkTheme.BORDER))
    return card


class _Card:
    def __init__(self, key, title, kind, preview_path, x, state):
        self.key = key
        self.title = title
        self.kind = kind
        self.preview_path = preview_path
        self.x = float(x)        # current (float) position
        self.drawn_x = int(x)    # last integer position applied to the canvas
        self.target = float(x)
        self.tag = f"card_{id(self)}"
        self.state = state       # "pending" | "downloading" | "done" | "failed"
        self.progress = 0.0
        self.photo = None        # keep a reference or Tk drops the image


class PreviewStrip(tk.Frame):
    """Horizontal strip of skin preview cards that flow right → left.

    Ticker (after a scan): every skin that will be downloaded or updated scrolls
    continuously right → left, looping, when they don't all fit.

    Conveyor (during sync): each skin's card slides in from the right edge when its
    download starts, shows a progress bar, then a ✓ (or ✗). Once the row is wider
    than the strip the whole row eases left and the oldest cards leave the frame.

    The public methods are safe to call from any thread: they only queue commands,
    which are applied on the Tk thread.
    """

    def __init__(self, master):
        super().__init__(master, bg=TBASDarkTheme.BG_DARKER, height=STRIP_H)
        self.pack_propagate(False)
        self.canvas = tk.Canvas(self, bg=TBASDarkTheme.BG_DARKER, highlightthickness=0, height=STRIP_H)
        self.canvas.pack(fill="both", expand=True)

        self._commands = queue.Queue()
        self._preview_requests = queue.Queue()
        self._thumbs: dict[str, Image.Image] = {}        # preview path -> thumbnail (Tk thread only)
        self._requested: set[str] = set()                # preview paths in flight or loaded
        self._ticker_waiting: dict[str, list] = {}       # preview path -> ticker items awaiting it

        self.cards: list[_Card] = []
        self.by_key: dict = {}
        self.mode = None                                 # None | "ticker" | "conveyor"
        self._anim_id = None
        self._last_t = None
        self._fade_l = self._fade_r = None

        self.canvas.bind("<Configure>", self._on_configure)
        for _ in range(LOADER_THREADS):
            threading.Thread(target=self._preview_loader, daemon=True).start()
        self.after(PUMP_MS, self._pump)

    # ── thread-safe API ─────────────────────────────────────────────────────
    def show_pending(self, items):
        """Ticker of skins to download/update. items: [(key, title, kind, preview_path), ...]"""
        self._commands.put(("ticker", list(items)))

    def start_sync(self):
        self._commands.put(("conveyor",))

    def skin_started(self, key, title, kind, preview_path):
        self._commands.put(("started", key, title, kind, preview_path))

    def skin_progress(self, key, fraction):
        self._commands.put(("progress", key, fraction))

    def skin_done(self, key, ok):
        self._commands.put(("done", key, ok))

    def clear(self):
        self._commands.put(("clear",))

    # ── command pump (Tk thread) ────────────────────────────────────────────
    def _pump(self):
        while True:
            try:
                command = self._commands.get_nowait()
            except queue.Empty:
                break
            try:
                getattr(self, f"_cmd_{command[0]}")(*command[1:])
            except Exception as e:
                loggingService.error(e)
        self.after(PUMP_MS, self._pump)

    def _cmd_clear(self):
        self.canvas.delete("card")
        self.cards.clear()
        self.by_key.clear()
        self._ticker_waiting.clear()
        self.mode = None

    def _cmd_ticker(self, items):
        self._cmd_clear()
        self.mode = "ticker"
        for key, title, kind, preview_path in items:
            if preview_path and preview_path not in self._thumbs:
                # add the card once its preview has arrived, so the ticker doesn't flash placeholders
                self._ticker_waiting.setdefault(preview_path, []).append((key, title, kind, preview_path))
                self._request_preview(preview_path)
            else:
                self._add_ticker_card(key, title, kind, preview_path)

    def _cmd_conveyor(self):
        self._cmd_clear()
        self.mode = "conveyor"

    def _cmd_started(self, key, title, kind, preview_path):
        if self.mode != "conveyor" or key in self.by_key:
            return
        self._request_preview(preview_path)
        card = _Card(key, title, kind, preview_path, self._width() + 8, "downloading")
        self._draw_card(card, progress_bar=True)
        self.cards.append(card)
        self.by_key[key] = card
        self._relayout()
        self._kick()

    def _cmd_progress(self, key, fraction):
        card = self.by_key.get(key)
        if card is None or card.state != "downloading":
            return
        card.progress = max(0.0, min(1.0, fraction))
        x0 = card.drawn_x + 6
        self.canvas.coords(f"{card.tag}_fill", x0, PAD_Y + CARD_H - 6,
                           x0 + (CARD_W - 12) * card.progress, PAD_Y + CARD_H - 3)

    def _cmd_done(self, key, ok):
        card = self.by_key.get(key)
        if card is None:
            return
        card.state = "done" if ok else "failed"
        self.canvas.delete(f"{card.tag}_bar")
        self._refresh_card_image(card)
        color, glyph = (TBASDarkTheme.SUCCESS, "✓") if ok else (TBASDarkTheme.ERROR, "✗")
        bx, by = card.drawn_x + CARD_W - 13, PAD_Y + 13
        self.canvas.create_oval(bx - 9, by - 9, bx + 9, by + 9, fill=color, outline="",
                                tags=("card", card.tag))
        self.canvas.create_text(bx, by, text=glyph, fill="white",
                                font=("Segoe UI Symbol", 9, "bold"), tags=("card", card.tag))
        self.canvas.tag_raise("fade")

    def _cmd_preview(self, preview_path, thumb):
        if thumb is None:
            self._requested.discard(preview_path)   # allow a retry on the next scan
        else:
            self._thumbs[preview_path] = thumb
        for item in self._ticker_waiting.pop(preview_path, []):
            if self.mode == "ticker":
                self._add_ticker_card(*item)
        for card in self.cards:
            if card.preview_path == preview_path:
                self._refresh_card_image(card)

    # ── preview loading (worker threads) ───────────────────────────────────
    def _request_preview(self, preview_path):
        if preview_path and preview_path not in self._requested:
            self._requested.add(preview_path)
            self._preview_requests.put(preview_path)

    def _preview_loader(self):
        while True:
            preview_path = self._preview_requests.get()
            thumb = None
            try:
                image = Image.open(io.BytesIO(downloadSkinPreview(preview_path))).convert("RGB")
                thumb = ImageOps.fit(image, (CARD_W, CARD_H), Image.Resampling.LANCZOS)
            except Exception as e:
                loggingService.warning(f"Cannot load skin preview {preview_path}: {e}")
            self._commands.put(("preview", preview_path, thumb))

    # ── drawing ─────────────────────────────────────────────────────────────
    def _width(self):
        width = self.canvas.winfo_width()
        return width if width > 1 else max(self.master.winfo_width(), 1)

    def _card_image(self, card):
        thumb = self._thumbs.get(card.preview_path)
        dim = card.state in ("downloading", "failed")
        return ImageTk.PhotoImage(_render_card(thumb, card.title, card.kind, dim))

    def _refresh_card_image(self, card):
        card.photo = self._card_image(card)
        self.canvas.itemconfigure(f"{card.tag}_img", image=card.photo)

    def _draw_card(self, card, progress_bar):
        card.photo = self._card_image(card)
        x = card.drawn_x
        self.canvas.create_image(x, PAD_Y, anchor="nw", image=card.photo,
                                 tags=("card", card.tag, f"{card.tag}_img"))
        if progress_bar:
            y0, y1 = PAD_Y + CARD_H - 6, PAD_Y + CARD_H - 3
            self.canvas.create_rectangle(x + 6, y0, x + CARD_W - 6, y1, fill="#3a3a3a", outline="",
                                         tags=("card", card.tag, f"{card.tag}_bar"))
            self.canvas.create_rectangle(x + 6, y0, x + 6, y1, fill=TBASDarkTheme.ACCENT_PRIMARY, outline="",
                                         tags=("card", card.tag, f"{card.tag}_bar", f"{card.tag}_fill"))
        self.canvas.tag_raise("fade")

    def _add_ticker_card(self, key, title, kind, preview_path):
        if key in self.by_key:
            return
        step = CARD_W + GAP
        x = PAD_X if not self.cards else max(c.x for c in self.cards) + step
        card = _Card(key, title, kind, preview_path, x, "pending")
        self._draw_card(card, progress_bar=False)
        self.cards.append(card)
        self.by_key[key] = card
        self._kick()

    def _on_configure(self, _event):
        self._build_fades()
        self._relayout()
        self._kick()

    def _build_fades(self):
        background = _rgb(TBASDarkTheme.BG_DARKER)
        gradient = Image.new("RGBA", (FADE_W, STRIP_H))
        draw = ImageDraw.Draw(gradient)
        for x in range(FADE_W):
            draw.line([(x, 0), (x, STRIP_H)], fill=background + (int(255 * (1 - x / (FADE_W - 1)) ** 1.6),))
        self._fade_l = ImageTk.PhotoImage(gradient)
        self._fade_r = ImageTk.PhotoImage(gradient.transpose(Image.Transpose.FLIP_LEFT_RIGHT))
        self.canvas.delete("fade")
        self.canvas.create_image(0, 0, anchor="nw", image=self._fade_l, tags="fade")
        self.canvas.create_image(self._width(), 0, anchor="ne", image=self._fade_r, tags="fade")

    # ── animation ───────────────────────────────────────────────────────────
    def _relayout(self):
        """Conveyor targets: fill from the left; once full, the newest card hugs the right edge."""
        if self.mode != "conveyor" or not self.cards:
            return
        step = CARD_W + GAP
        content = PAD_X * 2 + len(self.cards) * step - GAP
        scroll = max(0, content - self._width())
        for i, card in enumerate(self.cards):
            card.target = PAD_X + i * step - scroll

    def _kick(self):
        if self._anim_id is None:
            self._last_t = time.perf_counter()
            self._anim_id = self.after(FRAME_MS, self._tick)

    def _tick(self):
        now = time.perf_counter()
        dt = min(now - self._last_t, 0.05)
        self._last_t = now
        if self.mode == "ticker":
            busy = self._step_ticker(dt)
        elif self.mode == "conveyor":
            busy = self._step_conveyor(dt)
        else:
            busy = False
        self._anim_id = self.after(FRAME_MS, self._tick) if busy else None

    def _move(self, card, new_x):
        card.x = new_x
        ix = round(new_x)
        if ix != card.drawn_x:
            self.canvas.move(card.tag, ix - card.drawn_x, 0)
            card.drawn_x = ix

    def _step_conveyor(self, dt):
        k = 1.0 - math.exp(-SETTLE_RATE * dt)      # frame-rate independent ease-out
        moving = False
        for card in list(self.cards):
            if abs(card.target - card.x) < 0.4:
                self._move(card, card.target)
            else:
                self._move(card, card.x + (card.target - card.x) * k)
                moving = True
            if card.x + CARD_W < -4 and card.target + CARD_W < 0:   # fully out on the left
                self.canvas.delete(card.tag)
                self.cards.remove(card)
                self.by_key.pop(card.key, None)
        return moving

    def _step_ticker(self, dt):
        if not self.cards:
            return False
        step = CARD_W + GAP
        if PAD_X * 2 + len(self.cards) * step - GAP <= self._width():
            return False                              # everything fits: stay still
        for card in self.cards:
            self._move(card, card.x - TICKER_SPEED * dt)
        rightmost = max(card.x for card in self.cards)
        for card in self.cards:                       # recycle cards that left on the left
            if card.x + CARD_W < 0:
                self._move(card, rightmost + step)
                rightmost = card.x
        return True
