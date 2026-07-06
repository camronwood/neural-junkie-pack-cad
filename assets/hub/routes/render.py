"""CAD sidecar render routes — OpenSCAD, params, versions."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cad_common import (
    dry_run_enabled,
    list_versions,
    pack_fixtures_dir,
    parse_params,
    project_paths,
    read_stl_b64,
    render_scad_to_stl,
    restore_version,
    save_version,
    test_openscad,
)


def _resolve_scad_stl(body: dict[str, Any], settings: dict, pack_dir: str) -> tuple[Path, Path, str]:
    path = (body.get("path") or "").strip()
    project_id = (body.get("project_id") or "default").strip() or "default"
    output_path = (body.get("output_path") or "").strip()

    if path:
        scad_path = Path(path).expanduser()
        if not scad_path.is_absolute() and pack_dir:
            candidate = pack_fixtures_dir(pack_dir) / path
            if candidate.is_file():
                scad_path = candidate
        stl_path = Path(output_path) if output_path else scad_path.parent / "preview.stl"
    else:
        paths = project_paths(settings, project_id)
        scad_path = paths["scad"]
        stl_path = Path(output_path) if output_path else paths["stl"]
    return scad_path, stl_path, project_id


def render(body: dict[str, Any], settings: dict, pack_dir: str) -> dict[str, Any]:
    scad_path, stl_path, _ = _resolve_scad_stl(body, settings, pack_dir)
    params = body.get("params") if isinstance(body.get("params"), dict) else {}
    render_scad_to_stl(scad_path, stl_path, settings, params)
    scad_content = scad_path.read_text(encoding="utf-8") if scad_path.is_file() else ""
    return {
        "mime": "model/stl",
        "content_base64": read_stl_b64(stl_path, settings),
        "scad_path": str(scad_path),
        "stl_path": str(stl_path),
        "params": parse_params(scad_content),
        "dry_run": dry_run_enabled(settings),
    }


def mesh(query: dict[str, str], settings: dict, pack_dir: str) -> dict[str, Any]:
    body = {
        "path": query.get("path", ""),
        "project_id": query.get("project_id", "default"),
    }
    _, stl_path, _ = _resolve_scad_stl(body, settings, pack_dir)
    return {
        "mime": "model/stl",
        "content_base64": read_stl_b64(stl_path, settings),
        "stl_path": str(stl_path),
    }


def params(query: dict[str, str], settings: dict, pack_dir: str) -> dict[str, Any]:
    body = {
        "path": query.get("path", ""),
        "project_id": query.get("project_id", "default"),
    }
    scad_path, _, _ = _resolve_scad_stl(body, settings, pack_dir)
    if not scad_path.is_file():
        raise ValueError(f"scad not found: {scad_path}")
    content = scad_path.read_text(encoding="utf-8")
    return {"path": str(scad_path), "params": parse_params(content)}


def versions_get(query: dict[str, str], settings: dict) -> dict[str, Any]:
    project_id = (query.get("project_id") or "default").strip() or "default"
    paths = project_paths(settings, project_id)
    return {"versions": list_versions(paths)}


def versions_post(body: dict[str, Any], settings: dict, pack_dir: str) -> dict[str, Any]:
    project_id = (body.get("project_id") or "default").strip() or "default"
    paths = project_paths(settings, project_id)
    scad_path, _, _ = _resolve_scad_stl(body, settings, pack_dir)
    if not scad_path.is_file():
        raise ValueError(f"scad not found: {scad_path}")
    content = scad_path.read_text(encoding="utf-8")
    params_map = body.get("params") if isinstance(body.get("params"), dict) else {}
    return save_version(paths, body.get("label", ""), params_map, content, paths["stl"])


def versions_restore(body: dict[str, Any], settings: dict) -> dict[str, Any]:
    project_id = (body.get("project_id") or "default").strip() or "default"
    version_id = (body.get("version_id") or "").strip()
    paths = project_paths(settings, project_id)
    content = restore_version(paths, version_id)
    return {"scad_path": str(paths["scad"]), "content": content}


def test_openscad_route(body: dict[str, Any], settings: dict) -> dict[str, Any]:
    if body.get("path"):
        settings = dict(settings)
        settings["openscad_path"] = body["path"]
    msg = test_openscad(settings)
    return {"ok": True, "message": msg}
