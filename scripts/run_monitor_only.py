import queue
from threading import Event

from chrome_guard.monitor import monitor_chrome_loop


def main() -> None:
    metrics_queue = queue.Queue()
    stop_event = Event()
    try:
        monitor_chrome_loop(metrics_queue, stop_event)
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    main()
