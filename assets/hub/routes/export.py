"""STEP/2D drawing export and slicer preset bundles."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from cad_common import dry_run_enabled, freecad_path


def export_step(body: dict[str, Any], settings: dict, pack_dir: str) -> dict[str, Any]:
    src = (body.get("stl_path") or body.get("path") or "").strip()
    dest = (body.get("dest_path") or "").strip()
    if dry_run_enabled(settings) or not src:
        return {"dry_run": True, "step_path": dest or "export/part.step", "ok": True}
    src_path = Path(src).expanduser()
    if not src_path.is_file():
        raise ValueError(f"source not found: {src_path}")
    out_path = Path(dest).expanduser() if dest else src_path.with_suffix(".step")
    fc = freecad_path(settings)
    script = f"""
import FreeCAD, Mesh, Part, Import
doc = FreeCAD.newDocument()
mesh = Mesh.Mesh("{src_path}")
shape = Part.Shape()
shape.makeShapeFromMesh(mesh.Topology, 0.1)
obj = doc.addObject("Part::Feature", "Part")
obj.Shape = shape
Import.export([obj], "{out_path}")
FreeCAD.closeDocument(doc.Name)
"""
    proc = subprocess.run([fc, "-c", script], capture_output=True, text=True, timeout=180, check=False)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "FreeCAD STEP export failed").strip())
    return {"ok": True, "step_path": str(out_path)}


def export_drawing(body: dict[str, Any], settings: dict, pack_dir: str) -> dict[str, Any]:
    src = (body.get("step_path") or body.get("stl_path") or body.get("path") or "").strip()
    dest = (body.get("dest_path") or "").strip()
    if dry_run_enabled(settings) or not src:
        return {"dry_run": True, "drawing_path": dest or "export/part.pdf", "ok": True}
    out_path = Path(dest).expanduser() if dest else Path(src).with_suffix(".pdf")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # TechDraw requires GUI modules; write a placeholder PDF note for headless v2
    out_path.write_text(
        "CAD pack v2 drawing export placeholder — configure FreeCAD TechDraw for production PDFs.\n",
        encoding="utf-8",
    )
    return {"ok": True, "drawing_path": str(out_path), "note": "placeholder PDF; configure FreeCAD TechDraw"}


def export_slicer(body: dict[str, Any], settings: dict, pack_dir: str) -> dict[str, Any]:
    stl_path = (body.get("stl_path") or body.get("path") or "").strip()
    slicer = (body.get("slicer") or "prusa").lower()
    dest = (body.get("dest_path") or "").strip()
    if dry_run_enabled(settings) or not stl_path:
        preset_name = "0.20mm Standard" if slicer == "prusa" else "0.20mm Standard @BBL X1C"
        return {
            "dry_run": True,
            "slicer": slicer,
            "preset": preset_name,
            "bundle_path": dest or f"export/job.{'3mf' if slicer == 'prusa' else 'json'}",
        }
    out_path = Path(dest).expanduser() if dest else Path(stl_path).with_suffix(".slicer.json")
    profile = {
        "slicer": slicer,
        "stl_path": stl_path,
        "layer_height_mm": 0.2,
        "perimeters": 3,
        "infill_percent": 20,
        "material": "PLA",
        "nozzle_temp_c": 210,
        "bed_temp_c": 60,
    }
    if slicer == "orca":
        profile["printer"] = "Bambu Lab P1S"
        profile["preset"] = "0.20mm Standard @BBL X1C"
    else:
        profile["printer"] = "Prusa MK4"
        profile["preset"] = "0.20mm Standard"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    return {"ok": True, "bundle_path": str(out_path), "profile": profile}
