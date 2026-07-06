# Export for FDM

1. Final render to STL in workspace `exports/` directory.
2. Run printability check.
3. `@ManufacturingExpert` — `export_slicer_preset` for PrusaSlicer or Orca profile JSON.
4. Import STL + preset into slicer; review layer height and temps.
5. Optional: `sanity_check_gcode` on exported G-code before sending to printer.
