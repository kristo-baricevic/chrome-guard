import os
import platform
from pathlib import Path


def _default_chrome_path() -> str:
    system = platform.system()
    if system == "Darwin":
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if system == "Windows":
        return r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    return "google-chrome"


CHROME_PATH = os.environ.get("CHROME_GUARD_CHROME_PATH", _default_chrome_path())

_home = Path.home()
_system = platform.system()

if _system == "Darwin":
    PROFILE_DIR = _home / "Library/Application Support/Google/Chrome/LowLatencyProfile"
elif _system == "Windows":
    PROFILE_DIR = _home / "AppData/Local/Google/Chrome/User Data/LowLatencyProfile"
else:
    PROFILE_DIR = _home / ".config/chrome-guard-profile"

CHROME_FLAGS = [
    "--disable-background-networking",
    "--remote-debugging-port=9222",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--process-per-site",
    "--disable-features=InfiniteSessionRestore,HeavyAdIntervention",
    "--no-first-run",
    f"--user-data-dir={PROFILE_DIR}",
    "--remote-debugging-port=9222",
]

CPU_THRESHOLD_TOTAL = float(os.getenv("CHROME_GUARD_CPU_TOTAL", "200"))
CPU_THRESHOLD_SINGLE = float(os.getenv("CHROME_GUARD_CPU_SINGLE", "120"))
POLL_INTERVAL = float(os.getenv("CHROME_GUARD_POLL_INTERVAL", "3"))
SUSTAINED_HITS = int(os.getenv("CHROME_GUARD_SUSTAINED_HITS", "3"))
