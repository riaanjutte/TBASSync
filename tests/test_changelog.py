"""The changelog shown once after an update: which versions it covers, and when the window shows it.
Usage: python tests/test_changelog.py"""
import os
import tkinter as tk

import harness
from harness import check, mainGUI
import Services.changelogService as changelogService
from Services.versionManager import currentVersion

V = currentVersion
SAMPLE = f"""# Changelog

## [Unreleased]

### Added
- Not released yet.

## [{V}] - 2026-11-10

### Added
- New in {V}.
- Second item.

## [{V - 1}] - 2026-11-01

### Fixed
- Fixed in {V - 1}.

## [{V - 2}] - 2026-10-20

### Fixed
- Fixed in {V - 2}.
"""

# ── which sections
sections = changelogService.changesSince(SAMPLE, V - 2)
check("newer released sections only, newest first", [v for v, _, _ in sections] == [V, V - 1])
check("date and lines are kept", sections[0][1] == "2026-11-10"
      and sections[0][2] == ["### Added", f"- New in {V}.", "- Second item."])
check("Unreleased is never shown", all("Not released" not in line for _, _, lines in sections for line in lines))
check("nothing newer: empty", changelogService.changesSince(SAMPLE, V) == [])
real = open(os.path.join(harness.REPO, "CHANGELOG.md"), encoding="utf-8").read()
check("the real CHANGELOG.md parses: 16, 15, 14 after 13",
      [v for v, _, _ in changelogService.changesSince(real, 13, 16)] == [16, 15, 14])

# ── when there is something to show
changelog_file = os.path.join(harness.SANDBOX, "CHANGELOG.md")
open(changelog_file, "w", encoding="utf-8").write(SAMPLE)
changelogService.getRessourcePath = lambda rel: changelog_file

harness.write_config()   # a config from before this setting: no lastSeenVersion
check("updated from the previous version: shows this version's changes",
      [v for v, _, _ in changelogService.pendingChangelog(first_launch=False)] == [V])
harness.write_config(lastSeenVersion=V - 2)
check("skipped a version: shows both", [v for v, _, _ in changelogService.pendingChangelog(False)] == [V, V - 1])
harness.write_config(lastSeenVersion=V)
check("already seen: nothing", changelogService.pendingChangelog(False) == [])
harness.write_config(lastSeenVersion=None)
check("fresh install: nothing, and this version is recorded",
      changelogService.pendingChangelog(first_launch=True) == [] and harness.saved_config()["lastSeenVersion"] == V)
harness.write_config(lastSeenVersion=V - 1)
changelogService.getRessourcePath = lambda rel: os.path.join(harness.SANDBOX, "missing.md")
check("no changelog file: nothing, and not marked seen",
      changelogService.pendingChangelog(False) == [] and harness.saved_config()["lastSeenVersion"] == V - 1)
changelogService.getRessourcePath = lambda rel: changelog_file


# ── the window
def dialogs(root):
    return [w for w in root.winfo_children() if isinstance(w, tk.Toplevel) and w.title() == "What's new in TBAS Sync"]


def launch(started_at_login, steps):
    harness.write_config(trayMode=True, lastSeenVersion=V - 1)
    root = tk.Tk()
    gui = mainGUI.MainGUI(root, check_for_update=False, started_at_login=started_at_login)
    harness.run_steps(root, [lambda s=s: s(root, gui) for s in steps] + [gui.quit_app], delay_ms=900)
    root.mainloop()


def text_of(dialog):
    texts = [w for frame in dialog.winfo_children() for w in frame.winfo_children() if isinstance(w, tk.Text)]
    return texts[0].get("1.0", "end")


launch(False, [
    lambda root, gui: (check("user launch after an update: changelog shown", len(dialogs(root)) == 1),
                       check("it lists this version's changes", f"New in {V}." in text_of(dialogs(root)[0])
                             and "Version" not in text_of(dialogs(root)[0])),
                       check("it is marked seen", harness.saved_config()["lastSeenVersion"] == V),
                       dialogs(root)[0].destroy(), root.withdraw(), gui.show_window()),
    lambda root, gui: check("opening the window again: not shown twice", dialogs(root) == []),
])

launch(True, [
    lambda root, gui: (check("sign-in launch (hidden): not shown yet", dialogs(root) == []),
                       check("not marked seen while hidden", harness.saved_config()["lastSeenVersion"] == V - 1),
                       gui.show_window()),
    lambda root, gui: (check("window opened from the tray: changelog shown", len(dialogs(root)) == 1),
                       check("then marked seen", harness.saved_config()["lastSeenVersion"] == V)),
])

harness.finish()
