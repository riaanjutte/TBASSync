import tkinter as tk

from Services.messageBrocker import MessageBrocker
from GUI.customTheme import TBASDarkTheme

TICK_MS = 50
BAR_HEIGHT = 8

class ProgressBar(tk.Frame):
    """Hand-rolled determinate progress bar.

    Avoids ttk.Progressbar entirely so the visual update is independent of any
    theme/style quirks: it's just two Frames, where the inner one's width is
    a fraction of the outer one's. Worker threads write `_target` and `_success`
    (atomic in CPython); the Tk main thread polls them via `_tick` and updates
    the widget.
    """

    def __init__(self, root):
        super().__init__(
            root,
            bg=TBASDarkTheme.BG_LIGHT,
            height=BAR_HEIGHT,
            highlightthickness=0,
            bd=0,
        )
        self.pack_propagate(False)

        # The fill is placed (not packed) so we can size it precisely as a
        # fraction of the trough's actual rendered width.
        self._fill = tk.Frame(self, bg=TBASDarkTheme.ACCENT_PRIMARY, bd=0, highlightthickness=0)
        self._fill.place(x=0, y=0, relheight=1.0, width=0)

        self._target = 0.0
        self._success = False
        self._displayed_success = False
        MessageBrocker.registerProgressHook(self._set_target)
        MessageBrocker.registerProgressSuccessHook(self._set_success)

        self.after(TICK_MS, self._tick)

    def _set_target(self, progress: float):
        self._target = max(0.0, min(1.0, progress))
        self._success = False

    def _set_success(self):
        self._target = 1.0
        self._success = True

    def _tick(self):
        if self._success != self._displayed_success:
            color = TBASDarkTheme.SUCCESS if self._success else TBASDarkTheme.ACCENT_PRIMARY
            self._fill.configure(bg=color)
            self._displayed_success = self._success

        # Recompute every tick — cheap, and naturally tracks window resizes.
        trough_width = self.winfo_width()
        if trough_width > 0:
            self._fill.place_configure(width=int(trough_width * self._target))

        self.after(TICK_MS, self._tick)
