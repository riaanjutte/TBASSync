import threading

import pystray
from PIL import Image

from Services.filesService import getRessourcePath


class TrayIcon:
    """System tray icon with Open / Check now / Quit and Windows notifications.

    pystray runs its own message loop on a background thread and calls menu
    actions there, so every action is handed to the Tk thread through `ui`.
    """

    def __init__(self, ui, on_open, on_check, on_quit):
        menu = pystray.Menu(
            pystray.MenuItem("Open TBAS Sync", lambda: ui.call(on_open), default=True),
            pystray.MenuItem("Check for skin updates now", lambda: ui.call(on_check)),
            pystray.MenuItem("Quit", lambda: ui.call(on_quit)),
        )
        self._icon = pystray.Icon("TBASSync", Image.open(getRessourcePath("TBAS.png")), "TBAS Sync", menu)
        threading.Thread(target=self._icon.run, daemon=True).start()

    def notify(self, title, message):
        self._icon.notify(message, title)

    def stop(self):
        self._icon.stop()
