import asyncio
import json
import math
from dataclasses import dataclass
from typing import List

import requests
import websockets


DEVTOOLS_URL = "http://localhost:9222/json"

@dataclass
class TabMetric:
    title: str
    url: str
    cpu_pct: float


async def _get_tab_metrics_once(interval: float = 2.0) -> List[TabMetric]:
    resp = requests.get(DEVTOOLS_URL, timeout=1.0)
    
    resp.raise_for_status()
    targets = [t for t in resp.json() if t.get("type") == "page"]
    print("DEBUG targets:", targets)

    tab_infos = []
    for t in targets:
        ws_url = t.get("webSocketDebuggerUrl")
        if not ws_url:
            continue
        tab_infos.append(
            {
                "title": t.get("title", ""),
                "url": t.get("url", ""),
                "ws_url": ws_url,
            }
        )

    metrics_results: List[TabMetric] = []

    # Measure each tab twice and compute delta TaskDuration as a proxy for CPU load
    for info in tab_infos:
        try:
            async with websockets.connect(info["ws_url"]) as ws:
                await ws.send(json.dumps({"id": 1, "method": "Performance.enable"}))
                await ws.recv()

                await ws.send(json.dumps({"id": 2, "method": "Performance.getMetrics"}))
                first_raw = json.loads(await ws.recv())
                await asyncio.sleep(interval)
                await ws.send(json.dumps({"id": 3, "method": "Performance.getMetrics"}))
                second_raw = json.loads(await ws.recv())
        except Exception:
            continue

        first_metrics = {m["name"]: m["value"] for m in first_raw["result"]["metrics"]}
        second_metrics = {m["name"]: m["value"] for m in second_raw["result"]["metrics"]}

        # TaskDuration is a decent proxy for CPU time in that tab
        delta_task = second_metrics.get("TaskDuration", 0.0) - first_metrics.get(
            "TaskDuration", 0.0
        )
        if delta_task < 0:
            delta_task = 0.0

        # For now, just store raw "work" score, we normalize later
        metrics_results.append(
            TabMetric(title=info["title"], url=info["url"], cpu_pct=delta_task)
        )

    # Normalize so sum of cpu_pct is 100
    total = sum(m.cpu_pct for m in metrics_results)
    if total > 0:
        for m in metrics_results:
            m.cpu_pct = 100.0 * m.cpu_pct / total
    else:
        for m in metrics_results:
            m.cpu_pct = 0.0

    return metrics_results


def get_tab_metrics_blocking(interval: float = 2.0) -> List[TabMetric]:
    return asyncio.run(_get_tab_metrics_once(interval=interval))
