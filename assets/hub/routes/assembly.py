"""Assembly manifest, BOM, and fit validation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cad_common import dry_run_enabled, project_paths, render_scad_to_stl


def validate_assembly(body: dict[str, Any], settings: dict, pack_dir: str) -> dict[str, Any]:
    manifest_path = (body.get("manifest_path") or body.get("path") or "").strip()
    clearance_mm = float(body.get("clearance_mm", 0.2))

    if dry_run_enabled(settings) or not manifest_path:
        return {
            "dry_run": True,
            "ok": True,
            "bom": [
                {"part_id": "base", "name": "Base", "scad": "parts/base.scad"},
                {"part_id": "lid", "name": "Lid", "scad": "parts/lid.scad"},
            ],
            "fit_issues": [],
        }

    path = Path(manifest_path).expanduser()
    if not path.is_file():
        raise ValueError(f"manifest not found: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    parts = manifest.get("parts") or []
    bom = []
    fit_issues = []
    bboxes: list[dict[str, Any]] = []

    for part in parts:
        part_id = part.get("id", "part")
        name = part.get("name", part_id)
        scad_rel = part.get("scad", "")
        bom.append({"part_id": part_id, "name": name, "scad": scad_rel})
        scad_path = (path.parent / scad_rel).resolve()
        if not scad_path.is_file():
            fit_issues.append({"part_id": part_id, "issue": "missing scad"})
            continue
        stl_path = scad_path.with_suffix(".preview.stl")
        try:
            render_scad_to_stl(scad_path, stl_path, settings, part.get("params"))
        except RuntimeError as exc:
            fit_issues.append({"part_id": part_id, "issue": str(exc)})
            continue
        # Bounding box from transform + nominal size if provided
        transform = part.get("transform") or {}
        pos = transform.get("translate", [0, 0, 0])
        size = part.get("bbox_mm") or [20, 20, 20]
        bboxes.append(
            {
                "part_id": part_id,
                "min": [pos[i] - size[i] / 2 for i in range(3)],
                "max": [pos[i] + size[i] / 2 for i in range(3)],
            }
        )

    # Pairwise overlap check with clearance
    for i, a in enumerate(bboxes):
        for b in bboxes[i + 1 :]:
            overlap = True
            for axis in range(3):
                if a["max"][axis] + clearance_mm <= b["min"][axis] or b["max"][axis] + clearance_mm <= a["min"][axis]:
                    overlap = False
                    break
            if overlap:
                fit_issues.append(
                    {
                        "parts": [a["part_id"], b["part_id"]],
                        "issue": f"bounding boxes overlap within {clearance_mm}mm clearance",
                    }
                )

    return {"ok": len(fit_issues) == 0, "bom": bom, "fit_issues": fit_issues}


def create_assembly(body: dict[str, Any], settings: dict, pack_dir: str) -> dict[str, Any]:
    project_id = (body.get("project_id") or "default").strip() or "default"
    parts = body.get("parts") or []
    paths = project_paths(settings, project_id)
    manifest = {
        "project_id": project_id,
        "parts": parts,
        "clearance_mm": body.get("clearance_mm", 0.2),
    }
    manifest_path = paths["root"] / "cad.project.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"manifest_path": str(manifest_path), "part_count": len(parts)}
