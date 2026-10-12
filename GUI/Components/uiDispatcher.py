import queue
import tkinter as tk

import Services.loggingService as loggingService


class UiDispatcher:
    """Runs callables on the Tk thread.

    Tkinter is not thread-safe: worker threads must never touch widgets, nor call
    `root.after` themselves. They call `ui.call(fn, *args)` instead, which only
    puts the call on a queue; the Tk thread drains that queue every `poll_ms`.
    Calls queued after the window has been destroyed are simply never run.
    """

    def __init__(self, root: tk.Misc, poll_ms: int = 20):
        self._root = root
        self._poll_ms = poll_ms
        self._queue = queue.Queue()
        self._root.after(self._poll_ms, self._drain)

    def call(self, fn, *args):
        """Safe from any thread: run fn(*args) on the Tk thread as soon as possible."""
        self._queue.put((fn, args))

    def _drain(self):
        while True:
            try:
                fn, args = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                fn(*args)
            except Exception as e:
                loggingService.error(e)
        try:
            self._root.after(self._poll_ms, self._drain)
        except tk.TclError:
            pass  # window destroyed
