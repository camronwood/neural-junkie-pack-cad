# CAD workspace

Parametric design through manufacturing — OpenSCAD authoring, printability checks, and export, local-first.

## Prerequisites

1. Install **OpenSCAD**: [https://openscad.org](https://openscad.org)
2. Run sidecar setup:

```bash
./scripts/setup-cad-sidecar.sh
```

3. Optional: install **FreeCAD** for STEP import/export and 2D drawings — set `freecad_path` in **Settings → Domain packs → CAD tools**.

Test OpenSCAD from Settings or:

```bash
curl -X POST http://127.0.0.1:8080/api/cad/test-openscad -d '{}'
```

## Specialists

| Agent | Owns |
|-------|------|
| **CADExpert** | OpenSCAD authoring, params, assembly layout, version history |
| **ManufacturingExpert** | Printability, mesh repair, slicer presets, G-code sanity, STEP/2D export |

### Handoff wiring

```
Design parametric part        → @CADExpert
Will this print? / overhangs  → @ManufacturingExpert
Prusa/Orca export / G-code    → @ManufacturingExpert
STEP or dimensioned drawing   → @ManufacturingExpert
Multi-part BOM / fit check    → @CADExpert then @ManufacturingExpert
```

## Sidecar

Hub starts `assets/hub/server.py` when the CAD pack is enabled. Routes under `/api/cad/*`.

Health: `GET /api/cad/status`

Dry-run (no OpenSCAD): set `cad_sidecar_dry_run: true` in pack settings overlay.

## Model stack

| Role | Default |
|------|---------|
| Chat (CADExpert, ManufacturingExpert) | `qwen3.5:27b` |
| Tool runner | `qwen3.5:9b` |
| Domain LoRA (recommended when eval wins) | `nj-cad:27b` |

Run compile benchmark: `make eval` or `./scripts/eval-cad-models.sh qwen3.5:27b`

## Workbench

- Open `.scad` → CAD workbench (editor, param sliders, Three.js preview, versions).
- **Printability** panel — overhang and wall-thickness report from sidecar.
- **Assembly** panel — multi-part `cad.project.json` BOM and fit warnings.

## Pack assets

| Path | Purpose |
|------|---------|
| `assets/runbooks/printability-review.md` | FDM printability SOP |
| `assets/runbooks/assembly-fit-check.md` | Assembly validation SOP |
| `assets/runbooks/export-for-fdm.md` | STL → slicer export SOP |
| `assets/eval/cad.yaml` | Keyword eval probes |
| `scenarios/model-eval/prompts.json` | OpenSCAD compile benchmark |

## Smoke test

```bash
make verify && make pack-smoke
```

Collab north-star: `scenarios/collab/cad-design-render-export-smoke.json`

## Settings

| Key | Default |
|-----|---------|
| `cad_artifacts_dir` | `~/.neural-junkie/cad` |
| `cad_venv` | `~/.neural-junkie/cad/venv` |
| `openscad_path` | `openscad` |
| `freecad_path` | (optional) |
| `cad_sidecar_dry_run` | `false` |
