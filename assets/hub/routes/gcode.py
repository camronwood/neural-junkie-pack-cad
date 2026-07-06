"""G-code sanity checks."""
from __future__ import annotations

import re
from typing import Any

from cad_common import dry_run_enabled


def sanity_check_gcode(body: dict[str, Any], settings: dict, pack_dir: str) -> dict[str, Any]:
    gcode = body.get("gcode") or ""
    path = (body.get("path") or "").strip()
    if path and not gcode:
        from pathlib import Path

        gcode = Path(path).expanduser().read_text(encoding="utf-8", errors="replace")

    if dry_run_enabled(settings) and not gcode:
        gcode = "; dry-run\nG1 Z0.2 F3000\nM104 S200\nM140 S60"

    issues: list[str] = []
    layer_heights: list[float] = []
    temps: list[int] = []
    extrusion_moves = 0

    for line in gcode.splitlines():
        s = line.split(";", 1)[0].strip().upper()
        if not s:
            continue
        if s.startswith("M104") or s.startswith("M109"):
            m = re.search(r"S(-?\d+(?:\.\d+)?)", s)
            if m:
                temps.append(int(float(m.group(1))))
        if s.startswith("G0") or s.startswith("G1"):
            if "E" in s:
                extrusion_moves += 1
            z = re.search(r"Z(-?\d+(?:\.\d+)?)", s)
            if z:
                layer_heights.append(float(z.group(1)))

    if temps and max(temps) > 300:
        issues.append(f"nozzle temp {max(temps)}°C unusually high")
    if temps and min(temps) < 0:
        issues.append("negative nozzle temperature")
    if layer_heights:
        deltas = [layer_heights[i] - layer_heights[i - 1] for i in range(1, len(layer_heights)) if layer_heights[i] > layer_heights[i - 1]]
        for d in deltas:
            if d > 0.5:
                issues.append(f"layer height jump {d:.2f}mm > 0.5mm")
            if d < 0.05 and d > 0:
                issues.append(f"layer height {d:.2f}mm very thin")
    if extrusion_moves == 0:
        issues.append("no extrusion moves found")

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "stats": {
            "extrusion_moves": extrusion_moves,
            "max_nozzle_temp_c": max(temps) if temps else None,
            "layer_count": len(layer_heights),
        },
        "dry_run": dry_run_enabled(settings),
    }
