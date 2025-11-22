import queue
import time
from threading import Event

import psutil

from . import config
from .notifications import notify_user
from .utils.process_utils import is_chrome_proc, classify_proc
from .tab_metrics import get_tab_metrics_blocking   # ← REQUIRED IMPORT

# this method is used to compute overall cpu usage
def monitor_chrome_loop(
    metrics_queue: queue.Queue,
    stop_event: Event,
) -> None:
    # Number of consecutive samples over threshold
    hits = 0

    # Main loop runs until the stop_event is set by the UI
    while not stop_event.is_set():
        # Get all Chrome related processes
        chrome_procs = [p for p in psutil.process_iter(["name"]) if is_chrome_proc(p)]

        # If Chrome is not running, send idle metrics and sleep
        if not chrome_procs:
            metrics_queue.put(
                {
                    "total_cpu": 0.0,
                    "worst_cpu": 0.0,
                    "worst_kind": "none",
                    "pid": None,
                    "cmd_preview": "",
                    "alert": None,
                }
            )
            time.sleep(config.POLL_INTERVAL)
            continue

        # Collect CPU usage and classification for each Chrome process
        usage = []
        for p in chrome_procs:
            try:
                cpu = p.cpu_percent(interval=0.0)
                kind = classify_proc(p)
                usage.append((cpu, kind, p))
            except psutil.Error:
                # Skip processes that cannot be inspected
                continue

        # If nothing usable was collected, just try again later
        if not usage:
            time.sleep(config.POLL_INTERVAL)
            continue

        # Aggregate total CPU and find the worst single process
        total_cpu = sum(u[0] for u in usage)
        worst_cpu, worst_kind, worst_proc = max(usage, key=lambda x: x[0])

        # Try to get a short command line preview for the worst process
        try:
            cmdline_preview = " ".join(worst_proc.cmdline())[:200]
        except psutil.Error:
            cmdline_preview = ""

        # Decide whether to trigger an alert based on thresholds
        alert = None
        if (
            total_cpu > config.CPU_THRESHOLD_TOTAL
            or worst_cpu > config.CPU_THRESHOLD_SINGLE
        ):
            hits += 1
        else:
            hits = 0

        # If high usage has persisted for enough intervals, fire an alert
        if hits >= config.SUSTAINED_HITS:
            alert = (
                f"Latency spike: {worst_kind} process\n"
                f"Single CPU: {worst_cpu:.1f}%   Total Chrome: {total_cpu:.1f}%\n"
                f"PID: {worst_proc.pid}\n"
                f"Cmd: {cmdline_preview}"
            )
            notify_user("Chrome latency spike", alert)
            hits = 0

        # -------------------------------------------------------------------
        # Try to gather per-tab CPU estimates from the Chrome DevTools Protocol
        # -------------------------------------------------------------------
        try:
            # get_tab_metrics_blocking() returns a list of TabMetric objects
            # Each TabMetric contains: title, url, and an estimated cpu_pct contribution
            tab_metrics = get_tab_metrics_blocking(interval=config.POLL_INTERVAL)
        except Exception:
            # If anything goes wrong (Chrome not reachable, debug port disabled, etc.)
            # fall back to an empty list so the rest of the code can proceed normally.
            tab_metrics = []

        # Build the metrics dictionary that will be sent to the UI thread.
        metrics = {
            # Total Chrome CPU from psutil
            "total_cpu": total_cpu,

            # Worst single Chrome process (from psutil)
            "worst_cpu": worst_cpu,
            "worst_kind": worst_kind,
            "pid": worst_proc.pid,
            "cmd_preview": cmdline_preview,

            # Optional alert string (None if no alert triggered)
            "alert": alert,

            # Number of Chrome tabs detected through the debugging port
            "tab_count": len(tab_metrics),

            # Detailed per-tab metrics to display in the UI
            # Converted from TabMetric objects into simple dictionaries
            "tabs": [
                {
                    "title": m.title,      # Tab title from DevTools
                    "url": m.url,          # Tab URL
                    "cpu_pct": m.cpu_pct,  # Normalized CPU contribution estimate
                }
                for m in tab_metrics
            ],
        }

        # Send the metrics dictionary to the queue so the UI can update its widgets.
        metrics_queue.put(metrics)

        # Sleep until the next monitoring interval (e.g., every 3 seconds)
        time.sleep(config.POLL_INTERVAL)
