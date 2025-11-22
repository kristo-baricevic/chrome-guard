import queue
from threading import Event, Thread

import tkinter as tk
from tkinter import ttk

from .launcher import launch_chrome
from .monitor import monitor_chrome_loop


class ChromeGuardUI:
    def __init__(self, root: tk.Tk) -> None:
        # Keep a reference to the root Tk window
        self.root = root
        # Window title and initial size
        self.root.title("¸,ø¤º°`°º¤ø,¸¸,ø¤º°`°º¤ø,Chrome Guard,ø¤°º¤ø,¤º°`°`°º¤ø,¸")
        self.root.geometry("600x400")

        # Queue for metrics coming from the background monitor thread
        self.metrics_queue: queue.Queue = queue.Queue()
        # Event used to signal the monitor thread to stop
        self.stop_event = Event()
        # Start the background thread that watches Chrome CPU usage
        self.monitor_thread = Thread(
            target=monitor_chrome_loop,
            args=(self.metrics_queue, self.stop_event),
            daemon=True,
        )
        self.monitor_thread.start()

        # Build the UI widgets and start polling for metrics
        self._build_widgets()
        self._poll_metrics()

    def _build_widgets(self) -> None:
        # Top level frame in the window
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        # Row with URL label, text entry, and open button
        url_frame = ttk.Frame(main)
        url_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(url_frame, text="URL:").pack(side="left")

        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))

        open_btn = ttk.Button(url_frame, text="Open in Chrome", command=self._on_open)
        open_btn.pack(side="right")

        # Frame for CPU usage meters
        meters_frame = ttk.LabelFrame(main, text="Resource usage")
        meters_frame.pack(fill="x", pady=(0, 10))

        # Total Chrome CPU meter
        ttk.Label(meters_frame, text="Total Chrome CPU %").pack(anchor="w")
        self.total_cpu_var = tk.DoubleVar(value=0.0)
        self.total_cpu_bar = ttk.Progressbar(
            meters_frame,
            maximum=400.0,
            variable=self.total_cpu_var,
        )
        self.total_cpu_bar.pack(fill="x", pady=(0, 5))

        # Worst single process CPU meter
        ttk.Label(meters_frame, text="Worst process CPU %").pack(anchor="w")
        self.worst_cpu_var = tk.DoubleVar(value=0.0)
        self.worst_cpu_bar = ttk.Progressbar(
            meters_frame,
            maximum=200.0,
            variable=self.worst_cpu_var,
        )
        self.worst_cpu_bar.pack(fill="x", pady=(0, 5))

        # Frame showing info about the current worst process
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

        # Allow the second column to expand
        info_frame.columnconfigure(1, weight=1)

        # after info_frame and before alerts_frame, for example
        tabs_frame = ttk.LabelFrame(main, text="Tabs")
        tabs_frame.pack(fill="x", pady=(0, 10))

        self.tab_count_var = tk.StringVar(value="0")
        ttk.Label(tabs_frame, text="Open tabs:").grid(row=0, column=0, sticky="w")
        ttk.Label(tabs_frame, textvariable=self.tab_count_var).grid(
            row=0, column=1, sticky="w", padx=5
        )

        self.tabs_list = tk.Listbox(tabs_frame, height=5)
        self.tabs_list.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(5, 0))

        tabs_frame.columnconfigure(1, weight=1)
        tabs_frame.rowconfigure(1, weight=1)


        # Text box to show alert messages
        alerts_frame = ttk.LabelFrame(main, text="Alerts")
        alerts_frame.pack(fill="both", expand=True)

        self.alert_text = tk.Text(alerts_frame, height=6, wrap="word")
        self.alert_text.pack(fill="both", expand=True)

    def _on_open(self) -> None:
        # Normalize the URL from the entry
        url = self.url_var.get().strip()
        if not url:
            url = "about:blank"
        if not (
            url.startswith("http://")
            or url.startswith("https://")
            or url.startswith("about:")
        ):
            url = "https://" + url
        # Try to launch Chrome, log an alert if the binary is missing
        try:
            launch_chrome(url)
        except FileNotFoundError:
            self._append_alert("Could not find Chrome binary")

    def _poll_metrics(self) -> None:
        # Nonblocking drain of any pending metrics and update UI
        try:
            while True:
                metrics = self.metrics_queue.get_nowait()
                self._update_from_metrics(metrics)
        except queue.Empty:
            pass
        # Schedule the next poll in 500 ms
        self.root.after(500, self._poll_metrics)

    def _update_from_metrics(self, metrics: dict) -> None:
        # Update the CPU meters
        self.total_cpu_var.set(metrics.get("total_cpu", 0.0))
        self.worst_cpu_var.set(metrics.get("worst_cpu", 0.0))

        # Update current culprit info
        kind = metrics.get("worst_kind", "none")
        pid = metrics.get("pid")
        cmd = metrics.get("cmd_preview", "")

        self.kind_var.set(kind)
        self.pid_var.set(str(pid) if pid is not None else "-")
        self.cmd_var.set(cmd)

        # tab metrics
        tabs = metrics.get("tabs") or []
        self.tab_count_var.set(str(metrics.get("tab_count", len(tabs))))

        # show top 5 tabs by cpu_pct
        self.tabs_list.delete(0, "end")
        top_tabs = sorted(tabs, key=lambda t: t.get("cpu_pct", 0.0), reverse=True)[:5]
        for t in top_tabs:
            title = t.get("title") or t.get("url") or "<untitled>"
            cpu_pct = t.get("cpu_pct", 0.0)
            self.tabs_list.insert("end", f"{cpu_pct:5.1f}%  {title}")


        # Append any alert text into the alerts box
        alert = metrics.get("alert")
        if alert:
            self._append_alert(alert)

    def _append_alert(self, text: str) -> None:
        # Append alert text and scroll to the bottom
        self.alert_text.insert("end", text + "\n\n")
        self.alert_text.see("end")

    def shutdown(self) -> None:
        # Signal the monitor thread to stop
        self.stop_event.set()


def main() -> None:
    # Create the root Tk window and the ChromeGuard UI
    root = tk.Tk()
    app = ChromeGuardUI(root)

    # On window close, shut down the monitor thread and destroy the window
    def on_close() -> None:
        app.shutdown()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
