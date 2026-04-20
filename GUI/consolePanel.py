import re
import tkinter as tk
from collections import deque
from tkinter import ttk
from tkinter import font as tkfont

from Services.messageBrocker import MessageBrocker
from GUI.customTheme import TBASDarkTheme

LINE_DELAY_MS = 50
_TAG_RE = re.compile(r'<[^>]+>')
_FONT_PREFERENCE = ("Cascadia Mono", "Consolas", "Courier New")
_FONT_SIZE = 11


def _has_visible_content(line: str) -> bool:
    """Return True if the line contains anything other than whitespace + tag markup."""
    return bool(_TAG_RE.sub('', line).strip())


def _pick_console_font() -> str:
    """Return the first preferred font family that's actually installed."""
    available = set(tkfont.families())
    for family in _FONT_PREFERENCE:
        if family in available:
            return family
    return _FONT_PREFERENCE[-1]

class ConsolePanel:
    def __init__(self, root: tk):
        self.root = root
        self._pending_lines = deque()
        self._drain_scheduled = False
        self._font_family = _pick_console_font()

        # Create a frame to hold both Text and Scrollbar
        self.frame = tk.Frame(self.root)
        self.frame.pack(expand=True, fill="both")

        # Create Scrollbar widget
        self.scrollbar = ttk.Scrollbar(self.frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Create Text widget and connect it to Scrollbar
        self.text_widget = tk.Text(self.frame, wrap="char", height=15,
                                 yscrollcommand=self.scrollbar.set,
                                 font=(self._font_family, _FONT_SIZE),
                                 bg=TBASDarkTheme.BG_DARKER,
                                 fg=TBASDarkTheme.FG_PRIMARY,
                                 insertbackground=TBASDarkTheme.FG_PRIMARY,
                                 selectbackground=TBASDarkTheme.ACCENT_PRIMARY,
                                 relief="flat",
                                 borderwidth=0,
                                 padx=8, pady=6)
        self.text_widget.pack(side=tk.LEFT, expand=True, fill="both")
        
        # Configure Scrollbar to scroll the Text widget
        self.scrollbar.config(command=self.text_widget.yview)
        
        # Configure tags for formatting with theme colors
        self.text_widget.tag_configure("red", foreground=TBASDarkTheme.ERROR)
        self.text_widget.tag_configure("green", foreground=TBASDarkTheme.SUCCESS)
        self.text_widget.tag_configure("blue", foreground=TBASDarkTheme.INFO)
        self.text_widget.tag_configure("chocolate", foreground=TBASDarkTheme.WARNING)
        self.text_widget.tag_configure("italic", font=(self._font_family, _FONT_SIZE, "italic"))

        MessageBrocker.registerConsoleHook(self.addLine)

    def parse_and_insert_text(self, text: str):
        """Parse text and insert with appropriate tags"""
        # If no tags, insert directly
        if '<' not in text:
            self.text_widget.insert(tk.END, text)
            return

        current_pos = 0
        current_tags = []  # List of active tags

        while current_pos < len(text):
            # Look for next tag (opening or closing)
            next_tag_pos = text.find('<', current_pos)
            
            if next_tag_pos == -1:
                # No more tags, insert remaining text with current tags
                remaining_text = text[current_pos:]
                if remaining_text:
                    self.text_widget.insert(tk.END, remaining_text, tuple(current_tags))
                break
            
            # Insert text before the tag with current tags
            if next_tag_pos > current_pos:
                content = text[current_pos:next_tag_pos]
                self.text_widget.insert(tk.END, content, tuple(current_tags))
            
            # Process the tag
            if text[next_tag_pos:next_tag_pos+2] == '</':
                # Closing tag
                end_pos = text.find('>', next_tag_pos)
                if end_pos == -1:
                    break
                tag = text[next_tag_pos+2:end_pos]
                if tag in current_tags:
                    current_tags.remove(tag)
                current_pos = end_pos + 1
            else:
                # Opening tag
                end_pos = text.find('>', next_tag_pos)
                if end_pos == -1:
                    break
                tag = text[next_tag_pos+1:end_pos]
                current_tags.append(tag)
                current_pos = end_pos + 1
    
    def addLine(self, text):
        if text is None:
            return
        # Drop every empty/whitespace-only line, including blank lines embedded
        # inside a multi-line message (e.g. "\n*** Section ***\n\n").
        kept = [ln for ln in text.split('\n') if _has_visible_content(ln)]
        if not kept:
            return
        self._pending_lines.append('\n'.join(kept))
        if not self._drain_scheduled:
            self._drain_scheduled = True
            self.root.after(LINE_DELAY_MS, self._drain_next_line)

    def _drain_next_line(self):
        if not self._pending_lines:
            self._drain_scheduled = False
            return
        text = self._pending_lines.popleft()
        self.text_widget.config(state=tk.NORMAL)
        self.parse_and_insert_text(text)
        self.text_widget.insert(tk.END, "\n")
        self.text_widget.yview(tk.END)
        self.text_widget.config(state=tk.DISABLED)
        if self._pending_lines:
            self.root.after(LINE_DELAY_MS, self._drain_next_line)
        else:
            self._drain_scheduled = False

    def clearPanel(self):
        self._pending_lines.clear()
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.config(state=tk.DISABLED)