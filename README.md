# Chrome Guard

Chrome Guard is a lightweight desktop tool that launches Google Chrome in a dedicated low-latency profile and monitors how the browser uses system resources. It shows real-time CPU usage for Chrome, highlights which subprocess is causing load, and estimates per-tab activity using the Chrome DevTools Protocol. A simple Tkinter interface lets you open URLs and watch live metrics without using the command line.

## Features

* Launches Chrome with a low-latency, isolated user profile
* Tracks total CPU usage across all Chrome processes
* Identifies the highest-CPU Chrome subprocess (tab renderer, extension, GPU coordinator, utility, and so on)
* Estimates per-tab CPU contribution via the Chrome DevTools Protocol
* Shows live meters and a tab list in a desktop UI
* Logs alerts when Chrome causes sustained CPU spikes

## Project layout

chrome-guard/
• README.md
• requirements.txt

chrome_guard/
• **init**.py
• config.py
• launcher.py
• monitor.py
• notifications.py
• ui.py
• utils/
• **init**.py
• process_utils.py

scripts/
• run_gui.py
• run_monitor_only.py

## Installation

1. Create a virtual environment
   python3 -m venv .venv

2. Activate the virtual environment
   source .venv/bin/activate

3. Install dependencies
   pip install -r requirements.txt

## Running Chrome Guard

To start the desktop UI:
python3 scripts/run_gui.py

This opens the Chrome Guard window. Enter a URL and click the button to launch Chrome and begin monitoring.

To run the monitor without the UI:
python3 scripts/run_monitor_only.py

This prints Chrome CPU statistics and alerts to the terminal.

## Configuration

You can override default settings using environment variables:

CHROME_GUARD_CHROME_PATH
CHROME_GUARD_CPU_TOTAL
CHROME_GUARD_CPU_SINGLE
CHROME_GUARD_POLL_INTERVAL
CHROME_GUARD_SUSTAINED_HITS

Defaults for these values are defined in config.py.
