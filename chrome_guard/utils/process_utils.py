import psutil


CHROME_NAMES = {"Google Chrome", "Google Chrome Helper", "chrome", "chrome.exe"}


def is_chrome_proc(proc: psutil.Process) -> bool:
    try:
        return proc.name() in CHROME_NAMES
    except psutil.Error:
        return False


def classify_proc(proc: psutil.Process) -> str:
    try:
        cmd = " ".join(proc.cmdline())
    except psutil.Error:
        return "unknown"

    if "--type=gpu-process" in cmd:
        return "gpu"
    if "--type=renderer" in cmd and "--extension-process" in cmd:
        return "extension renderer"
    if "--type=renderer" in cmd:
        return "tab renderer"
    if "--type=utility" in cmd:
        return "utility"
    if "--type=zygote" in cmd:
        return "zygote"
    return "browser or other"
