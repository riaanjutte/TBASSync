"""
TBAS Custom Dark Theme for tkinter/ttk
Charcoal dark theme with orange brand accent
"""

from tkinter import ttk
import sys
import ctypes


class TBASDarkTheme:
    """Custom charcoal dark theme for TBAS application"""

    # Background scale — near-black charcoal
    BG_DARKER   = "#111111"   # Header, titlebar, console bg
    BG_DARK     = "#1c1c1c"   # Main window background
    BG_LIGHT    = "#252525"   # Panels, cards, input fields
    BG_HOVER    = "#303030"   # Hover state

    # Foreground
    FG_PRIMARY   = "#efefef"  # Primary text
    FG_SECONDARY = "#888888"  # Muted / secondary text
    FG_DISABLED  = "#444444"  # Disabled elements

    # Brand accent — matches TBAS logo orange
    ACCENT_PRIMARY = "#e07820"
    ACCENT_HOVER   = "#c86010"
    ACCENT_DARK    = "#a04a00"

    # Structural
    BORDER = "#2a2a2a"        # Subtle border

    # Semantic — used for console message coloring; keep distinct from accent
    ERROR   = "#e05050"       # Red
    SUCCESS = "#50c878"       # Green
    INFO    = "#5b9bd5"       # Blue
    WARNING = "#d4890a"       # Amber (intentionally distinct from ACCENT orange)

    @staticmethod
    def _set_window_titlebar_color(root):
        if sys.platform != "win32":
            return
        try:
            hex_color = TBASDarkTheme.BG_DARKER.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            bgr_color = b << 16 | g << 8 | r
            hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
            DWMWA_CAPTION_COLOR        = 35
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            try:
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_CAPTION_COLOR,
                    ctypes.byref(ctypes.c_int(bgr_color)), ctypes.sizeof(ctypes.c_int)
                )
            except Exception:
                pass
            try:
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                    ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
                )
            except Exception:
                pass
        except Exception:
            pass

    @staticmethod
    def apply(root):
        style = ttk.Style(root)
        style.theme_use('clam')

        # ===== GENERAL =====
        style.configure(".",
            background=TBASDarkTheme.BG_DARK,
            foreground=TBASDarkTheme.FG_PRIMARY,
            bordercolor=TBASDarkTheme.BORDER,
            darkcolor=TBASDarkTheme.BG_DARK,
            lightcolor=TBASDarkTheme.BG_LIGHT,
            troughcolor=TBASDarkTheme.BG_LIGHT,
            focuscolor=TBASDarkTheme.ACCENT_PRIMARY,
            selectbackground=TBASDarkTheme.ACCENT_PRIMARY,
            selectforeground=TBASDarkTheme.FG_PRIMARY,
            selectborderwidth=0,
            font=("Bahnschrift Light Condensed", 14)
        )

        # ===== FRAME =====
        style.configure("TFrame", background=TBASDarkTheme.BG_DARK, borderwidth=0)

        # ===== LABEL =====
        style.configure("TLabel",
            background=TBASDarkTheme.BG_DARK,
            foreground=TBASDarkTheme.FG_PRIMARY,
            borderwidth=0
        )
        style.map("TLabel", foreground=[("disabled", TBASDarkTheme.FG_DISABLED)])

        # ===== BUTTON =====
        style.configure("TButton",
            background=TBASDarkTheme.BG_LIGHT,
            foreground=TBASDarkTheme.FG_PRIMARY,
            bordercolor=TBASDarkTheme.BORDER,
            lightcolor=TBASDarkTheme.BG_LIGHT,
            darkcolor=TBASDarkTheme.BG_LIGHT,
            borderwidth=1,
            focuscolor=TBASDarkTheme.ACCENT_PRIMARY,
            padding=(12, 6),
            relief="flat"
        )
        style.map("TButton",
            background=[
                ("active",   TBASDarkTheme.BG_HOVER),
                ("disabled", TBASDarkTheme.BG_DARK),
                ("pressed",  TBASDarkTheme.BG_DARK)
            ],
            foreground=[("disabled", TBASDarkTheme.FG_DISABLED)],
            bordercolor=[
                ("active", TBASDarkTheme.ACCENT_PRIMARY),
                ("focus",  TBASDarkTheme.ACCENT_PRIMARY)
            ]
        )

        # ===== ACCENT BUTTON (Synchronize) =====
        style.configure("Accent.TButton",
            background=TBASDarkTheme.ACCENT_PRIMARY,
            foreground=TBASDarkTheme.FG_PRIMARY,
            bordercolor=TBASDarkTheme.ACCENT_PRIMARY,
            lightcolor=TBASDarkTheme.ACCENT_PRIMARY,
            darkcolor=TBASDarkTheme.ACCENT_PRIMARY,
            borderwidth=0,
            padding=(12, 6),
            relief="flat"
        )
        style.map("Accent.TButton",
            background=[
                ("active",   TBASDarkTheme.ACCENT_HOVER),
                ("disabled", TBASDarkTheme.BG_LIGHT),
                ("pressed",  TBASDarkTheme.ACCENT_DARK)
            ],
            foreground=[("disabled", TBASDarkTheme.FG_DISABLED)]
        )

        # ===== DANGER BUTTON (Exit) =====
        # Tkinter widgets don't support true alpha; these colors are 50% blends
        # of the solid red palette with BG_DARK so the button reads as faded.
        style.configure("Danger.TButton",
            background="#712222",
            foreground="#858585",
            bordercolor="#712222",
            lightcolor="#712222",
            darkcolor="#712222",
            borderwidth=0,
            padding=(12, 6),
            relief="flat"
        )
        style.map("Danger.TButton",
            background=[
                ("active",   "#802a28"),
                ("disabled", TBASDarkTheme.BG_LIGHT),
                ("pressed",  "#551d1d")
            ],
            foreground=[("disabled", TBASDarkTheme.FG_DISABLED)]
        )

        # ===== LABELFRAME =====
        style.configure("TLabelframe",
            background=TBASDarkTheme.BG_DARK,
            foreground=TBASDarkTheme.FG_PRIMARY,
            bordercolor=TBASDarkTheme.BORDER,
            borderwidth=1,
            relief="solid"
        )
        style.configure("TLabelframe.Label",
            background=TBASDarkTheme.BG_DARK,
            foreground=TBASDarkTheme.FG_SECONDARY,
            font=("Bahnschrift Light Condensed", 14, "bold")
        )

        # ===== ENTRY =====
        style.configure("TEntry",
            fieldbackground=TBASDarkTheme.BG_LIGHT,
            background=TBASDarkTheme.BG_LIGHT,
            foreground=TBASDarkTheme.FG_PRIMARY,
            bordercolor=TBASDarkTheme.BORDER,
            lightcolor=TBASDarkTheme.BG_LIGHT,
            darkcolor=TBASDarkTheme.BG_LIGHT,
            insertcolor=TBASDarkTheme.FG_PRIMARY,
            borderwidth=1,
            relief="solid"
        )
        style.map("TEntry",
            fieldbackground=[
                ("disabled", TBASDarkTheme.BG_DARK),
                ("readonly", TBASDarkTheme.BG_DARK)
            ],
            foreground=[("disabled", TBASDarkTheme.FG_DISABLED)],
            bordercolor=[
                ("focus",  TBASDarkTheme.ACCENT_PRIMARY),
                ("active", TBASDarkTheme.ACCENT_PRIMARY)
            ]
        )

        # ===== COMBOBOX =====
        style.configure("TCombobox",
            fieldbackground=TBASDarkTheme.BG_LIGHT,
            background=TBASDarkTheme.BG_LIGHT,
            foreground=TBASDarkTheme.FG_PRIMARY,
            bordercolor=TBASDarkTheme.BORDER,
            lightcolor=TBASDarkTheme.BG_LIGHT,
            darkcolor=TBASDarkTheme.BG_LIGHT,
            arrowcolor=TBASDarkTheme.FG_SECONDARY,
            borderwidth=1,
            relief="solid"
        )
        style.map("TCombobox",
            fieldbackground=[
                ("disabled", TBASDarkTheme.BG_DARK),
                ("readonly", TBASDarkTheme.BG_LIGHT)
            ],
            foreground=[
                ("disabled", TBASDarkTheme.FG_DISABLED),
                ("readonly", TBASDarkTheme.FG_PRIMARY)
            ],
            bordercolor=[
                ("focus",  TBASDarkTheme.ACCENT_PRIMARY),
                ("active", TBASDarkTheme.ACCENT_PRIMARY)
            ],
            selectbackground=[("readonly", TBASDarkTheme.ACCENT_PRIMARY)],
            selectforeground=[("readonly", TBASDarkTheme.FG_PRIMARY)]
        )

        # ===== CHECKBUTTON =====
        style.configure("TCheckbutton",
            background=TBASDarkTheme.BG_DARK,
            foreground=TBASDarkTheme.FG_PRIMARY,
            bordercolor=TBASDarkTheme.BORDER,
            indicatorbackground=TBASDarkTheme.BG_LIGHT,
            indicatorforeground=TBASDarkTheme.ACCENT_PRIMARY,
            focuscolor=TBASDarkTheme.ACCENT_PRIMARY
        )
        style.map("TCheckbutton",
            background=[("active", TBASDarkTheme.BG_DARK)],
            foreground=[("disabled", TBASDarkTheme.FG_DISABLED)],
            indicatorbackground=[
                ("selected", TBASDarkTheme.ACCENT_PRIMARY),
                ("active",   TBASDarkTheme.BG_HOVER)
            ]
        )

        # ===== RADIOBUTTON =====
        style.configure("TRadiobutton",
            background=TBASDarkTheme.BG_DARK,
            foreground=TBASDarkTheme.FG_PRIMARY,
            bordercolor=TBASDarkTheme.BORDER,
            indicatorbackground=TBASDarkTheme.BG_LIGHT,
            indicatorforeground=TBASDarkTheme.ACCENT_PRIMARY,
            focuscolor=TBASDarkTheme.BG_DARK
        )
        style.map("TRadiobutton",
            background=[("active", TBASDarkTheme.BG_DARK)],
            foreground=[("disabled", TBASDarkTheme.FG_DISABLED)],
            indicatorbackground=[
                ("selected", TBASDarkTheme.ACCENT_PRIMARY),
                ("active",   TBASDarkTheme.BG_HOVER)
            ]
        )

        # ===== SCROLLBAR =====
        style.configure("Vertical.TScrollbar",
            background=TBASDarkTheme.BG_HOVER,
            troughcolor=TBASDarkTheme.BG_DARK,
            bordercolor=TBASDarkTheme.BG_DARK,
            arrowcolor=TBASDarkTheme.FG_SECONDARY,
            borderwidth=0,
            relief="flat"
        )
        style.map("Vertical.TScrollbar",
            background=[
                ("active",  TBASDarkTheme.ACCENT_PRIMARY),
                ("pressed", TBASDarkTheme.ACCENT_DARK)
            ]
        )
        style.configure("Horizontal.TScrollbar",
            background=TBASDarkTheme.BG_HOVER,
            troughcolor=TBASDarkTheme.BG_DARK,
            bordercolor=TBASDarkTheme.BG_DARK,
            arrowcolor=TBASDarkTheme.FG_SECONDARY,
            borderwidth=0,
            relief="flat"
        )
        style.map("Horizontal.TScrollbar",
            background=[
                ("active",  TBASDarkTheme.ACCENT_PRIMARY),
                ("pressed", TBASDarkTheme.ACCENT_DARK)
            ]
        )

        # ===== SEPARATOR =====
        style.configure("TSeparator", background=TBASDarkTheme.BORDER)

        # ===== TREEVIEW =====
        style.configure("Treeview",
            background=TBASDarkTheme.BG_LIGHT,
            foreground=TBASDarkTheme.FG_PRIMARY,
            fieldbackground=TBASDarkTheme.BG_LIGHT,
            bordercolor=TBASDarkTheme.BORDER,
            borderwidth=1,
            relief="solid",
            rowheight=24
        )
        style.configure("Treeview.Heading",
            background=TBASDarkTheme.BG_DARK,
            foreground=TBASDarkTheme.FG_SECONDARY,
            bordercolor=TBASDarkTheme.BORDER,
            relief="flat",
            font=("Bahnschrift Light Condensed", 14, "bold")
        )
        style.map("Treeview",
            background=[("selected", TBASDarkTheme.ACCENT_PRIMARY)],
            foreground=[("selected", TBASDarkTheme.FG_PRIMARY)]
        )
        style.map("Treeview.Heading",
            background=[("active", TBASDarkTheme.BG_HOVER)]
        )

        # ===== CUSTOM LABEL STYLES =====
        style.configure("Path.TLabel",
            background=TBASDarkTheme.BG_DARK,
            foreground=TBASDarkTheme.ACCENT_PRIMARY,
            font=("Bahnschrift Light Condensed", 14, "underline"),
            cursor="hand2",
            padding=5
        )
        style.configure("PathError.TLabel",
            background="#5a1010",
            foreground=TBASDarkTheme.FG_PRIMARY,
            font=("Bahnschrift Light Condensed", 14, "underline"),
            cursor="hand2",
            padding=5
        )

        # ===== TK WIDGET DEFAULTS =====
        root.option_add("*Background",        TBASDarkTheme.BG_DARK)
        root.option_add("*Foreground",        TBASDarkTheme.FG_PRIMARY)
        root.option_add("*selectBackground",  TBASDarkTheme.ACCENT_PRIMARY)
        root.option_add("*selectForeground",  TBASDarkTheme.FG_PRIMARY)
        root.option_add("*activeBackground",  TBASDarkTheme.BG_HOVER)
        root.option_add("*activeForeground",  TBASDarkTheme.FG_PRIMARY)
        root.option_add("*highlightBackground", TBASDarkTheme.BG_DARK)
        root.option_add("*highlightColor",    TBASDarkTheme.ACCENT_PRIMARY)
        root.option_add("*TCombobox*Listbox.font", ("Bahnschrift Light Condensed", 14))
        root.option_add("*Font", ("Bahnschrift Light Condensed", 14))

        root.configure(background=TBASDarkTheme.BG_DARK)
        root.update_idletasks()
        TBASDarkTheme._set_window_titlebar_color(root)


def apply_theme(root):
    TBASDarkTheme.apply(root)


def apply_titlebar_color(window):
    window.update_idletasks()
    TBASDarkTheme._set_window_titlebar_color(window)
