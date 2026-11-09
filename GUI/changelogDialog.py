import tkinter as tk
from tkinter import ttk

from GUI.customTheme import TBASDarkTheme
from Services.versionManager import getVersionLabel


def showChangelog(root, sections):
    """A window listing what changed: sections from changelogService.changesSince, newest first."""
    dialog = tk.Toplevel(root, bg=TBASDarkTheme.BG_DARK)
    dialog.title("What's new in TBAS Sync")
    dialog.transient(root)
    dialog.geometry("600x440")
    dialog.minsize(420, 280)

    buttons = ttk.Frame(dialog, padding=(16, 0, 16, 16))
    buttons.pack(side="bottom", fill="x")
    close = ttk.Button(buttons, text="Close", style="Accent.TButton", command=dialog.destroy)
    close.pack(side="right")

    frame = tk.Frame(dialog, bg=TBASDarkTheme.BG_DARK)
    frame.pack(fill="both", expand=True, padx=16, pady=16)
    scrollbar = ttk.Scrollbar(frame, orient="vertical")
    scrollbar.pack(side="right", fill="y")
    text = tk.Text(frame, wrap="word", relief="flat", borderwidth=0, padx=4, pady=4,
                   bg=TBASDarkTheme.BG_DARK, fg=TBASDarkTheme.FG_PRIMARY,
                   font=("Bahnschrift Light Condensed", 12), yscrollcommand=scrollbar.set)
    text.pack(side="left", fill="both", expand=True)
    scrollbar.configure(command=text.yview)

    text.tag_configure("version", font=("Bahnschrift Light Condensed", 18, "bold"),
                       foreground=TBASDarkTheme.ACCENT_PRIMARY, spacing1=10, spacing3=2)
    text.tag_configure("heading", font=("Bahnschrift Light Condensed", 13, "bold"), spacing1=8, spacing3=2)
    text.tag_configure("item", lmargin1=8, lmargin2=24, spacing3=4)

    for version, date, lines in sections:
        text.insert("end", f"TBAS Sync {getVersionLabel(version)}", "version")
        text.insert("end", f"   {date}\n" if date else "\n")
        for line in lines:
            line = line.replace("`", "").replace("**", "")
            if line.startswith("### "):
                text.insert("end", line[4:] + "\n", "heading")
            elif line.startswith("- "):
                text.insert("end", "•  " + line[2:] + "\n", "item")
            elif line.startswith("  ") and line.strip():   # a wrapped bullet continues
                text.insert("end", line.strip() + "\n", "item")
            elif line.strip():
                text.insert("end", line + "\n")
    text.configure(state="disabled")

    dialog.update_idletasks()
    x = root.winfo_rootx() + (root.winfo_width() - dialog.winfo_width()) // 2
    y = root.winfo_rooty() + (root.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")
    close.focus_set()
    return dialog
