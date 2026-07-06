"""Printability analysis — overhangs and wall thickness."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from cad_common import dry_run_enabled, minimal_cube_stl_bytes


def _load_trimesh():
    try:
        import trimesh  # type: ignore

        return trimesh
    except ImportError:
        return None


def check_printability(body: dict[str, Any], settings: dict, pack_dir: str) -> dict[str, Any]:
    stl_path = (body.get("stl_path") or body.get("path") or "").strip()
    min_wall = float(body.get("min_wall_mm", 1.2))
    max_overhang_deg = float(body.get("max_overhang_deg", 45))

    if dry_run_enabled(settings) or stl_path == "dry-run":
        return {
            "dry_run": True,
            "printable": True,
            "min_wall_mm": min_wall,
            "estimated_min_wall_mm": 2.0,
            "overhang": {
                "max_angle_deg": 32.0,
                "faces_over_limit": 12,
                "threshold_deg": max_overhang_deg,
            },
            "warnings": [],
        }

    path = Path(stl_path).expanduser()
    if not path.is_file():
        raise ValueError(f"stl not found: {path}")

    trimesh = _load_trimesh()
    if trimesh is None:
        raise RuntimeError("trimesh not installed — run scripts/setup-cad-sidecar.sh")

    mesh = trimesh.load(str(path), force="mesh")
    warnings: list[str] = []

    # Overhang: angle between face normal and +Z (build direction)
    over_limit = 0
    max_angle = 0.0
    normals = getattr(mesh, "face_normals", None)
    if normals is not None:
        for n in normals:
            nz = float(n[2]) if len(n) > 2 else 1.0
            nz = max(-1.0, min(1.0, nz))
            angle_from_horizontal = math.degrees(math.acos(abs(nz)))
            overhang_angle = 90.0 - angle_from_horizontal
            max_angle = max(max_angle, overhang_angle)
            if overhang_angle > max_overhang_deg:
                over_limit += 1
    if over_limit > 0:
        warnings.append(f"{over_limit} faces exceed {max_overhang_deg}° overhang")

    # Wall thickness proxy: bounding-box smallest dimension / 2
    bounds = mesh.bounds
    extents = bounds[1] - bounds[0]
    est_wall = float(min(extents)) / 2.0 if len(extents) else 0.0
    printable = est_wall >= min_wall and over_limit == 0
    if est_wall < min_wall:
        warnings.append(f"estimated min wall {est_wall:.2f}mm < {min_wall}mm")

    watertight = bool(getattr(mesh, "is_watertight", True))
    if not watertight:
        warnings.append("mesh is not watertight")

    return {
        "printable": printable,
        "watertight": watertight,
        "min_wall_mm": min_wall,
        "estimated_min_wall_mm": round(est_wall, 3),
        "overhang": {
            "max_angle_deg": round(max_angle, 2),
            "faces_over_limit": over_limit,
            "threshold_deg": max_overhang_deg,
        },
        "warnings": warnings,
        "triangle_count": len(getattr(mesh, "faces", []) or []),
    }
