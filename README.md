# CAD pack (v2)

Official Neural Junkie CAD domain pack — parametric OpenSCAD design through manufacturing.

**North star:** v1 is chat → SCAD → STL. v2 is parametric design through manufacturing, local-first.

## Specialists

- **CADExpert** — OpenSCAD authoring, assembly, version history
- **ManufacturingExpert** — printability, mesh repair, slicer export, G-code sanity, STEP/2D

## Setup

```bash
make setup    # venv + trimesh
make verify   # pack manifest + sidecar smoke
make pack-smoke
```

See [assets/WORKSPACE.md](assets/WORKSPACE.md) for full workflow.

## Phase 0 eval leaderboard (compile pass rate)

Run locally with OpenSCAD + Ollama:

```bash
./scripts/eval-cad-models.sh qwen3.5:27b --json-out /tmp/cad-eval-qwen.json
./scripts/eval-cad-models.sh nj-cad:27b --json-out /tmp/cad-eval-lora.json
```

| Model | Role | Notes |
|-------|------|-------|
| `qwen3.5:27b` | Chat baseline | Default in `pack.yaml` |
| `qwen3.5:9b` | Tool runner | Compose `tool_model` |
| `nj-cad:27b` | Domain LoRA | Recommended when compile rate ≥ baseline |

Publish updated scores in release notes after each eval run.

## Scenarios

| Path | Gate |
|------|------|
| `scenarios/implement/cad-render-smoke.json` | Sidecar render fixture |
| `scenarios/implement/dm-cad-greeting-smoke.json` | CADExpert DM |
| `scenarios/collab/cad-design-render-export-smoke.json` | Design → export collab |

## Release

```bash
make pack-zip
```
