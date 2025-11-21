import queue
import time
from threading import Event

import psutil

from . import config
from .notifications import notify_user
from .utils.process_utils import is_chrome_proc, classify_proc


def monitor_chrome_loop(
    metrics_queue: queue.Queue,
    stop_event: Event,
) -> None:
    hits = 0

    while not stop_event.is_set():
        chrome_procs = [p for p in psutil.process_iter(["name"]) if is_chrome_proc(p)]

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

        usage = []
        for p in chrome_procs:
            try:
                cpu = p.cpu_percent(interval=0.0)
                kind = classify_proc(p)
                usage.append((cpu, kind, p))
            except psutil.Error:
                continue

        if not usage:
            time.sleep(config.POLL_INTERVAL)
            continue

        total_cpu = sum(u[0] for u in usage)
        worst_cpu, worst_kind, worst_proc = max(usage, key=lambda x: x[0])

        try:
            cmdline_preview = " ".join(worst_proc.cmdline())[:200]
        except psutil.Error:
            cmdline_preview = ""

        alert = None
        if (
            total_cpu > config.CPU_THRESHOLD_TOTAL
            or worst_cpu > config.CPU_THRESHOLD_SINGLE
        ):
            hits += 1
        else:
            hits = 0

        if hits >= config.SUSTAINED_HITS:
            alert = (
                f"Latency spike: {worst_kind} process\n"
                f"Single CPU: {worst_cpu:.1f}%   Total Chrome: {total_cpu:.1f}%\n"
                f"PID: {worst_proc.pid}\n"
                f"Cmd: {cmdline_preview}"
            )
            notify_user("Chrome latency spike", alert)
            hits = 0

        metrics = {
            "total_cpu": total_cpu,
            "worst_cpu": worst_cpu,
            "worst_kind": worst_kind,
            "pid": worst_proc.pid,
            "cmd_preview": cmdline_preview,
            "alert": alert,
        }

        metrics_queue.put(metrics)
        time.sleep(config.POLL_INTERVAL)
