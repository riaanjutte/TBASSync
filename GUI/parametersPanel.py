import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkFont
import threading
from PIL import Image, ImageTk

from GUI.Components.tooltip import Tooltip
from Services.configurationService import getConf, update_config_param, cockpitNotesModes, checkIL2InstallPath, tryToFindIL2PathViaSteam, tryToFindIL2PathBroadSearch
from Services.filesService import getIconPath
from Services.messageBrocker import MessageBrocker

class ParametersPanel:
    def __init__(self, root: tk, on_parameters_change=None, ask_broad_search=None):
        self.root = root
        self.on_parameters_change = on_parameters_change
        self._external_ask_broad_search = ask_broad_search

        params_label_frame = ttk.Frame(root, padding=(5, 5))
        params_label_frame.pack(fill="both", padx=2, pady=2)
        
        # Path frame
        path_frame = tk.Frame(params_label_frame)
        path_frame.pack(fill="x", pady=2)
        
        # Frame to contain icon and label (for better alignment)
        path_content_frame = tk.Frame(path_frame)
        path_content_frame.pack(fill="both", expand=True)
        path_content_frame.columnconfigure(1, weight=1)
        
        # Icon (path placeholder)
        self.icon_path_image = ImageTk.PhotoImage(Image.open(getIconPath("IL2.png")).convert('RGBA').resize((24, 24), Image.Resampling.LANCZOS))
        self.icon_path = tk.Label(path_content_frame, image=self.icon_path_image)
        self.icon_path.grid(row=0, column=0, padx=(0, 5))

        # Clickable path label
        self.path_label = ttk.Label(path_content_frame,
                                  style="Path.TLabel",
                                  cursor="hand2")
        self.path_label.grid(row=0, column=1, sticky="ew")
        self._path_font = tkFont.Font(family="Bahnschrift Light Condensed", size=16, underline=1)
        self._current_full_path = ""
        self.path_label.bind("<Configure>", self._on_path_label_configure)
        Tooltip(self.path_label, "Click to specify the game directory")

        # Auto-detect button (only shown when path is invalid)
        self.find_btn = ttk.Button(path_content_frame, text="Auto-detect", command=self.auto_find_path)
        # not gridded initially — shown only when path is invalid

        self.update_pathLabel()

        cokpit_note_frame = tk.Frame(params_label_frame)
        cokpit_note_frame.pack(fill="x", pady=2)

        cokpitNote_label = tk.Label(cokpit_note_frame, text="Cockpit notes/photos", anchor="w", font=("Bahnschrift Light Condensed", 14))
        cokpitNote_label.pack(side=tk.LEFT, padx=5)

        self.cokpitNote_dropdown = ttk.Combobox(
            cokpit_note_frame,
            values=[cockpitNotesModes[mode] for mode in cockpitNotesModes.keys()],
            state="readonly",
            width=60,
            font=("Bahnschrift Light Condensed", 14),
        )
        Tooltip(self.cokpitNote_dropdown, text="Select the cockpit photos collection - some include notes on the plane's operational limits")
        self.cokpitNote_dropdown.set(cockpitNotesModes[getConf("cockpitNotesMode")])
        self.cokpitNote_dropdown.pack(side=tk.LEFT, padx=5)
        self.cokpitNote_dropdown.bind("<<ComboboxSelected>>", self.on_cokpitNote_dropdown_change)

        restricted_frame = tk.Frame(params_label_frame)
        restricted_frame.pack(fill="x", pady=2)

        restricted_label = tk.Label(restricted_frame, text="Restricted symbols", anchor="w", font=("Bahnschrift Light Condensed", 14))
        restricted_label.pack(side=tk.LEFT, padx=5)
        Tooltip(restricted_label, text="Hide replaces symbols like swastikas with neutral markings. Required in some countries.")

        self.hide_restricted_var = tk.BooleanVar(value=getConf("applyCensorship"))

        self.hide_restricted_radio = ttk.Radiobutton(
            restricted_frame,
            text="Hide",
            variable=self.hide_restricted_var,
            value=True,
            command=self.modify_apply_censorship,
        )
        self.hide_restricted_radio.pack(side=tk.LEFT, padx=(15, 5))

        self.show_restricted_radio = ttk.Radiobutton(
            restricted_frame,
            text="Show",
            variable=self.hide_restricted_var,
            value=False,
            command=self.modify_apply_censorship,
        )
        self.show_restricted_radio.pack(side=tk.LEFT, padx=5)

    def emit_collections_change(self):
        #external emit
        if self.on_parameters_change:
            self.root.after(0, self.on_parameters_change)
    
    def _fit_path_text(self, fullPath, available_px):
        if available_px <= 0:
            return fullPath
        if self._path_font.measure(fullPath) <= available_px:
            return fullPath
        ellipsis = "..."
        ellipsis_px = self._path_font.measure(ellipsis)
        lo, hi = 0, len(fullPath)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self._path_font.measure(fullPath[:mid]) + ellipsis_px <= available_px:
                lo = mid
            else:
                hi = mid - 1
        return fullPath[:lo] + ellipsis

    def _on_path_label_configure(self, event):
        padding_px = 10
        fitted = self._fit_path_text(self._current_full_path, event.width - padding_px)
        if self.path_label.cget("text") != fitted:
            self.path_label.config(text=fitted)

    def update_pathLabel(self):
        self._current_full_path = getConf("IL2GBGameDirectory")
        width = self.path_label.winfo_width()
        padding_px = 10
        self.path_label.config(text=self._fit_path_text(self._current_full_path, width - padding_px))

        if checkIL2InstallPath():
            self.path_label.configure(style="Path.TLabel")
            self.find_btn.grid_remove()
        else:
            self.path_label.configure(style="PathError.TLabel")
            self.find_btn.grid(row=0, column=2, padx=(5, 0))

    def auto_find_path(self, on_complete=None):
        self._auto_detect_on_complete = on_complete
        found = tryToFindIL2PathViaSteam()
        if found:
            self._auto_detect_done(found)
            return

        self._ask_broad_search(self._on_broad_search_answer)

    def _on_broad_search_answer(self, wants_search):
        if not wants_search:
            self._auto_detect_done(None)
            return
        self.find_btn.configure(state="disabled", text="Searching...")
        self._start_broad_search()

    def _ask_broad_search(self, on_answer):
        if self._external_ask_broad_search is not None:
            self._external_ask_broad_search(on_answer)
            return
        answer = messagebox.askyesno(
            "Search computer?",
            "IL-2 was not found in your Steam installation.\n\n"
            "Would you like to search your entire computer for the IL-2 folder?\n"
            "(This may take a minute)"
        )
        on_answer(answer)

    def _auto_detect_done(self, found_path):
        if found_path is not None:
            update_config_param("IL2GBGameDirectory", found_path)
            self.update_pathLabel()
        cb = getattr(self, "_auto_detect_on_complete", None)
        self._auto_detect_on_complete = None
        if cb is not None:
            self.root.after(0, cb)
        else:
            self.emit_collections_change()

    def _start_broad_search(self):
        self._search_dialog = self._build_search_dialog()
        threading.Thread(target=self._broad_search_thread, daemon=True).start()

    def _build_search_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Searching computer")
        dialog.transient(self.root.winfo_toplevel())
        dialog.resizable(False, False)
        dialog.protocol("WM_DELETE_WINDOW", lambda: None)

        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text="Searching your computer for the IL-2 folder...\nThis may take a minute.",
            justify="center",
        ).pack(pady=(0, 10))
        progress = ttk.Progressbar(frame, mode="indeterminate", length=280)
        progress.pack()
        progress.start(12)

        dialog.update_idletasks()
        parent = self.root.winfo_toplevel()
        x = parent.winfo_rootx() + (parent.winfo_width() - dialog.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        dialog.grab_set()
        return dialog

    def _broad_search_thread(self):
        found = tryToFindIL2PathBroadSearch()
        self.root.after(3000, lambda: self._on_broad_search_done(found))

    def _on_broad_search_done(self, found):
        if getattr(self, "_search_dialog", None) is not None:
            self._search_dialog.grab_release()
            self._search_dialog.destroy()
            self._search_dialog = None
        self.find_btn.configure(state="normal", text="Auto-detect")
        if found:
            MessageBrocker.emitConsoleMessage(f"<green>Found IL-2 installation at: {found}</green>")
        self._auto_detect_done(found)
    
    def modify_path(self):
        file_path = filedialog.askdirectory(
            initialdir=getConf("IL2GBGameDirectory"),
            title="Select your IL2 folder"
        )
        if len(file_path) > 0:
            update_config_param("IL2GBGameDirectory", file_path)
            self.update_pathLabel()
            self.emit_collections_change()
    
    def modify_apply_censorship(self):
        update_config_param("applyCensorship", self.hide_restricted_var.get())
        self.emit_collections_change()
    
    def on_cokpitNote_dropdown_change(self, event):
        #find the cokpit not mode associated to the text
        selected_mode = next(mode for mode in cockpitNotesModes.keys()
                           if cockpitNotesModes[mode] == self.cokpitNote_dropdown.get())
        update_config_param("cockpitNotesMode", selected_mode)
        self.cokpitNote_dropdown.selection_clear()
        self.emit_collections_change()

    def lock_actions(self):
        self.cokpitNote_dropdown.configure(state="disabled")
        self.hide_restricted_radio.configure(state="disabled")
        self.show_restricted_radio.configure(state="disabled")
        self.path_label.unbind("<Button-1>")

    def unlock_actions(self):
        self.cokpitNote_dropdown.configure(state="readonly")
        self.hide_restricted_radio.configure(state="normal")
        self.show_restricted_radio.configure(state="normal")
        # Click event configuration
        self.path_label.bind("<Button-1>", lambda e: self.modify_path())