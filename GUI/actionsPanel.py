import tkinter as tk
from tkinter import ttk


class ActionPanel:
    STATE_LOADING    = "loading"
    STATE_SCANNING   = "scanning"
    STATE_UP_TO_DATE = "up_to_date"
    STATE_UPDATES    = "updates_available"
    STATE_SYNCING    = "syncing"

    def __init__(self, root: tk, scanCommand, syncCommand):
        self.root = root
        self._scanCommand = scanCommand
        self._syncCommand = syncCommand

        frame = tk.Frame(root)
        frame.pack(fill="x", padx=10, pady=10)
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=0)

        self.recheckButton = ttk.Button(
            frame,
            text="\u21bb  Re-check",
            command=scanCommand
        )
        self.recheckButton.grid(row=0, column=0, sticky="w")

        self.primaryButton = ttk.Button(
            frame,
            text="Loading\u2026",
            style="Accent.TButton",
            command=self._on_primary_click,
            width=16
        )
        self.primaryButton.grid(row=0, column=2, sticky="e", ipady=10, padx=10)

        self._state = None
        self.set_state(self.STATE_LOADING)

    def _on_primary_click(self):
        if self._state == self.STATE_UPDATES:
            self._syncCommand()

    def set_state(self, state, summary: str = None):
        self._state = state

        if state == self.STATE_LOADING:
            self.primaryButton.configure(text="Loading\u2026", state="disabled", style="")
            self.recheckButton.configure(state="disabled")
        elif state == self.STATE_SCANNING:
            self.primaryButton.configure(text="Checking\u2026", state="disabled", style="")
            self.recheckButton.configure(state="disabled")
        elif state == self.STATE_UP_TO_DATE:
            self.primaryButton.configure(text="\u2713  Up to date", state="disabled", style="")
            self.recheckButton.configure(state="normal")
        elif state == self.STATE_UPDATES:
            label = "Update Now" if not summary else f"Update Now  ({summary})"
            self.primaryButton.configure(text=label, state="normal", style="Accent.TButton")
            self.recheckButton.configure(state="normal")
        elif state == self.STATE_SYNCING:
            self.primaryButton.configure(text="Updating\u2026", state="disabled", style="")
            self.recheckButton.configure(state="disabled")
