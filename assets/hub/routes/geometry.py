"""Mesh repair and STEP/IGES import routes."""
from __future__ import annotations

import base64
import subprocess
from pathlib import Path
from typing import Any

from cad_common import dry_run_enabled, freecad_path, minimal_cube_stl_bytes, read_stl_b64


def _load_trimesh():
    try:
        import trimesh  # type: ignore

        return trimesh
    except ImportError:
        return None


def repair_mesh(body: dict[str, Any], settings: dict, pack_dir: str) -> dict[str, Any]:
    stl_path = (body.get("stl_path") or body.get("path") or "").strip()
    if dry_run_enabled(settings) or stl_path == "dry-run":
        b64 = base64.b64encode(minimal_cube_stl_bytes()).decode("ascii")
        return {
            "repaired": True,
            "dry_run": True,
            "content_base64": b64,
            "issues_fixed": ["non_manifold", "degenerate_faces"],
        }
    path = Path(stl_path).expanduser()
    if not path.is_file():
        raise ValueError(f"stl not found: {path}")
    trimesh = _load_trimesh()
    if trimesh is None:
        raise RuntimeError("trimesh not installed — run scripts/setup-cad-sidecar.sh")
    mesh = trimesh.load(str(path), force="mesh")
    if hasattr(mesh, "fill_holes"):
        mesh.fill_holes()
    if hasattr(mesh, "remove_degenerate_faces"):
        mesh.remove_degenerate_faces()
    if hasattr(mesh, "remove_duplicate_faces"):
        mesh.remove_duplicate_faces()
    if hasattr(mesh, "fix_normals"):
        mesh.fix_normals()
    out_path = path.with_suffix(".repaired.stl")
    mesh.export(str(out_path))
    return {
        "repaired": True,
        "stl_path": str(out_path),
        "content_base64": read_stl_b64(out_path, settings),
        "watertight": bool(getattr(mesh, "is_watertight", False)),
    }


def import_cad(body: dict[str, Any], settings: dict, pack_dir: str) -> dict[str, Any]:
    src = (body.get("path") or body.get("source_path") or "").strip()
    fmt = (body.get("format") or Path(src).suffix.lstrip(".")).lower()
    if dry_run_enabled(settings) or not src:
        b64 = base64.b64encode(minimal_cube_stl_bytes()).decode("ascii")
        return {
            "dry_run": True,
            "format": fmt or "step",
            "content_base64": b64,
            "mime": "model/stl",
        }
    src_path = Path(src).expanduser()
    if not src_path.is_file():
        raise ValueError(f"import file not found: {src_path}")
    out_path = src_path.with_suffix(".imported.stl")
    fc = freecad_path(settings)
    script = f"""
import FreeCAD, Import, Mesh, Part
doc = FreeCAD.newDocument()
shape = Part.Shape()
shape.read("{src_path}")
obj = doc.addObject("Part::Feature", "Import")
obj.Shape = shape
mesh = doc.addObject("Mesh::Feature", "Mesh")
mesh.Mesh = Mesh.Mesh(obj.Shape.tessellate(0.1))
mesh.Mesh.write("{out_path}")
FreeCAD.closeDocument(doc.Name)
"""
    try:
        proc = subprocess.run(
            [fc, "-c", script],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"FreeCAD not found ({fc!r}) — set freecad_path in Settings"
        ) from exc
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"FreeCAD import failed: {msg}")
    return {
        "stl_path": str(out_path),
        "content_base64": read_stl_b64(out_path, settings),
        "mime": "model/stl",
        "format": fmt,
    }
