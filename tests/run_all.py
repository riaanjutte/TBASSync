"""Run every test, each in its own process (GUI tests open real windows and tray icons).
Usage: venv\\Scripts\\python.exe tests\\run_all.py
Needs a Windows desktop session; takes about a minute."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = [
    ("test_services.py",),
    ("test_sync_guards.py",),
    ("test_cockpit_preview.py",),
    ("test_changelog.py",),
    ("test_hangar.py",),
    ("test_background_checkbox.py", "on"),
    ("test_background_checkbox.py", "off"),
    ("test_background_checkbox.py", "fresh"),
    ("test_quit_during_sync.py", "on"),
    ("test_quit_during_sync.py", "off"),
    ("test_launch_visibility.py", "rules"),
    ("test_launch_visibility.py", "signal"),
]

failed = []
for script, *args in RUNS:
    name = " ".join([script, *args])
    proc = subprocess.run([sys.executable, os.path.join(HERE, script), *args],
                          capture_output=True, text=True, timeout=180, cwd=HERE)
    lines = [l for l in proc.stdout.splitlines() if l.startswith(("PASS", "FAIL", "RESULT"))]
    ok = proc.returncode == 0 and lines and lines[-1] == "RESULT: ALL PASS"
    print(f"{'ok  ' if ok else 'FAIL'} {name}")
    if not ok:
        failed.append(name)
        print("\n".join("    " + l for l in lines if not l.startswith("PASS")) or proc.stderr[-2000:])

print(f"\n{len(RUNS) - len(failed)}/{len(RUNS)} passed")
sys.exit(1 if failed else 0)
