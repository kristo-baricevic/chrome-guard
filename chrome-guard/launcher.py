import subprocess
from pathlib import Path

from . import config


def launch_chrome(url: str | None = None) -> subprocess.Popen:
    Path(config.PROFILE_DIR).mkdir(parents=True, exist_ok=True)
    cmd = [config.CHROME_PATH] + list(config.CHROME_FLAGS)
    if url:
        cmd.append(url)
    return subprocess.Popen(cmd)
