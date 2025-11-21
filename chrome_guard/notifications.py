import platform
import subprocess


def notify_user(title: str, message: str) -> None:
    system = platform.system()

    if system == "Darwin":
        try:
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "{message}" with title "{title}"',
                ],
                check=False,
            )
            return
        except FileNotFoundError:
            pass

    if system == "Linux":
        try:
            subprocess.run(
                ["notify-send", title, message],
                check=False,
            )
            return
        except FileNotFoundError:
            pass

    print(f"{title}: {message}")
