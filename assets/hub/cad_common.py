"""Shared CAD sidecar helpers: paths, settings, param parsing, dry-run."""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import struct
import subprocess
import time
from pathlib import Path
from typing import Any


def _truthy(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    return str(val).strip().lower() not in ("0", "false", "no", "")


def _setting(settings: dict, *keys: str, default: str = "") -> str:
    for key in keys:
        val = settings.get(key)
        if val is not None and str(val).strip() != "":
            return str(val).strip()
    return default


def dry_run_enabled(settings: dict) -> bool:
    return _truthy(settings.get("cad_sidecar_dry_run")) or _truthy(
        os.environ.get("NJ_CAD_DRY_RUN")
    )


def openscad_path(settings: dict) -> str:
    return _setting(settings, "openscad_path", default="openscad")


def freecad_path(settings: dict) -> str:
    return _setting(settings, "freecad_path", default="freecad")


def artifacts_root(settings: dict) -> Path:
    raw = _setting(settings, "cad_artifacts_dir", default="~/.neural-junkie/cad")
    return Path(os.path.expanduser(raw))


def pack_fixtures_dir(pack_dir: str) -> Path:
    return Path(pack_dir) / "scenarios" / "fixtures"


def sanitize_project_id(project_id: str) -> str:
    project_id = (project_id or "").strip() or "default"
    out = []
    for ch in project_id:
        if ch.isalnum() or ch in "-_":
            out.append(ch)
        elif ch in "/\\ ":
            out.append("-")
    return "".join(out) or "default"


def project_paths(settings: dict, project_id: str = "default") -> dict[str, Path]:
    root = artifacts_root(settings) / sanitize_project_id(project_id)
    versions = root / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    return {
        "root": root,
        "scad": root / "model.scad",
        "stl": root / "preview.stl",
        "versions": versions,
    }


PARAM_ASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;]+);")
SECTION_RE = re.compile(r"/\*\s*\[([^\]]+)\]\s*\*/")
RANGE_RE = re.compile(r"\[(-?\d+(?:\.\d+)?)\s*:\s*(-?\d+(?:\.\d+)?)(?:\s*:\s*(-?\d+(?:\.\d+)?))?\]")


def parse_params(source: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    section = ""
    for line in source.splitlines():
        stripped = line.strip()
        m = SECTION_RE.search(stripped)
        if m:
            section = m.group(1).strip()
            continue
        if not stripped or (stripped.startswith("//") and "[" not in stripped):
            continue
        m = PARAM_ASSIGN_RE.match(stripped)
        if not m:
            continue
        name, value = m.group(1), m.group(2).strip()
        comment = ""
        if "//" in line:
            comment = line.split("//", 1)[1].strip()
        entry: dict[str, Any] = {
            "name": name,
            "value": value,
            "section": section,
            "comment": comment,
        }
        rm = RANGE_RE.search(comment)
        if rm:
            entry["min"] = float(rm.group(1))
            entry["max"] = float(rm.group(2))
            if rm.group(3):
                entry["step"] = float(rm.group(3))
        out.append(entry)
    return out


def format_openscad_value(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return '""'
    if value.startswith("[") or value.startswith("("):
        return value
    lower = value.lower()
    if lower in ("true", "false"):
        return lower
    try:
        float(value)
        return value
    except ValueError:
        return json.dumps(value)


def render_scad_to_stl(
    scad_path: Path,
    stl_path: Path,
    settings: dict,
    params: dict[str, str] | None = None,
    timeout_sec: int = 120,
) -> None:
    if dry_run_enabled(settings):
        stl_path.parent.mkdir(parents=True, exist_ok=True)
        stl_path.write_bytes(minimal_cube_stl_bytes())
        return
    bin_path = openscad_path(settings)
    if not scad_path.is_file():
        raise ValueError(f"scad file not found: {scad_path}")
    stl_path.parent.mkdir(parents=True, exist_ok=True)
    args = [bin_path, "-o", str(stl_path)]
    for key, val in (params or {}).items():
        key = key.strip()
        if not key:
            continue
        args.extend(["-D", f"{key}={format_openscad_value(str(val))}"])
    args.append(str(scad_path))
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"openscad not found ({bin_path!r}): install from https://openscad.org"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"openscad timed out after {timeout_sec}s") from exc
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"openscad failed: {msg}")
    if not stl_path.is_file():
        raise RuntimeError("openscad did not produce output")


def test_openscad(settings: dict) -> str:
    if dry_run_enabled(settings):
        return "OpenSCAD dry-run OK"
    bin_path = openscad_path(settings)
    try:
        proc = subprocess.run(
            [bin_path, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"openscad not found at {bin_path!r}") from exc
    text = (proc.stdout or proc.stderr or "").strip()
    if proc.returncode != 0:
        raise RuntimeError(text or "openscad --version failed")
    return text


def minimal_cube_stl_bytes() -> bytes:
    """Return a tiny binary STL (12 triangles) for dry-run smoke tests."""
    # 20mm cube centered at origin
    verts = [
        (-10, -10, -10),
        (10, -10, -10),
        (10, 10, -10),
        (-10, 10, -10),
        (-10, -10, 10),
        (10, -10, 10),
        (10, 10, 10),
        (-10, 10, 10),
    ]
    faces = [
        (0, 2, 1),
        (0, 3, 2),
        (4, 5, 6),
        (4, 6, 7),
        (0, 1, 5),
        (0, 5, 4),
        (2, 3, 7),
        (2, 7, 6),
        (0, 4, 7),
        (0, 7, 3),
        (1, 2, 6),
        (1, 6, 5),
    ]
    buf = bytearray(b"\x00" * 80)
    buf += struct.pack("<I", len(faces))
    for i0, i1, i2 in faces:
        v0, v1, v2 = verts[i0], verts[i1], verts[i2]
        # normal placeholder
        buf += struct.pack("<3f", 0.0, 0.0, 1.0)
        buf += struct.pack("<3f", *v0)
        buf += struct.pack("<3f", *v1)
        buf += struct.pack("<3f", *v2)
        buf += struct.pack("<H", 0)
    return bytes(buf)


def read_stl_b64(path: Path, settings: dict) -> str:
    if not path.is_file():
        if dry_run_enabled(settings):
            return base64.b64encode(minimal_cube_stl_bytes()).decode("ascii")
        raise ValueError(f"stl not found: {path}")
    return base64.b64encode(path.read_bytes()).decode("ascii")


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def save_version(
    paths: dict[str, Path],
    label: str,
    params: dict[str, str] | None,
    scad_content: str,
    stl_path: Path | None,
) -> dict[str, Any]:
    vid = str(time.time_ns())
    vdir = paths["versions"] / vid
    vdir.mkdir(parents=True, exist_ok=True)
    scad_rel = Path("versions") / vid / "model.scad"
    scad_abs = paths["root"] / scad_rel
    scad_abs.write_text(scad_content, encoding="utf-8")
    meta: dict[str, Any] = {
        "id": vid,
        "label": (label or "").strip() or vid,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "params": params or {},
        "scad_rel": str(scad_rel).replace("\\", "/"),
    }
    if stl_path and stl_path.is_file():
        stl_rel = Path("versions") / vid / "preview.stl"
        copy_file(stl_path, paths["root"] / stl_rel)
        meta["stl_rel"] = str(stl_rel).replace("\\", "/")
    (vdir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {
        "id": meta["id"],
        "label": meta["label"],
        "created_at": meta["created_at"],
        "params": meta.get("params"),
    }


def list_versions(paths: dict[str, Path]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not paths["versions"].is_dir():
        return out
    for entry in paths["versions"].iterdir():
        meta_path = entry / "meta.json"
        if not meta_path.is_file():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        out.append(
            {
                "id": meta.get("id", entry.name),
                "label": meta.get("label", entry.name),
                "created_at": meta.get("created_at", ""),
                "params": meta.get("params"),
            }
        )
    out.sort(key=lambda m: m.get("created_at", ""), reverse=True)
    return out


def restore_version(paths: dict[str, Path], version_id: str) -> str:
    version_id = (version_id or "").strip()
    meta_path = paths["versions"] / version_id / "meta.json"
    if not meta_path.is_file():
        raise ValueError(f"version not found: {version_id}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    scad_rel = meta.get("scad_rel", "")
    src = paths["root"] / scad_rel
    content = src.read_text(encoding="utf-8")
    paths["scad"].write_text(content, encoding="utf-8")
    stl_rel = meta.get("stl_rel")
    if stl_rel:
        stl_src = paths["root"] / stl_rel
        if stl_src.is_file():
            copy_file(stl_src, paths["stl"])
    return content
