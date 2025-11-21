import queue
from threading import Event, Thread

import tkinter as tk
from tkinter import ttk

from .launcher import launch_chrome
from .monitor import monitor_chrome_loop


class ChromeGuardUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Chrome Guard")
        self.root.geometry("600x400")

        self.metrics_queue: queue.Queue = queue.Queue()
        self.stop_event = Event()
        self.monitor_thread = Thread(
            target=monitor_chrome_loop,
            args=(self.metrics_queue, self.stop_event),
            daemon=True,
        )
        self.monitor_thread.start()

        self._build_widgets()
        self._poll_metrics()

    def _build_widgets(self) -> None:
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        url_frame = ttk.Frame(main)
        url_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(url_frame, text="URL:").pack(side="left")

        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))

        open_btn = ttk.Button(url_frame, text="Open in Chrome", command=self._on_open)
        open_btn.pack(side="right")

        meters_frame = ttk.LabelFrame(main, text="Resource usage")
        meters_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(meters_frame, text="Total Chrome CPU %").pack(anchor="w")
        self.total_cpu_var = tk.DoubleVar(value=0.0)
        self.total_cpu_bar = ttk.Progressbar(
            meters_frame,
            maximum=400.0,
            variable=self.total_cpu_var,
        )
        self.total_cpu_bar.pack(fill="x", pady=(0, 5))

        ttk.Label(meters_frame, text="Worst process CPU %").pack(anchor="w")
        self.worst_cpu_var = tk.DoubleVar(value=0.0)
        self.worst_cpu_bar = ttk.Progressbar(
            meters_frame,
            maximum=200.0,
            variable=self.worst_cpu_var,
        )
        self.worst_cpu_bar.pack(fill="x", pady=(0, 5))

        info_frame = ttk.LabelFrame(main, text="Current culprit")
        info_frame.pack(fill="x", pady=(0, 10))

        self.kind_var = tk.StringVar(value="none")
        self.pid_var = tk.StringVar(value="-")
        self.cmd_var = tk.StringVar(value="")

        ttk.Label(info_frame, text="Type:").grid(row=0, column=0, sticky="w")
        ttk.Label(info_frame, textvariable=self.kind_var).grid(
            row=0, column=1, sticky="w", padx=5
        )

        ttk.Label(info_frame, text="PID:").grid(row=1, column=0, sticky="w")
        ttk.Label(info_frame, textvariable=self.pid_var).grid(
            row=1, column=1, sticky="w", padx=5
        )

        ttk.Label(info_frame, text="Cmd:").grid(row=2, column=0, sticky="nw")
        self.cmd_label = ttk.Label(info_frame, textvariable=self.cmd_var, wraplength=450)
        self.cmd_label.grid(row=2, column=1, sticky="w", padx=5)

        info_frame.columnconfigure(1, weight=1)

        alerts_frame = ttk.LabelFrame(main, text="Alerts")
        alerts_frame.pack(fill="both", expand=True)

        self.alert_text = tk.Text(alerts_frame, height=6, wrap="word")
        self.alert_text.pack(fill="both", expand=True)

    def _on_open(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            url = "about:blank"
        if not (
            url.startswith("http://")
            or url.startswith("https://")
            or url.startswith("about:")
        ):
            url = "https://" + url
        try:
            launch_chrome(url)
        except FileNotFoundError:
            self._append_alert("Could not find Chrome binary")

    def _poll_metrics(self) -> None:
        try:
            while True:
                metrics = self.metrics_queue.get_nowait()
                self._update_from_metrics(metrics)
        except queue.Empty:
            pass
        self.root.after(500, self._poll_metrics)

    def _update_from_metrics(self, metrics: dict) -> None:
        self.total_cpu_var.set(metrics.get("total_cpu", 0.0))
        self.worst_cpu_var.set(metrics.get("worst_cpu", 0.0))

        kind = metrics.get("worst_kind", "none")
        pid = metrics.get("pid")
        cmd = metrics.get("cmd_preview", "")

        self.kind_var.set(kind)
        self.pid_var.set(str(pid) if pid is not None else "-")
        self.cmd_var.set(cmd)

        alert = metrics.get("alert")
        if alert:
            self._append_alert(alert)

    def _append_alert(self, text: str) -> None:
        self.alert_text.insert("end", text + "\n\n")
        self.alert_text.see("end")

    def shutdown(self) -> None:
        self.stop_event.set()


def main() -> None:
    root = tk.Tk()
    app = ChromeGuardUI(root)

    def on_close() -> None:
        app.shutdown()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
