# Printability review

1. Render latest STL from OpenSCAD (`render_openscad` or workbench **Render**).
2. Call `@ManufacturingExpert` or `check_printability` on the STL path.
3. Review overhang report — faces above 45° may need supports.
4. Confirm estimated min wall thickness ≥ 1.2mm for FDM (2.4mm for structural parts).
5. If mesh is not watertight, run `repair_mesh` before slicing.
6. Document warnings in chat before approving print.
