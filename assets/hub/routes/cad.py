"""CAD sidecar route dispatcher."""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from routes import assembly, export, gcode, geometry, printability, render

POST_ROUTES = {
    "/api/cad/render": render.render,
    "/api/cad/versions": render.versions_post,
    "/api/cad/versions/restore": render.versions_restore,
    "/api/cad/test-openscad": render.test_openscad_route,
    "/api/cad/import": geometry.import_cad,
    "/api/cad/geometry/repair": geometry.repair_mesh,
    "/api/cad/printability": printability.check_printability,
    "/api/cad/export/step": export.export_step,
    "/api/cad/export/drawing": export.export_drawing,
    "/api/cad/export/slicer": export.export_slicer,
    "/api/cad/assembly/validate": assembly.validate_assembly,
    "/api/cad/assembly/create": assembly.create_assembly,
    "/api/cad/gcode/sanity": gcode.sanity_check_gcode,
}


def _query_dict(path: str) -> dict[str, str]:
    parsed = urlparse(path)
    qs = parse_qs(parsed.query)
    return {k: (v[0] if v else "") for k, v in qs.items()}


def handle_get(handler, path: str, settings: dict, pack_dir: str) -> None:
    parsed = urlparse(path)
    route = parsed.path
    query = _query_dict(path)
    if route == "/api/cad/status":
        handler._json(
            200,
            {
                "ok": True,
                "dry_run": settings.get("cad_sidecar_dry_run"),
                "openscad_path": settings.get("openscad_path", "openscad"),
            },
        )
        return
    if route == "/api/cad/mesh":
        try:
            result = render.mesh(query, settings, pack_dir)
            handler._json(200, result)
        except ValueError as exc:
            handler._json(404, {"error": str(exc)})
        return
    if route == "/api/cad/params":
        try:
            result = render.params(query, settings, pack_dir)
            handler._json(200, result)
        except ValueError as exc:
            handler._json(404, {"error": str(exc)})
        return
    if route == "/api/cad/versions":
        try:
            result = render.versions_get(query, settings)
            handler._json(200, result)
        except ValueError as exc:
            handler._json(400, {"error": str(exc)})
        return
    handler._json(404, {"error": "not found"})


def handle_post(handler, path: str, body: dict, settings: dict, pack_dir: str) -> None:
    route = path.split("?", 1)[0]
    fn = POST_ROUTES.get(route)
    if fn is None:
        handler._json(404, {"error": "not found"})
        return
    try:
        result = fn(body, settings, pack_dir)
        handler._json(200, result)
    except ValueError as exc:
        handler._json(400, {"error": str(exc)})
    except RuntimeError as exc:
        handler._json(503, {"error": str(exc)})
    except Exception as exc:  # noqa: BLE001
        handler._json(500, {"error": str(exc)})
