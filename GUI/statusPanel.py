import tkinter as tk
from tkinter import ttk

from GUI.customTheme import TBASDarkTheme


class StatusPanel:
    def __init__(self, root):
        self.root = root

        self.frame = tk.Frame(root, bg=TBASDarkTheme.BG_DARKER)
        self.frame.pack(expand=True, fill="both")

        inner = tk.Frame(self.frame, bg=TBASDarkTheme.BG_DARKER)
        inner.place(relx=0.5, rely=0.42, anchor="center")

        self.icon_label = tk.Label(
            inner,
            text="",
            font=("Bahnschrift Light Condensed", 28, "bold"),
            bg=TBASDarkTheme.BG_DARKER,
            fg=TBASDarkTheme.FG_SECONDARY,
        )
        self.icon_label.pack(pady=(0, 3))

        self.title_label = tk.Label(
            inner,
            text="",
            font=("Bahnschrift Light Condensed", 18, "bold"),
            bg=TBASDarkTheme.BG_DARKER,
            fg=TBASDarkTheme.FG_PRIMARY,
        )
        self.title_label.pack(pady=(0, 4))

        self.detail_label = tk.Label(
            inner,
            text="",
            font=("Bahnschrift Light Condensed", 12),
            bg=TBASDarkTheme.BG_DARKER,
            fg=TBASDarkTheme.FG_SECONDARY,
        )
        self.detail_label.pack()

        self.actions_frame = tk.Frame(inner, bg=TBASDarkTheme.BG_DARKER)
        self.actions_frame.pack(pady=(10, 0))

    def _clear_actions(self):
        for child in self.actions_frame.winfo_children():
            child.destroy()

    def _show(self, icon, icon_color, title, title_color, detail=""):
        self._clear_actions()
        self.icon_label.configure(text=icon, fg=icon_color)
        self.title_label.configure(text=title, fg=title_color)
        self.detail_label.configure(text=detail)

    def showLoading(self):
        self._show("\u22ef", TBASDarkTheme.FG_SECONDARY,
                   "Loading collections\u2026",
                   TBASDarkTheme.FG_PRIMARY)

    def showScanning(self):
        self._show("\u22ef", TBASDarkTheme.FG_SECONDARY,
                   "Checking your skins\u2026",
                   TBASDarkTheme.FG_PRIMARY)

    def showUpToDate(self):
        self._show("\u2713", TBASDarkTheme.SUCCESS,
                   "Everything is up to date",
                   TBASDarkTheme.SUCCESS)

    def showUpdatesNeeded(self, skins: int = 0, cockpit: int = 0):
        counts = self._format_counts(skins, cockpit)
        title = f"{counts} need updating" if counts else "Updates available"
        self._show("\u2193", TBASDarkTheme.ACCENT_PRIMARY,
                   title, TBASDarkTheme.ACCENT_PRIMARY,
                   "Press \"Update Now\" to start.")

    def showSyncing(self, skins: int = 0, cockpit: int = 0):
        title = f"Updating {self._format_counts(skins, cockpit)}\u2026" if (skins or cockpit) else "Updating\u2026"
        self._show("\u22ef", TBASDarkTheme.ACCENT_PRIMARY,
                   title, TBASDarkTheme.FG_PRIMARY)

    def showSyncSuccess(self, skins: int = 0, cockpit: int = 0):
        if skins or cockpit:
            title = f"{self._format_counts(skins, cockpit)} updated successfully"
        else:
            title = "Update complete"
        self._show("\u2713", TBASDarkTheme.SUCCESS,
                   title, TBASDarkTheme.SUCCESS)

    @staticmethod
    def _format_counts(skins: int, cockpit: int) -> str:
        parts = []
        if skins > 0:
            parts.append(f"{skins} {'skin' if skins == 1 else 'skins'}")
        if cockpit > 0:
            parts.append(f"{cockpit} cockpit {'photo' if cockpit == 1 else 'photos'}")
        return " and ".join(parts)

    def showSyncPartialFailure(self, skin_failed: int = 0, skin_total: int = 0,
                               cockpit_failed: int = 0, cockpit_total: int = 0):
        parts = []
        if skin_failed > 0:
            noun = "skin" if skin_total == 1 else "skins"
            parts.append(f"{skin_failed} of {skin_total} {noun}")
        if cockpit_failed > 0:
            noun = "cockpit photo" if cockpit_total == 1 else "cockpit photos"
            parts.append(f"{cockpit_failed} of {cockpit_total} {noun}")
        title = f"{' and '.join(parts)} failed to update" if parts else "Update failed"
        self._show("\u2717", TBASDarkTheme.ERROR,
                   title, TBASDarkTheme.ERROR,
                   "See the log file for details.")

    def showError(self, title="Something went wrong", detail="See the log file for details."):
        self._show("\u2717", TBASDarkTheme.ERROR,
                   title, TBASDarkTheme.ERROR, detail)

    def showPrompt(self, title, detail, primary_label, on_primary,
                   secondary_label, on_secondary):
        self._show("?", TBASDarkTheme.ACCENT_PRIMARY,
                   title, TBASDarkTheme.FG_PRIMARY, detail)

        primary_btn = ttk.Button(
            self.actions_frame,
            text=primary_label,
            style="Accent.TButton",
            command=on_primary,
        )
        primary_btn.pack(side="left", padx=6)

        secondary_btn = ttk.Button(
            self.actions_frame,
            text=secondary_label,
            command=on_secondary,
        )
        secondary_btn.pack(side="left", padx=6)
